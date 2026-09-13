$ErrorActionPreference = 'Stop'
$scopeRoot = Split-Path -Parent $PSScriptRoot
Set-Location -LiteralPath $scopeRoot
$env:SCOPEPROOF_MODEL = 'qwen3:4b-instruct'
$env:OLLAMA_HOST = 'http://127.0.0.1:11434'
$env:OTEL_SDK_DISABLED = 'true'
& "$scopeRoot\.venv\Scripts\python.exe" -m uvicorn scopeproof.server:app --host 127.0.0.1 --port 8791
