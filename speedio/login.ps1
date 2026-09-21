# Primeira vez: minta a sessao do LinkedIn a mao, com browser visivel.
# Depois disto o roda.ps1 sobe headless usando a sessao guardada.
. "$PSScriptRoot\_ambiente.ps1"
uv run -m linkedin_mcp_server --login @args
