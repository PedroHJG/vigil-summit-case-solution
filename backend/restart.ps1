# Reinicia o backend FastAPI (mata quem estiver na porta 8000 e sobe de novo).
# Uso (a partir da pasta backend):  .\restart.ps1
# Necessário após editar o .env (as configs são lidas apenas no startup).
# Utilize esse script na bash do Windows (PowerShell) ou no terminal do VSCode. Não funciona no cmd.exe.

$ErrorActionPreference = "SilentlyContinue"

# 1. Derruba o processo atual da porta 8000 (inclui workers órfãos de --reload)
$conns = Get-NetTCPConnection -LocalPort 8000 -State Listen
foreach ($c in ($conns | Select-Object -ExpandProperty OwningProcess -Unique)) {
    Write-Host "Encerrando processo $c na porta 8000..."
    Stop-Process -Id $c -Force
}
Start-Sleep -Seconds 2

# 2. Sobe o backend com o venv do projeto
Write-Host "Iniciando backend em http://localhost:8000 ..."
& "$PSScriptRoot\.venv\Scripts\python.exe" -m uvicorn main:app --host 0.0.0.0 --port 8000