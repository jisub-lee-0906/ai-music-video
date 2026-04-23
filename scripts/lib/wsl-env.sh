#!/usr/bin/env bash
set -euo pipefail

ai_mv_wsl_repo_root() {
  local source_path="${BASH_SOURCE[0]}"
  local repo_root
  repo_root="$(cd -- "$(dirname -- "$source_path")/../.." && pwd)"
  printf '%s\n' "$repo_root"
}

ai_mv_require_wsl() {
  if ! grep -qi microsoft /proc/version 2>/dev/null && [ ! -e /proc/sys/fs/binfmt_misc/WSLInterop ]; then
    echo "error: this wrapper must be run inside WSL" >&2
    exit 1
  fi
}

ai_mv_detect_gateway_host() {
  ip route show default 2>/dev/null | awk '/^default via / {print $3; exit}'
}

ai_mv_detect_codex_bin() {
  local codex_bin
  codex_bin="$(command -v codex || true)"
  if [ -z "$codex_bin" ] && [ -x "$HOME/.hermes/node/bin/codex" ]; then
    codex_bin="$HOME/.hermes/node/bin/codex"
  fi
  printf '%s\n' "$codex_bin"
}

ai_mv_detect_python_bin() {
  local repo_root="$1"
  local venv_python="$repo_root/.venv/bin/python"
  local venv_python3="$repo_root/.venv/bin/python3"
  if [ -x "$venv_python" ]; then
    printf '%s\n' "$venv_python"
    return 0
  fi
  if [ -x "$venv_python3" ]; then
    printf '%s\n' "$venv_python3"
    return 0
  fi
  command -v python3 || true
}

ai_mv_require_tool() {
  local tool="$1"
  if ! command -v "$tool" >/dev/null 2>&1; then
    echo "error: required command not found on PATH: $tool" >&2
    exit 1
  fi
}

ai_mv_bootstrap_wsl_env() {
  ai_mv_require_wsl

  export AI_MV_REPO_ROOT="$(ai_mv_wsl_repo_root)"
  export AI_MV_PYTHON_BIN="$(ai_mv_detect_python_bin "$AI_MV_REPO_ROOT")"
  if [ -z "${AI_MV_PYTHON_BIN}" ]; then
    echo "error: python executable not found (.venv/bin/python preferred, fallback python3 missing)" >&2
    exit 1
  fi
  export AI_MV_WSL_GATEWAY_HOST="$(ai_mv_detect_gateway_host)"
  if [ -z "${AI_MV_WSL_GATEWAY_HOST}" ]; then
    echo "error: could not determine the Windows WSL gateway from 'ip route show default'" >&2
    exit 1
  fi

  export AI_MV_COMFY_INPUT_DIR="/mnt/c/Users/Desktop/Documents/ComfyUI/input"
  export AI_MV_COMFY_OUTPUT_DIR="/mnt/c/Users/Desktop/Documents/ComfyUI/output"
  for path in "$AI_MV_COMFY_INPUT_DIR" "$AI_MV_COMFY_OUTPUT_DIR"; do
    if [ ! -d "$path" ]; then
      echo "error: required ComfyUI directory not found: $path" >&2
      exit 1
    fi
  done

  export AI_MV_CODEX_BIN="$(ai_mv_detect_codex_bin)"
  if [ -z "${AI_MV_CODEX_BIN}" ]; then
    echo "error: codex executable not found on PATH or fallback path" >&2
    exit 1
  fi

  for tool in ffmpeg ffprobe; do
    ai_mv_require_tool "$tool"
  done
}

ai_mv_print_wsl_env() {
  local label="$1"
  echo "[$label] repo=$AI_MV_REPO_ROOT"
  echo "[$label] python_bin=$AI_MV_PYTHON_BIN"
  echo "[$label] comfyui_base_url=http://${AI_MV_WSL_GATEWAY_HOST}:8000"
  echo "[$label] comfyui_input_dir=$AI_MV_COMFY_INPUT_DIR"
  echo "[$label] comfyui_output_dir=$AI_MV_COMFY_OUTPUT_DIR"
  echo "[$label] codex_cli_path=$AI_MV_CODEX_BIN"
}
