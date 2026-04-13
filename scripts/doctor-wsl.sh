#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd -- "${SCRIPT_DIR}/.." && pwd)"

if ! grep -qi microsoft /proc/version 2>/dev/null && [ ! -e /proc/sys/fs/binfmt_misc/WSLInterop ]; then
  echo "error: doctor-wsl.sh must be run inside WSL" >&2
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

echo "[doctor-wsl] repo=$REPO_ROOT"
echo "[doctor-wsl] comfyui_base_url=http://${GATEWAY_HOST}:8000"
echo "[doctor-wsl] comfyui_input_dir=$COMFY_INPUT_DIR"
echo "[doctor-wsl] comfyui_output_dir=$COMFY_OUTPUT_DIR"
echo "[doctor-wsl] codex_cli_path=$CODEX_BIN"

export AI_MV_WSL_GATEWAY_HOST="$GATEWAY_HOST"
export AI_MV_COMFY_INPUT_DIR="$COMFY_INPUT_DIR"
export AI_MV_COMFY_OUTPUT_DIR="$COMFY_OUTPUT_DIR"
export AI_MV_CODEX_BIN="$CODEX_BIN"

PYTHONPATH=src python3 - <<'PY'
from ai_mv.entrypoints.doctor import run_doctor
import os

cfg = {
    'integrations': {
        'comfyui_base_url': f"http://{os.environ['AI_MV_WSL_GATEWAY_HOST']}:8000",
        'comfyui_input_dir': os.environ['AI_MV_COMFY_INPUT_DIR'],
        'comfyui_output_dir': os.environ['AI_MV_COMFY_OUTPUT_DIR'],
        'codex_cli_path': os.environ['AI_MV_CODEX_BIN'],
        'codex_model': 'gpt-5.4-mini',
        'codex_timeout_structured_sec': 30,
        'workflows_dir': 'workflows',
    },
    'runtime': {
        'template_hash_lock': False,
        'template_hashes': {},
        'interrupt_comfy_before_start': True,
        'clear_comfy_queue_before_start': True,
    },
}
raise SystemExit(run_doctor(cfg))
PY
