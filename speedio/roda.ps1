# Sobe o MCP do LinkedIn em HTTP, para o tunnel publicar.
#
# `--transport streamable-http` e o que o Worker fala; o stdio nao serve porque
# quem chama esta do outro lado do mundo. Escuta so em 127.0.0.1: quem expoe e
# o cloudflared, atras de Cloudflare Access.
. "$PSScriptRoot\_ambiente.ps1"
uv run -m linkedin_mcp_server --transport streamable-http --host 127.0.0.1 --port 8080 --path /mcp @args
