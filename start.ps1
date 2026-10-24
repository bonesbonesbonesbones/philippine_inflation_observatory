param([switch]$Train)
$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
$taskPython = 'C:\Users\Luzan\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe'
$env:PYTHONPATH = "$PSScriptRoot\.packages;$PSScriptRoot"
$env:PYTHONIOENCODING = 'utf-8'
if ($Train) {
    & $taskPython tools/run_notebooks.py
} else {
    & $taskPython -m streamlit run app.py --global.developmentMode false --server.address 127.0.0.1 --server.port 8501 --server.headless true --browser.gatherUsageStats false
}
