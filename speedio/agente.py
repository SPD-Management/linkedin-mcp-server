"""Aplica no MCP o cookie do LinkedIn que o painel mandou.

Laco simples: pergunta ao Worker se ha cookie esperando, aplica, responde.
Roda como tarefa agendada (ou `python agente.py --sempre`) na maquina que tem
o browser.

Por que o cookie vem por PULL e nao por PUSH: assim esta maquina nao precisa de
nenhuma porta aberta para o mundo alem do que o tunnel ja publica, e o Worker
nao precisa alcancar uma maquina que dorme.

O que este arquivo NAO faz: editar o upstream. Ele importa a maquinaria de
`linkedin_mcp_server` e a chama na ordem que o proprio `--import-from-browser`
usa — encena `cookies.json`, manda o servidor validar contra o /feed/, e so
entao grava o `source-state.json`. E o degrau 2 da regra em README.md.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import shutil
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

URL = os.environ.get("CACA_URL", "https://caca-vagas.speedio.com.br")
TOKEN = os.environ.get("CACA_TOKEN", "")
PORTA_MCP = int(os.environ.get("MCP_PORTA", "8080"))

# Os cookies que o LinkedIn precisa ver. `li_at` e a sessao; `JSESSIONID` e o
# par do token CSRF e so importa em acao que escreve — mandar mensagem e uma.
DOMINIO = ".www.linkedin.com"


def fala(msg: str) -> None:
    print(f"[agente] {msg}", flush=True)


def _chama(caminho: str, corpo: dict | None = None) -> dict:
    req = urllib.request.Request(
        f"{URL}{caminho}",
        data=json.dumps(corpo or {}).encode(),
        headers={"content-type": "application/json",
                 "authorization": f"Bearer {TOKEN}"},
        method="POST")
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read())


def pega_pedido() -> dict | None:
    """Consome o cookie que espera, se houver. O Worker o apaga na entrega."""
    return _chama("/api/sessao/pendente").get("cookie")


def responde(ok: bool, detalhe: str) -> None:
    try:
        _chama("/api/sessao/resultado", {"ok": ok, "detalhe": detalhe[:400]})
    except Exception as e:                      # noqa: BLE001
        fala(f"nao consegui responder ao painel: {e}")


def para_o_servidor() -> None:
    """Derruba o MCP antes de mexer no perfil.

    Sem isto a validacao brigaria com o servidor pelo mesmo perfil do Chromium:
    o upstream tem todo um mecanismo de lease para esse caso, e a forma mais
    simples de nao depender dele e nao ter concorrente.

    O alvo e QUEM ESCUTA A PORTA, nunca "todo python cujo caminho contem
    linkedin-mcp". Aquele filtro derrubava o proprio agente: o `uv run` lanca o
    python do venv (`...\\linkedin-mcp-server\\.venv\\Scripts\\python.exe`) como
    PAI, e matar o pai levava a arvore inteira. Media 9444 de `os.getpid()` e
    10928 no filtro — excluir o proprio pid nao bastava. O sintoma era mudo:
    log parando nesta linha, sem traceback, codigo de saida -1, e o pedido
    preso em "entregue" ate o prazo estourar.
    """
    subprocess.run(
        ["powershell", "-NoProfile", "-Command",
         f"Get-NetTCPConnection -LocalPort {PORTA_MCP} -State Listen "
         "-ErrorAction SilentlyContinue | "
         "Select-Object -ExpandProperty OwningProcess -Unique | "
         "ForEach-Object { Stop-Process -Id $_ -Force -ErrorAction SilentlyContinue }"],
        capture_output=True, check=False)
    time.sleep(2)


def sobe_o_servidor(raiz: Path) -> None:
    subprocess.Popen(
        ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass",
         "-File", str(raiz / "speedio" / "roda.ps1")],
        creationflags=getattr(subprocess, "CREATE_NEW_CONSOLE", 0))


def cookies_playwright(pedido: dict) -> list[dict]:
    """Monta o formato que o `cookies.json` do upstream guarda."""
    base = {"domain": DOMINIO, "path": "/", "expires": -1,
            "httpOnly": True, "secure": True, "sameSite": "None"}
    fora = [{**base, "name": "li_at", "value": pedido["li_at"]}]
    if pedido.get("jsessionid"):
        # O JSESSIONID viaja entre aspas no LinkedIn; quem copia do devtools
        # costuma trazer sem, e ai o par com o token CSRF nao fecha.
        valor = pedido["jsessionid"]
        if not valor.startswith('"'):
            valor = f'"{valor}"'
        fora.append({**base, "name": "JSESSIONID", "value": valor, "httpOnly": False})
    return fora


async def aplica(pedido: dict) -> tuple[bool, str]:
    from linkedin_mcp_server.config import get_config
    from linkedin_mcp_server.drivers.browser import validate_imported_cookies
    from linkedin_mcp_server.session_state import (
        portable_cookie_path, reset_source_profile, write_source_state,
    )

    perfil = Path(get_config().browser.user_data_dir).expanduser().resolve()
    caminho = portable_cookie_path(perfil)
    caminho.parent.mkdir(parents=True, exist_ok=True)

    # Guarda a sessao que ja estava la antes de encostar nela: se o cookie novo
    # for recusado, o upstream apaga o perfil, e sem esta copia voce sairia de
    # uma sessao boa para nenhuma.
    reserva = None
    if perfil.exists():
        reserva = perfil.parent / f"reserva-{int(time.time())}"
        shutil.copytree(perfil, reserva, dirs_exist_ok=True)

    caminho.write_text(json.dumps(cookies_playwright(pedido), indent=2), encoding="utf-8")
    fala(f"cookies encenados em {caminho}")

    try:
        aceito = await validate_imported_cookies(caminho, perfil)
    except Exception as e:                      # noqa: BLE001
        aceito, erro = False, str(e)
    else:
        erro = ""

    if aceito:
        write_source_state(perfil)
        if reserva:
            shutil.rmtree(reserva, ignore_errors=True)
        return True, "sessão validada no /feed/ do LinkedIn"

    reset_source_profile(perfil)
    if reserva and reserva.exists():
        shutil.rmtree(perfil, ignore_errors=True)
        shutil.move(str(reserva), str(perfil))
        volta = "; a sessão anterior foi devolvida"
    else:
        volta = ""
    motivo = erro or "o LinkedIn não aceitou o cookie (expirado, ou logout remoto)"
    return False, motivo + volta


def uma_rodada(raiz: Path) -> bool:
    try:
        pedido = pega_pedido()
    except urllib.error.URLError as e:
        fala(f"painel fora do ar: {e}")
        return False
    if not pedido:
        return False

    fala("cookie recebido; parando o MCP para aplicar")
    para_o_servidor()
    try:
        ok, detalhe = asyncio.run(aplica(pedido))
    except Exception as e:                      # noqa: BLE001
        ok, detalhe = False, f"falha ao aplicar: {e}"
    fala(("ok: " if ok else "erro: ") + detalhe)
    responde(ok, detalhe)
    sobe_o_servidor(raiz)
    return True


def main() -> None:
    p = argparse.ArgumentParser(description="Aplica o cookie do LinkedIn vindo do painel.")
    p.add_argument("--sempre", action="store_true", help="fica em laço em vez de rodar uma vez")
    p.add_argument("--intervalo", type=int, default=45, help="segundos entre consultas")
    args = p.parse_args()

    if not TOKEN:
        sys.exit("Falta CACA_TOKEN no ambiente.")
    raiz = Path(__file__).resolve().parent.parent

    if not args.sempre:
        uma_rodada(raiz)
        return
    fala(f"em laço, consultando {URL} a cada {args.intervalo}s")
    while True:
        try:
            uma_rodada(raiz)
        except KeyboardInterrupt:
            raise
        except Exception as e:                  # noqa: BLE001
            fala(f"rodada falhou, seguindo: {e}")
        time.sleep(args.intervalo)


if __name__ == "__main__":
    main()
