$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot
if (-not (Test-Path -LiteralPath 'work/public-host.json')) {
    Write-Host 'No active public connection is recorded.'
    exit 0
}
$hostState = Get-Content -LiteralPath 'work/public-host.json' -Raw | ConvertFrom-Json
$runningTunnel = Get-Process -Id $hostState.tunnel_pid -ErrorAction SilentlyContinue
$expectedTunnel = Join-Path $PSScriptRoot 'runtime/cloudflared/cloudflared.exe'
if ($runningTunnel -and $runningTunnel.Path -eq $expectedTunnel) {
    Stop-Process -Id $runningTunnel.Id
    Write-Host 'Public connection closed. The hosting helper will release its temporary sleep prevention.'
} else {
    Write-Host 'The recorded tunnel is no longer running.'
}
