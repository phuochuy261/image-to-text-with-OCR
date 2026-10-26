$ErrorActionPreference = "Stop"
$env:PYTHONUTF8 = "1"
Set-Location -LiteralPath $PSScriptRoot
if (-not (Test-Path -LiteralPath ".venv\Scripts\python.exe")) {
    throw "Chưa có môi trường. Hãy chạy setup.ps1 trước."
}
& .\.venv\Scripts\python.exe app.py @args
exit $LASTEXITCODE
