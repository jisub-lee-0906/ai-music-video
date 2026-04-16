#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
GATEWAY_HOST="$(ip route show default | awk '/^default via / {print $3; exit}')"
CODEX_BIN="/home/jisub-lee/.hermes/node/bin/codex"

export PATH="/home/jisub-lee/.hermes/node/bin:$PATH"
export AI_MV_CODEX_BIN="$CODEX_BIN"
export AI_MV_COMFY_BASE_URL="http://${GATEWAY_HOST}:8000"
export AI_MV_COMFY_INPUT_DIR="/mnt/c/Users/Desktop/Documents/ComfyUI/input"
export AI_MV_COMFY_OUTPUT_DIR="/mnt/c/Users/Desktop/Documents/ComfyUI/output"
export AI_MV_WSL_SMOKE_MODE=1
export AI_MV_SMOKE_AUDIO_MIN_SEC=15
export AI_MV_SMOKE_AUDIO_MAX_SEC=20

exec uv run ai-mv preflight "$@"
