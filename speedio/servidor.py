"""O servidor do upstream com UMA ferramenta a mais: `speedio_print`.

Degrau 2 da regra do README: um entrypoint aqui que importa o
`linkedin_mcp_server` e embrulha o que falta, sem tocar em arquivo deles.
Roda com os MESMOS argumentos do `-m linkedin_mcp_server`:

    uv run python speedio/servidor.py --transport streamable-http ...

Por que existe (2026-09-25): o caca-vagas grava 'enviado' quando o
`send_message` diz `sent`, e mais nada prova que a mensagem saiu, por qual
conta e para quem. Depois de cada acao o Worker pede um print da pagina do
proprio browser que agiu e o guarda junto do envio.

A ferramenta NUNCA abre browser nem login: sem Chromium de pe', responde
`sem_navegador`. Abrir um aqui poderia disparar o fluxo de login do upstream,
e um print nao vale o risco de mexer na sessao da conta.
"""

from __future__ import annotations

import base64
from typing import Any

from linkedin_mcp_server import cli_main
from linkedin_mcp_server.drivers import browser as navegador
from linkedin_mcp_server.server_role import ServerRole

_cria_original = cli_main.create_mcp_server


def _cria(*args: Any, **kwargs: Any):
    mcp = _cria_original(*args, **kwargs)
    # Proxy nao tem browser: o print dele seria sempre `sem_navegador`, e o
    # nome colidiria com o do dono se um dia este processo virar proxy.
    if kwargs.get("role", ServerRole.DIRECT).drives_browser:
        mcp.tool(
            name="speedio_print",
            description=(
                "Screenshot (JPEG, base64) of the page the logged-in browser is "
                "showing right now. Read-only; never opens a browser or a login."
            ),
        )(speedio_print)
    return mcp


async def speedio_print(qualidade: int = 60, pagina_inteira: bool = False) -> dict[str, Any]:
    """O que o browser desta conta mostra agora, como JPEG em base64."""
    atual = navegador._browser
    if atual is None:
        return {"status": "sem_navegador", "message": "Nenhum browser aberto nesta conta."}
    pagina = atual.page
    try:
        titulo = await pagina.title()
    except Exception as e:  # pagina fechando: o print ainda pode sair
        titulo = f"<erro: {e}>"
    try:
        # JPEG e nao PNG: a conversa do LinkedIn em PNG passa de 1 MB, e isto
        # atravessa o tunnel e o JSON-RPC inteiro em base64.
        cru = await pagina.screenshot(
            type="jpeg",
            quality=max(20, min(int(qualidade), 90)),
            full_page=bool(pagina_inteira),
        )
    except Exception as e:
        return {"status": "falhou", "message": str(e), "url": pagina.url}
    return {
        "status": "ok",
        "url": pagina.url,
        "title": titulo,
        "bytes": len(cru),
        "jpeg_base64": base64.b64encode(cru).decode("ascii"),
    }


# `cli_main` fez `from ...server import create_mcp_server` no import, entao e'
# o nome DELE que se troca, e nao o do modulo `server`.
cli_main.create_mcp_server = _cria

if __name__ == "__main__":
    cli_main.main()
