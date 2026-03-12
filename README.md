# AI-MV

ComfyUI + Ollama orchestration for long-form music-video generation.

## Quick Start
```bash
pip install -e .[dev]
ai-mv start --profile jpop_citypop
```

`profile` is the main creative input surface.
- `audio.tags`: audio/music direction
- `style.guidance`: visual direction

Ollama expands those inputs into:
- AceStep audio plan
- visual bridge brief
- TTI master anchor and shot blueprints
- USO keyframe progression
- WAN motion prompts

Pipeline flow:
- `acestep_music -> visual_bridge -> tti_anchor -> uso_chain -> wan_interpolation -> merge_mux`

## Commands
- `ai-mv start [--run-id <id>] [--profile <name>]`
- `ai-mv doctor`
- `ai-mv status --run-id <id>`

## Doctor Checks
- local ComfyUI base URL and input/output directories
- configured Ollama model presence
- workflow template files
- `ffmpeg` and `ffprobe` on `PATH`

## Core Paths
- profiles: creative profiles
- workflows: ComfyUI API workflow exports
- artifacts/runs_state: run snapshots and manifests
- artifacts/reports: summaries
