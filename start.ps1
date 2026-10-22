$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot
$model = Join-Path $PSScriptRoot 'models/qwen2.5-1.5b-instruct-q4_k_m.gguf'
$server = Get-ChildItem -Path 'runtime/llama' -Filter llama-server.exe -Recurse | Select-Object -First 1
if (-not $server -or -not (Test-Path -LiteralPath $model)) { throw 'Local model runtime or weights are missing. See README.md.' }
$modelReady = $false
try { $modelReady = (Invoke-WebRequest 'http://127.0.0.1:8081/health' -TimeoutSec 2).StatusCode -eq 200 } catch {}
if (-not $modelReady) {
    Start-Process -FilePath $server.FullName -ArgumentList @('-m', ('"' + $model + '"'), '--host','127.0.0.1','--port','8081','-c','4096','-t','8','--parallel','1') -WindowStyle Hidden -RedirectStandardOutput 'work/model.log' -RedirectStandardError 'work/model-error.log'
}
try {
    $apiReady = (Invoke-WebRequest 'http://127.0.0.1:8000/health' -TimeoutSec 2).StatusCode -eq 200
    if ($apiReady) { Write-Host 'Already running: http://127.0.0.1:8000/docs'; exit 0 }
} catch {}
Write-Host 'Starting API at http://127.0.0.1:8000/docs. Model may need a few seconds to load.'
& '.venv/Scripts/python.exe' -m uvicorn geoai.app:app --host 127.0.0.1 --port 8000
