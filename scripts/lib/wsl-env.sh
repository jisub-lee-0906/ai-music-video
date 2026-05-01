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

ai_mv_check_single_shared_comfy_backend() {
  if [ "${AI_MV_SKIP_SHARED_COMFY_GUARD:-0}" = "1" ]; then
    echo "[shared-comfy] duplicate-backend guard skipped by AI_MV_SKIP_SHARED_COMFY_GUARD=1" >&2
    return 0
  fi

  local powershell_bin="/mnt/c/Windows/System32/WindowsPowerShell/v1.0/powershell.exe"
  if [ ! -x "$powershell_bin" ]; then
    echo "[shared-comfy] warning: Windows PowerShell not found; skipping duplicate ComfyUI backend guard" >&2
    return 0
  fi

  local owner_mode="${AI_MV_SHARED_COMFY_OWNER_MODE:-desktop}"
  if [ "$owner_mode" != "desktop" ] && [ "$owner_mode" != "any" ]; then
    echo "error: AI_MV_SHARED_COMFY_OWNER_MODE must be 'desktop' or 'any'" >&2
    return 1
  fi

  "$powershell_bin" -NoProfile -Command '
$ErrorActionPreference = "Stop"
$ports = 8000,8001,8002,8188
$ownerMode = "'"$owner_mode"'"

function Get-AncestorSummary($process) {
  $items = @()
  $cursor = $process
  for ($i = 0; $i -lt 12; $i++) {
    if ($null -eq $cursor) { break }
    $items += ("{0}:{1}" -f $cursor.ProcessId, $cursor.Name)
    if ($null -eq $cursor.ParentProcessId -or [int]$cursor.ParentProcessId -le 0) { break }
    $cursor = Get-CimInstance Win32_Process -Filter ("ProcessId = {0}" -f $cursor.ParentProcessId) -ErrorAction SilentlyContinue
  }
  return ($items -join " <- ")
}

function Has-ComfyDesktopAncestor($process) {
  $cursor = $process
  for ($i = 0; $i -lt 12; $i++) {
    if ($null -eq $cursor) { return $false }
    if ([string]$cursor.Name -eq "ComfyUI.exe") { return $true }
    if ($null -eq $cursor.ParentProcessId -or [int]$cursor.ParentProcessId -le 0) { return $false }
    $cursor = Get-CimInstance Win32_Process -Filter ("ProcessId = {0}" -f $cursor.ParentProcessId) -ErrorAction SilentlyContinue
  }
  return $false
}

$listeners = Get-NetTCPConnection -State Listen | Where-Object { $ports -contains $_.LocalPort }
$rows = @()
foreach ($listener in $listeners) {
  $proc = Get-CimInstance Win32_Process -Filter ("ProcessId = {0}" -f $listener.OwningProcess) -ErrorAction SilentlyContinue
  if ($null -eq $proc) { continue }
  $cmd = [string]$proc.CommandLine
  if ($cmd -match "main\.py" -and $cmd -match "ComfyUI") {
    $rows += [pscustomobject]@{
      Port = $listener.LocalPort
      Address = $listener.LocalAddress
      PID = $listener.OwningProcess
      ParentPID = $proc.ParentProcessId
      Created = $proc.CreationDate
      DesktopOwned = Has-ComfyDesktopAncestor $proc
      Ancestors = Get-AncestorSummary $proc
      CommandLine = $cmd
    }
  }
}
if ($rows.Count -gt 1) {
  Write-Host ("error: duplicate ComfyUI backend servers detected. Use exactly one shared backend on port 8000 for Krita/Blender/ai-music-video. Detected: " + (($rows | ForEach-Object { "port=$($_.Port) pid=$($_.PID) parent=$($_.ParentPID) desktop_owned=$($_.DesktopOwned)" }) -join "; "))
  exit 42
}
if ($rows.Count -eq 1 -and [int]$rows[0].Port -ne 8000) {
  Write-Host ("error: ComfyUI backend is listening on port $($rows[0].Port), but ai-music-video shared setup expects canonical port 8000. Reopen a single ComfyUI backend on 8000 or set explicit config intentionally.")
  exit 43
}
if ($rows.Count -eq 1 -and $ownerMode -eq "desktop" -and -not [bool]$rows[0].DesktopOwned) {
  Write-Host ("error: ComfyUI backend on port 8000 is not owned by ComfyUI Desktop. Current owner chain: $($rows[0].Ancestors). For the Desktop-canonical setup, stop the manual/WSL-started backend and launch ComfyUI from the Desktop app. Set AI_MV_SHARED_COMFY_OWNER_MODE=any only for diagnostics or intentional manual backend use.")
  exit 44
}
' || {
    local status=$?
    echo "[shared-comfy] duplicate-backend guard failed; set AI_MV_SKIP_SHARED_COMFY_GUARD=1 only for diagnostics." >&2
    return "$status"
  }
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

  ai_mv_check_single_shared_comfy_backend

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
