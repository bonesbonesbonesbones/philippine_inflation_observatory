param([switch]$Train)
$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
$taskPython = Join-Path $PSScriptRoot '.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $taskPython)) {
    throw 'Create the project environment with: python -m venv .venv; then run .venv\Scripts\python.exe -m pip install -r requirements.txt'
}
$env:PYTHONPATH = $PSScriptRoot
$env:PYTHONIOENCODING = 'utf-8'
if ($Train) {
    & $taskPython tools/run_notebooks.py
} else {
    & $taskPython -m streamlit run app.py --global.developmentMode false --server.address 127.0.0.1 --server.port 8501 --server.headless true --browser.gatherUsageStats false
}
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
