# AI-MV

ComfyUI + Codex CLI orchestration for long-form music-video generation.

## Quick Start
```bash
python -m venv .venv
& .\.venv\Scripts\Activate.ps1
python -m pip install -U pip
python -m pip install -e .[dev]
python -m ai_mv.cli.app doctor
python -m ai_mv.cli.app start --profile jpop_citypop
```

`profile` is the main creative input surface.
- `audio.brief`: primary music briefing for the LLM
- `audio.hook_brief`: hook and topline briefing
- `audio.tags`: optional conditioning spine for audio engines
- `audio.language`: lyrics language only
- `visual.brief`: primary visual briefing for the LLM
- `visual.negative`: forbidden visual drift
- `mv.story_world`, `mv.action_vocabulary`, `mv.payoff_style`: section progression and MV behavior
- `mv.avoid`: forbidden MV drift

The planners are now strictly `brief-first`.
- explicit identity/world briefing fields are required
- missing briefing fields fail fast during profile bootstrap
- old tag/guidance inference is not used in the runtime path anymore
- profiles define the world and artistic boundaries, while planners reinterpret them into per-run workflow payloads

Codex CLI expands those inputs into:
- AceStep audio plan
- visual bridge brief
- Lyric timeline and story bible planning
- Shot timeline and Flux 2 reference progression
- WAN motion prompts

Pipeline flow:
- `acestep_music -> lyrics_timeline -> visual_story_bible -> shot_timeline -> shot_router -> flux2_ref_chain -> wan_interpolation -> merge_mux`

Language policy:
- `audio.language` applies to lyrics generation and lyrics validation only
- `genre_description` always stays in English for AceStep conditioning
- visual / TTI / Flux 2 ref / WAN prompts stay in English workflow grammar

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
