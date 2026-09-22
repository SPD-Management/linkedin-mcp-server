$env:PYTHONIOENCODING = "utf-8"
$env:PYTHONUTF8 = "1"
$env:Path = "$env:USERPROFILE\.local\bin;$env:Path"
# O painel virou parte do findhu em 2026-09-21; o token no arquivo abaixo e o
# ADMIN_TOKEN de la, nao mais o CACA_TOKEN do Worker morto da Speedio.
$env:CACA_URL = "https://findhu.app/api/admin/caca"
# O token vem de ARQUIVO, nao de variavel de ambiente do sistema: variavel de
# ambiente vaza em listagem de processo, como ja vaza o token do tunnel do
# cloudflared na linha de comando do servico dele.
$tok = "$env:USERPROFILE\.caca-vagas\token.txt"
if (Test-Path $tok) { $env:CACA_TOKEN = (Get-Content $tok -Raw).Trim() }
Set-Location (Split-Path $PSScriptRoot -Parent)
