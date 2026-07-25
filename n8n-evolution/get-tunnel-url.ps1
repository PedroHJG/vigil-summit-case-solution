# Reinicia o Cloudflare Tunnel e mostra a nova URL publica da Evolution API.
# Uso (a partir da pasta n8n-evolution):  .\get-tunnel-url.ps1
#
# Necessario sempre que os containers forem reiniciados: o Quick Tunnel
# (gratuito, sem conta) gera uma URL ALEATORIA NOVA a cada restart do
# container cloudflared. Depois de rodar este script, cole a URL impressa
# em Render -> seu servico -> Environment -> EVOLUTION_API_URL.

Write-Host "Reiniciando o tunel..." -ForegroundColor Cyan
docker compose restart cloudflared | Out-Null

Write-Host "Aguardando nova sessao do tunel..." -ForegroundColor Cyan
Start-Sleep -Seconds 8

$logs = docker compose logs cloudflared --tail 30
$match = $logs | Select-String -Pattern "https://[a-z0-9-]+\.trycloudflare\.com" | Select-Object -Last 1

if (-not $match) {
    Write-Host "Nao encontrei a URL ainda. Rode de novo em alguns segundos:" -ForegroundColor Yellow
    Write-Host "  docker compose logs cloudflared --tail 30" -ForegroundColor Yellow
    exit 1
}

$url = [regex]::Match($match.Line, "https://[a-z0-9-]+\.trycloudflare\.com").Value

# Confirma que o tunel esta respondendo de verdade antes de anunciar sucesso
try {
    $resp = Invoke-WebRequest -Uri $url -TimeoutSec 15 -UseBasicParsing
    $ok = $resp.StatusCode -eq 200
} catch {
    $ok = $false
}

Write-Host ""
if ($ok) {
    Write-Host "Tunel ativo e respondendo:" -ForegroundColor Green
} else {
    Write-Host "URL encontrada, mas ainda nao respondeu (aguarde mais alguns segundos e teste de novo):" -ForegroundColor Yellow
}
Write-Host $url -ForegroundColor White
Write-Host ""
Write-Host "Cole isso no Render -> Environment -> EVOLUTION_API_URL" -ForegroundColor Cyan