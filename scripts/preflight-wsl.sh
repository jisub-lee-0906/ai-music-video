#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd -- "${SCRIPT_DIR}/.." && pwd)"

usage() {
  cat <<'EOF'
Usage: ./scripts/preflight-wsl.sh [--run-id ID] [--concept-text TEXT]

WSL-only wrapper for ai-mv preflight that injects WSL-safe ComfyUI/Codex paths.
EOF
}

RUN_ID=""
CONCEPT_TEXT=""
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

if ! grep -qi microsoft /proc/version 2>/dev/null && [ ! -e /proc/sys/fs/binfmt_misc/WSLInterop ]; then
  echo "error: preflight-wsl.sh must be run inside WSL" >&2
  exit 1
fi

GATEWAY_HOST="$(ip route show default 2>/dev/null | awk '/^default via / {print $3; exit}')"
if [ -z "${GATEWAY_HOST}" ]; then
  echo "error: could not determine the Windows WSL gateway from 'ip route show default'" >&2
  exit 1
fi

COMFY_INPUT_DIR="/mnt/c/Users/Desktop/Documents/ComfyUI/input"
COMFY_OUTPUT_DIR="/mnt/c/Users/Desktop/Documents/ComfyUI/output"
for path in "$COMFY_INPUT_DIR" "$COMFY_OUTPUT_DIR"; do
  if [ ! -d "$path" ]; then
    echo "error: required ComfyUI directory not found: $path" >&2
    exit 1
  fi
done

CODEX_BIN="$(command -v codex || true)"
if [ -z "${CODEX_BIN}" ] && [ -x "/home/jisub-lee/.hermes/node/bin/codex" ]; then
  CODEX_BIN="/home/jisub-lee/.hermes/node/bin/codex"
fi
if [ -z "${CODEX_BIN}" ]; then
  echo "error: codex executable not found on PATH or fallback path" >&2
  exit 1
fi

for tool in python3 ffmpeg ffprobe; do
  if ! command -v "$tool" >/dev/null 2>&1; then
    echo "error: required command not found on PATH: $tool" >&2
    exit 1
  fi
done

cd "$REPO_ROOT"

echo "[preflight-wsl] repo=$REPO_ROOT"
echo "[preflight-wsl] comfyui_base_url=http://${GATEWAY_HOST}:8000"
echo "[preflight-wsl] comfyui_input_dir=$COMFY_INPUT_DIR"
echo "[preflight-wsl] comfyui_output_dir=$COMFY_OUTPUT_DIR"
echo "[preflight-wsl] codex_cli_path=$CODEX_BIN"
[ -n "$RUN_ID" ] && echo "[preflight-wsl] run_id=$RUN_ID"
[ -n "$CONCEPT_TEXT" ] && echo "[preflight-wsl] concept_text=$CONCEPT_TEXT"

export AI_MV_WSL_GATEWAY_HOST="$GATEWAY_HOST"
export AI_MV_COMFY_INPUT_DIR="$COMFY_INPUT_DIR"
export AI_MV_COMFY_OUTPUT_DIR="$COMFY_OUTPUT_DIR"
export AI_MV_CODEX_BIN="$CODEX_BIN"
export AI_MV_RUN_ID="$RUN_ID"
export AI_MV_CONCEPT_TEXT="$CONCEPT_TEXT"

PYTHONPATH=src python3 - <<'PY'
import os
from ai_mv.entrypoints.preflight import run_preflight_entry
from ai_mv.core.orchestration.config_defaults import apply_defaults as _apply_defaults
from ai_mv.core.orchestration.config_defaults import default_config as _default_config
from ai_mv.entrypoints import preflight as preflight_entry


def _wsl_default_config() -> dict:
    cfg = _default_config()
    cfg['integrations']['comfyui_base_url'] = f"http://{os.environ['AI_MV_WSL_GATEWAY_HOST']}:8000"
    cfg['integrations']['comfyui_input_dir'] = os.environ['AI_MV_COMFY_INPUT_DIR']
    cfg['integrations']['comfyui_output_dir'] = os.environ['AI_MV_COMFY_OUTPUT_DIR']
    cfg['integrations']['codex_cli_path'] = os.environ['AI_MV_CODEX_BIN']
    cfg['integrations']['codex_model'] = 'gpt-5.4-mini'
    cfg['integrations']['codex_timeout_structured_sec'] = 30
    cfg['integrations']['workflows_dir'] = 'workflows'
    return cfg


def _wsl_apply_defaults(config: dict) -> None:
    _apply_defaults(config)
    config['integrations']['comfyui_base_url'] = f"http://{os.environ['AI_MV_WSL_GATEWAY_HOST']}:8000"
    config['integrations']['comfyui_input_dir'] = os.environ['AI_MV_COMFY_INPUT_DIR']
    config['integrations']['comfyui_output_dir'] = os.environ['AI_MV_COMFY_OUTPUT_DIR']
    config['integrations']['codex_cli_path'] = os.environ['AI_MV_CODEX_BIN']
    config['integrations']['codex_model'] = 'gpt-5.4-mini'
    config['integrations']['codex_timeout_structured_sec'] = 30
    config['integrations']['workflows_dir'] = 'workflows'


preflight_entry.default_config = _wsl_default_config
preflight_entry.apply_defaults = _wsl_apply_defaults

raise SystemExit(run_preflight_entry(os.environ['AI_MV_RUN_ID'] or None, os.environ['AI_MV_CONCEPT_TEXT'] or None))
PY
