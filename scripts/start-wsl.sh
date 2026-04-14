#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=lib/wsl-env.sh
source "$SCRIPT_DIR/lib/wsl-env.sh"

usage() {
  cat <<'EOF'
Usage: ./scripts/start-wsl.sh [--run-id ID] [--concept-text TEXT] [--full-run]

WSL-only wrapper for ai-mv start that injects WSL-safe ComfyUI/Codex paths.
Defaults to smoke mode (15-20s audio, ia2v/flf2v disabled). Use --full-run to disable smoke mode.
EOF
}

RUN_ID=""
CONCEPT_TEXT=""
SMOKE_MODE=1
while [ "$#" -gt 0 ]; do
  case "$1" in
    --run-id)
      [ "$#" -ge 2 ] || { echo "error: --run-id requires a value" >&2; exit 1; }
      RUN_ID="$2"
      shift 2
      ;;
    --concept-text)
      [ "$#" -ge 2 ] || { echo "error: --concept-text requires a value" >&2; exit 1; }
      CONCEPT_TEXT="$2"
      shift 2
      ;;
    --full-run)
      SMOKE_MODE=0
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "error: unknown argument: $1" >&2
      usage >&2
      exit 1
      ;;
  esac
done

ai_mv_bootstrap_wsl_env
cd "$AI_MV_REPO_ROOT"
export AI_MV_WSL_SMOKE_MODE="$SMOKE_MODE"
if [ "$SMOKE_MODE" = "1" ]; then
  export AI_MV_SMOKE_AUDIO_MIN_SEC="15"
  export AI_MV_SMOKE_AUDIO_MAX_SEC="20"
fi
ai_mv_print_wsl_env "start-wsl"
[ "$SMOKE_MODE" = "1" ] && echo "[start-wsl] mode=smoke (15-20s, ia2v/flf2v disabled)"
[ "$SMOKE_MODE" = "0" ] && echo "[start-wsl] mode=full-run"
[ -n "$RUN_ID" ] && echo "[start-wsl] run_id=$RUN_ID"
[ -n "$CONCEPT_TEXT" ] && echo "[start-wsl] concept_text=$CONCEPT_TEXT"

echo "[start-wsl] warning: this command runs the real generation pipeline and may create outputs / consume time." >&2

CMD=("$AI_MV_PYTHON_BIN" -m ai_mv.cli.app start)
[ -n "$RUN_ID" ] && CMD+=(--run-id "$RUN_ID")
[ -n "$CONCEPT_TEXT" ] && CMD+=(--concept-text "$CONCEPT_TEXT")

PYTHONPATH=src "${CMD[@]}"
