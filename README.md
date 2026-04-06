# ai-mv

`ai-mv` is a Python 3.11 CLI that orchestrates an AI music-video pipeline around local ComfyUI workflows and Codex CLI planning. It takes a director brief in `profiles/*.yaml`, generates music and planning artifacts, renders image/video segments through ComfyUI, and muxes the final video with `ffmpeg`.

## What This Project Does

The main pipeline in `src/ai_mv/core/orchestration/pipeline.py` runs these stages in order:

1. `acestep_music`
2. `lyrics_timeline`
3. `scene_outline`
4. `shot_density_refiner`
5. `direction_plan`
6. `prompt_plan`
7. `backend_preview`
8. `tti_anchor`
9. `flux2_ref_chain`
10. `wan_interpolation`
11. `merge_mux`

In practice, that means:

- a brief is loaded from `profiles/`
- audio and section structure are planned first
- scene and shot plans are derived from the audio structure
- prompt contracts are prepared for backend workflows
- ComfyUI workflows generate anchor images, reference frames, and interpolated clips
- `ffmpeg` merges the rendered clips with the generated audio into `final_mv.mp4`

## Requirements

The code currently assumes a local Windows-oriented setup:

- Python `>=3.11`
- local ComfyUI reachable at `http://127.0.0.1:8188`
- valid ComfyUI input/output directories
- Codex CLI installed and logged in
- `ffmpeg` and `ffprobe` available on `PATH`
- workflow JSON templates present in `workflows/`

The default integration values live in `src/ai_mv/core/orchestration/config_defaults.py`. Out of the box they point to:

- `C:\Users\Desktop\Documents\ComfyUI\input`
- `C:\Users\Desktop\Documents\ComfyUI\output`
- `workflows/`

If your environment differs, update the defaults or provide the matching local setup.

## Install

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -e .[dev]
```

## Quick Start

Run environment checks first:

```powershell
ai-mv doctor
```

Run a dry planning pass without backend rendering:

```powershell
ai-mv preflight --brief director_brief_example
```

Run the full pipeline:

```powershell
ai-mv start --brief director_brief_example
```

Check a previous run:

```powershell
ai-mv status --run-id 20260406-215500
```

## CLI Commands

The CLI is defined in `src/ai_mv/cli/args.py`.

- `ai-mv start [--run-id <id>] [--brief <name>]`
  Runs `doctor`, clears/interrupts the ComfyUI queue if enabled, creates a run directory, and executes the full pipeline.
- `ai-mv preflight [--run-id <id>] [--brief <name>]`
  Builds preview artifacts for the planning stages without running the render stages.
- `ai-mv tti [--run-id <id>] [--brief <name>]`
  Runs a text-to-image probe for the master anchor prompt and writes probe outputs under `artifacts/tti_probe/`.
- `ai-mv ref-probe --ref <path> --prompt <text> [--run-id <id>] [--brief <name>]`
  Runs a single reference-frame probe against a provided reference image.
- `ai-mv ref-probe-batch --ref <path> --prompts-file <path> [--run-id <id>] [--brief <name>]`
  Runs a batch of reference probes from a prompt list file.
- `ai-mv doctor`
  Verifies runtime prerequisites, Codex login, and ComfyUI availability.
- `ai-mv status --run-id <id>`
  Prints the saved status for a run.

`run_id` values are restricted to letters, numbers, `.`, `_`, and `-`.

## Director Briefs

The pipeline loads a brief from `profiles/<name>.yaml`. The bootstrap logic is in `src/ai_mv/core/orchestration/bootstrap_guard.py`.

The included example is `profiles/director_brief_example.yaml`. It defines three major sections:

- `audio`: song language, tags, hook direction, section bar overrides, and audio briefing text
- `visual`: story premise, world rules, section story roles, and section event scripts
- `character`: heroine identity, continuity hooks, wardrobe guidance, and reference consistency rules

Required fields are enforced in `src/ai_mv/core/director_brief.py`.

## Output Layout

Two artifact trees are maintained:

- `artifacts/runs/`
  Per-run published artifacts for full pipeline runs
- `artifacts/runs_state/`
  Snapshot state for full pipeline runs

Preflight uses:

- `artifacts/preflight/`
- `artifacts/preflight_state/`

The publisher also maintains:

- `artifacts/latest/`
- `artifacts/latest_success/`

Typical files written per run include:

- `manifest.json`
- `run_summary.json`
- prompt previews
- workflow input previews
- quality review artifacts
- `final_mv.mp4` for successful full runs

## Workflow Templates

The project expects these ComfyUI workflow templates:

- `audio_ace_step_1_5_split_4b.json`
- `image_flux2_text_to_image.json`
- `image_flux2.json`
- `video_wan2_2_14B_flf2v.json`

They are referenced from `src/ai_mv/core/workflow_names.py` and validated by the doctor/preflight flow.

## Development

Run tests with:

```powershell
pytest
```

The repository currently includes unit, integration, regression, and placeholder performance tests under `tests/`.
