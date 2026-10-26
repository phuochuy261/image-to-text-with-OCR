param([string]$PythonExe = "python")
$ErrorActionPreference = "Stop"
$env:PYTHONUTF8 = "1"
Set-Location -LiteralPath $PSScriptRoot
if (-not (Test-Path -LiteralPath ".venv\Scripts\python.exe")) {
    & $PythonExe -m venv .venv
    if ($LASTEXITCODE -ne 0) { throw "Không tạo được môi trường. Cần Python 3.10–3.12." }
}
& .\.venv\Scripts\python.exe -m pip install -r requirements.txt
if ($LASTEXITCODE -ne 0) { throw "Cài thư viện thất bại. Kiểm tra mạng và phiên bản Python." }
& .\.venv\Scripts\python.exe scripts\make_demo.py
if ($LASTEXITCODE -ne 0) { throw "Chưa tạo được ảnh mẫu. Kiểm tra font Arial." }
Write-Host "Xong. Chạy: .\.venv\Scripts\python.exe app.py"
