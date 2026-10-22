$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot
if (Test-Path -LiteralPath 'work/public-host.json') {
    $hostState = Get-Content -LiteralPath 'work/public-host.json' -Raw | ConvertFrom-Json
    $runningTunnel = Get-Process -Id $hostState.tunnel_pid -ErrorAction SilentlyContinue
    $expectedTunnel = Join-Path $PSScriptRoot 'runtime/cloudflared/cloudflared.exe'
    if ($runningTunnel -and $runningTunnel.Path -eq $expectedTunnel) {
        Write-Host ('Already public: ' + $hostState.url + '/docs')
        exit 0
    }
}
& '.venv/Scripts/python.exe' -u deployment/public.py
