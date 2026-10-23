$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot
$runtimeConfig = Get-Content -LiteralPath (Join-Path $PSScriptRoot 'submission/runtime_config.json') -Raw | ConvertFrom-Json
if ($runtimeConfig.parameter_count -gt 3000000000) { throw 'Model exceeds the rulebook size limit.' }
$modelName = ($runtimeConfig.base_model -split '/')[-1]
$model = Join-Path (Join-Path $PSScriptRoot 'models') $runtimeConfig.gguf_file
$server = Get-ChildItem -Path 'runtime/llama' -Filter llama-server.exe -Recurse | Select-Object -First 1
if (-not $server -or -not (Test-Path -LiteralPath $model)) { throw 'Local model runtime or weights are missing. See README.md.' }
$modelReady = $false
try {
    $modelReady = (Invoke-WebRequest 'http://127.0.0.1:8081/health' -TimeoutSec 2).StatusCode -eq 200
    if ($modelReady) {
        $loadedModels = Invoke-RestMethod 'http://127.0.0.1:8081/v1/models' -TimeoutSec 2
        if ($modelName -notin $loadedModels.data.id) { throw 'A different model is using port 8081. Stop that model before starting this project.' }
    }
} catch {
    if ($_.Exception.Message -like 'A different model*') { throw }
}
if (-not $modelReady) {
    Start-Process -FilePath $server.FullName -ArgumentList @('-m', ('"' + $model + '"'), '--host','127.0.0.1','--port','8081','-c','4096','-t','8','--parallel','1','--alias',$modelName,'--reasoning-budget','0','--reasoning','off') -WindowStyle Hidden -RedirectStandardOutput 'work/model.log' -RedirectStandardError 'work/model-error.log'
}
try {
    $apiState = Invoke-RestMethod 'http://127.0.0.1:8000/health' -TimeoutSec 2
    $apiReady = $apiState.model -eq $modelName -and $apiState.model_ready
    if ($apiReady) { Write-Host 'Already running: http://127.0.0.1:8000/'; exit 0 }
} catch {}
Write-Host 'Starting website at http://127.0.0.1:8000/. Model may need a few seconds to load.'
& '.venv/Scripts/python.exe' -m uvicorn geoai.app:app --host 127.0.0.1 --port 8000
