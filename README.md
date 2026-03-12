# AI-MV

ComfyUI + Codex CLI orchestration for long-form music-video generation.

## Quick Start
```bash
pip install -e .[dev]
ai-mv start --profile jpop_citypop
```

`profile` is the main creative input surface.
- `audio.tags`: audio/music direction
- `audio.language`: lyrics language only
- `style.guidance`: visual direction

Codex CLI expands those inputs into:
- AceStep audio plan
- visual bridge brief
- TTI master anchor and shot blueprints
- USO keyframe progression
- WAN motion prompts

Pipeline flow:
- `acestep_music -> visual_bridge -> tti_anchor -> uso_chain -> wan_interpolation -> merge_mux`

Language policy:
- `audio.language` applies to lyrics generation and lyrics validation only
- `genre_description` always stays in English for AceStep conditioning
- visual / TTI / USO / WAN prompts stay in English workflow grammar

## Commands
- `ai-mv start [--run-id <id>] [--profile <name>]`
- `ai-mv doctor`
- `ai-mv status --run-id <id>`

## Doctor Checks
- local ComfyUI base URL and input/output directories
- Codex CLI readiness
- workflow template files
- `ffmpeg` and `ffprobe` on `PATH`

## Core Paths
- profiles: creative profiles
- workflows: ComfyUI API workflow exports
- artifacts/runs: per-run user-facing summary, manifest, dashboard, prompt preview, and workflow input preview
- artifacts/latest: latest run summary, manifest, dashboard, prompt preview, and workflow input preview
- artifacts/reports: planner experiments and ad-hoc quality reports
- artifacts/runs_state: internal snapshots and orchestration state

## Media Outputs
Generated media is written under ComfyUI output, not under project artifacts:
- `anchors/`
- `keyframes/`
- `clips/`
- `music/`

Artifacts are for state, previews, summaries, and reports.
