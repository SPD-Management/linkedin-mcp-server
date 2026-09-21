# Aplica o cookie que o painel mandou. Sem --sempre, roda uma vez e sai
# (e assim que a Tarefa Agendada deve chama-lo, de minuto em minuto).
. "$PSScriptRoot\_ambiente.ps1"
if (-not $env:CACA_TOKEN) { Write-Error "Falta CACA_TOKEN no ambiente da maquina."; exit 1 }
uv run python speedio\agente.py @args
