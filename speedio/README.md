# speedio/

Tudo o que e nosso mora aqui. **Nenhum arquivo do upstream e editado.**

Arquivo novo nunca da conflito de merge; linha alterada da. Atualizar e:

    git fetch upstream && git merge upstream/main

e deve ser fast-forward em tudo o que e deles. Se der conflito fora de
`speedio/`, alguem quebrou a regra â€” veja `PATCHES.md`.

Se o comportamento do upstream precisar mudar, nesta ordem:

1. variavel de ambiente ou config que ele ja tem;
2. um entrypoint aqui que importa `linkedin_mcp_server` e embrulha o que falta;
3. por ultimo, patch no arquivo deles â€” e entao registrado em `PATCHES.md`
   com o porque, para saber o que reaplicar depois do merge.

## Quem consome isto

O Worker `caca-vagas` (monorepo `rh`, `apps/caca-vagas`), que fala MCP
streamable-HTTP com este servidor atraves de um tunnel cloudflared, atras de
Cloudflare Access. O cliente esta em `apps/caca-vagas/worker/mcp.ts` e usa
`send_message(linkedin_username, message, confirm_send, profile_urn)`.

**Ele confere o `tools/list` antes de cada envio** e falha alto se o nome da
ferramenta ou algum desses parametros sumir. Se um `git merge upstream/main`
mudar essa assinatura, o envio para de funcionar com a mensagem certa na tela â€”
e nao manda argumento errado para um browser logado, que e pior.

## A maquina

`diogo-win11.casa.internal` (Tailscale, 100.106.47.39), usuario `speedio`.
Windows 11 Pro build 22621, Chrome 139. O `uv` traz o Python 3.12+ que o
`pyproject.toml` exige â€” o Python do sistema e 3.10 e nao serve.

O servidor **nao** pluga no Chrome aberto: ele importa os cookies do LinkedIn do
perfil do Chrome (`pywin32` decifra via DPAPI, por isso tem de rodar como o
MESMO usuario dono do perfil) e sobe um Chromium proprio com `patchright`.

## O que ja esta de pe (2026-09-21)

- `uv 0.12.17` instalado; `uv sync` traz Python 3.13.15. O Python do sistema e
  3.10 e **nao serve**: o `pyproject.toml` exige `>=3.12.4`.
- Servidor sobe e responde em `http://127.0.0.1:8080/mcp`. Conferido na mao:
  `initialize` devolve **`text/event-stream`** (nao JSON puro — quem le a
  resposta precisa entender SSE), manda `mcp-session-id` no cabecalho, e
  `tools/list` traz 19 ferramentas com `send_message(linkedin_username,
  message, confirm_send, profile_urn)`.
- `PYTHONIOENCODING=utf-8` em `_ambiente.ps1`: sem isso o upstream **derruba o
  processo** com `UnicodeEncodeError` ao imprimir o emoji de "sem sessao", porque
  o console do Windows e cp1252. Remendo por variavel de ambiente, degrau 1 da
  regra acima — nenhum arquivo deles foi tocado.

## O que falta

1. **Sessao do LinkedIn.** Nenhum dos 6 perfis do Chrome desta maquina esta
   logado, entao `--import-from-browser chrome` nao acha nada. Ou se loga no
   Chrome de la e roda o import, ou se roda `speedio\login.ps1` (browser
   visivel, precisa de alguem na maquina).
2. **Hostname publico no tunnel.** Ja existe um tunnel rodando como servico do
   Windows, gerenciado remotamente, na conta Cloudflare da Speedio. Nao precisa
   de `cloudflared tunnel login`: basta acrescentar no painel Zero Trust o
   hostname `mcp-linkedin.speedio.com.br` -> `http://127.0.0.1:8080`. O
   `config.yml` daqui e so o plano B, para um tunnel local.
   Depois: aplicacao do Access nesse hostname + service token, cujo id/segredo
   viram `CF_ACCESS_CLIENT_ID` / `CF_ACCESS_CLIENT_SECRET` do Worker.

> O token do tunnel aparece **cru na linha de comando do servico** (`Get-CimInstance
> Win32_Service`). Qualquer um que liste processos nessa maquina o le. Se um dia
> essa maquina for compartilhada, rotacione o tunnel.

## O print de cada envio (2026-09-25)

As tarefas das contas sobem `speedio\servidor.py` e nao mais
`-m linkedin_mcp_server`: e o mesmo servidor, com os mesmos argumentos, mais a
ferramenta `speedio_print` (JPEG em base64 da pagina que o browser da conta
mostra agora). O caca-vagas a chama logo depois de cada `send_message` e
`connect_with_person` e guarda a imagem com o envio — e a prova de que a
mensagem saiu, por qual conta e para quem. Ela nunca abre browser nem login:
sem Chromium de pe', responde `sem_navegador`.
