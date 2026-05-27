$ErrorActionPreference = "Stop"
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$repoRoot = Split-Path -Parent $scriptDir
Set-Location $repoRoot

if (-not $env:AI_MV_COMFY_BASE_URL) { $env:AI_MV_COMFY_BASE_URL = "http://127.0.0.1:8000" }
if (-not $env:AI_MV_COMFY_INPUT_DIR) { $env:AI_MV_COMFY_INPUT_DIR = "C:\Users\Desktop\Documents\ComfyUI\input" }
if (-not $env:AI_MV_COMFY_OUTPUT_DIR) { $env:AI_MV_COMFY_OUTPUT_DIR = "C:\Users\Desktop\Documents\ComfyUI\output" }

$env:AI_MV_SMOKE_MODE = "1"
$env:AI_MV_SMOKE_AUDIO_MIN_SEC = "15"
$env:AI_MV_SMOKE_AUDIO_MAX_SEC = "20"

uv run ai-mv preflight @args
