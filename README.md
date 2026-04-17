# ai-mv

`ai-mv` is a Python 3.11 CLI for generating complete music videos from a single `concept_text` input using local ComfyUI workflows, music generation, and automated review.

## Product direction

The project is evolving toward:
- multi-style music video generation, not a citypop-only tool
- a concept-text-first UX
- final-MV quality as the main success metric
- strong ComfyUI/workflow orchestration
- review and rerender loops that improve weak outputs

The external UX is intentionally simple even though the internal planning and workflow routing are more complex.

## Current pipeline

The current pipeline runs these high-level stages:

1. `audio`
2. `plan`
3. `stills`
4. `clips`
5. `assemble`
6. `review`

In practice this means:
- derive music direction from `concept_text`
- generate music and timing structure
- build a visual plan
- render stills and clips through ComfyUI workflows
- assemble a final MV
- review the output and identify rerender targets

## Requirements

- Python `>=3.11`
- local ComfyUI reachable from this environment
- Codex CLI installed and logged in
- `ffmpeg` and `ffprobe` on `PATH`
- workflow JSON templates in `workflows/`

Default integration values live in `src/ai_mv/core/orchestration/config_defaults.py`.

## Install

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -e .[dev]
```

## Commands

```powershell
ai-mv doctor
ai-mv preflight --concept-text "dreamy synthwave night drive with lonely neon romance"
ai-mv start --concept-text "dreamy synthwave night drive with lonely neon romance"
ai-mv status --run-id 20260406-215500
ai-mv extract-frames --video artifacts/latest_success/final_video.mp4 --output-dir .analysis/final-review --kind final --sample-count 8
ai-mv quality-findings-template --shot-id S001 --shot-id S002 --output .analysis/review-findings.json
```

## WSL Usage

If you run the repo from WSL while ComfyUI stays on Windows, prefer the WSL wrapper scripts instead of the default CLI commands. The wrappers inject WSL-safe values for the ComfyUI host, mounted input/output directories, and Codex path.

### First successful WSL run target

Use this as the initial success envelope:
- concept-text driven run only
- target music duration: 15–20 seconds
- `planning.enable_ia2v=false`
- `planning.enable_flf2v=false`
- still generation + basic i2v clips only
- `./scripts/preflight-wsl.sh` and `./scripts/start-wsl.sh` default to this smoke mode
- add `--full-run` only when you intentionally want the longer path

```bash
./scripts/doctor-wsl.sh
./scripts/preflight-wsl.sh --concept-text 'dreamy synthwave night drive with lonely neon romance'
./scripts/start-wsl.sh --concept-text 'dreamy synthwave night drive with lonely neon romance'
```

Notes:
- the wrappers auto-detect the Windows WSL gateway for `comfyui_base_url`
- they expect ComfyUI input/output under `/mnt/c/Users/Desktop/Documents/ComfyUI/`
- `start-wsl.sh` runs the real generation pipeline and will create outputs / consume time
- do not treat `ia2v`, `flf2v`, perfect identity consistency, or precise sync as first-run pass criteria

## Tests

```powershell
pytest
```
