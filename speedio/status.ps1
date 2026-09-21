# Estado da sessao. Nao toca no LinkedIn: so olha o perfil no disco.
. "$PSScriptRoot\_ambiente.ps1"
uv run -m linkedin_mcp_server --status @args
