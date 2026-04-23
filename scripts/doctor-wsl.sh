#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=./lib/wsl-env.sh
source "$SCRIPT_DIR/lib/wsl-env.sh"

ai_mv_bootstrap_wsl_env

export AI_MV_WSL_SMOKE_MODE=1
export AI_MV_SMOKE_AUDIO_MIN_SEC=15
export AI_MV_SMOKE_AUDIO_MAX_SEC=20

exec uv run ai-mv doctor "$@"
