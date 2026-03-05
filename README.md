# AI-MV

ComfyUI + Ollama orchestration for long-form music-video generation.

## Quick Start
```bash
pip install -e .[dev]
ai-mv start --config configs/default.yaml
```

## Commands
- `ai-mv start --config <yaml> [--run-id <id>]`
- `ai-mv run-batch --config <yaml>`
- `ai-mv doctor --config <yaml>`
- `ai-mv status --run-id <id>`

## Core Paths
- configs: runtime policies and profiles
- workflows: ComfyUI API workflow exports
- artifacts/runs_state: run snapshots and manifests
- artifacts/reports: summaries and release readiness
