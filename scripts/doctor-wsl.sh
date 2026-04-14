#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=lib/wsl-env.sh
source "$SCRIPT_DIR/lib/wsl-env.sh"

ai_mv_bootstrap_wsl_env
cd "$AI_MV_REPO_ROOT"
ai_mv_print_wsl_env "doctor-wsl"

PYTHONPATH=src "$AI_MV_PYTHON_BIN" -m ai_mv.cli.app doctor
