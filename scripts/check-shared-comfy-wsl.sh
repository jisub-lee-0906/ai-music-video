#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=./lib/wsl-env.sh
source "$SCRIPT_DIR/lib/wsl-env.sh"

ai_mv_require_wsl

echo "[shared-comfy] WSL gateway: $(ai_mv_detect_gateway_host)"
echo "[shared-comfy] expected ai-music-video URL: http://$(ai_mv_detect_gateway_host):8000"
echo "[shared-comfy] checking for duplicate Windows ComfyUI backend servers..."
echo "[shared-comfy] owner mode: ${AI_MV_SHARED_COMFY_OWNER_MODE:-desktop}"

ai_mv_check_single_shared_comfy_backend

if [ "${AI_MV_SKIP_SHARED_COMFY_GUARD:-0}" = "1" ]; then
  echo "[shared-comfy] skipped: duplicate-backend guard was bypassed for diagnostics."
elif [ "${AI_MV_SHARED_COMFY_OWNER_MODE:-desktop}" = "desktop" ]; then
  echo "[shared-comfy] OK: exactly one canonical Desktop-owned ComfyUI backend may be used on port 8000."
else
  echo "[shared-comfy] OK: at most one ComfyUI backend is listening, and the canonical backend is port 8000."
fi
