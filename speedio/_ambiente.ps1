$env:PYTHONIOENCODING = "utf-8"
$env:PYTHONUTF8 = "1"
$env:Path = "$env:USERPROFILE\.local\bin;$env:Path"
Set-Location (Split-Path $PSScriptRoot -Parent)
