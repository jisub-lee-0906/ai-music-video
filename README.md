# ai-mv

`ai-mv` is a Python 3.11 CLI for generating music-video assets with local ComfyUI workflows and Codex-based planning.

## Pipeline

The current pipeline runs these stages:

1. `acestep_music`
2. `storyboard`
3. `keyframes`
4. `wan_interpolation`
5. `merge_mux`

In practice this means:

- load a profile from `profiles/`
- generate song text and audio inputs
- derive a storyboard from lyrics and profile context
- render anchor and reference frames
- interpolate clips and mux the final output

## Profile

The current example profile is `profiles/director_brief_example.yaml`.

Core fields:

- `prompt`
- `genre`
- `voice`
- `language`

Optional visual support:

- `visual_concept`
- `locations`
- `props`
- `anchor_*`

## Requirements

- Python `>=3.11`
- local ComfyUI at `http://127.0.0.1:8000`
- Codex CLI installed and logged in
- `ffmpeg` and `ffprobe` on `PATH`
- workflow JSON templates in `workflows/`

Default integration values live in [config_defaults.py](/D:/workspace/ai-music-video/src/ai_mv/core/orchestration/config_defaults.py).

## Install

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -e .[dev]
```

## Commands

```powershell
ai-mv doctor
ai-mv preflight --brief director_brief_example
ai-mv start --brief director_brief_example
ai-mv status --run-id 20260406-215500
```

## WSL Usage

If you run the repo from WSL while ComfyUI stays on Windows, prefer the WSL wrapper scripts instead of the default CLI commands. The default shared config still uses Windows-style ComfyUI directories, so the wrappers inject WSL-safe values without changing the Windows workflow.

```bash
./scripts/doctor-wsl.sh
./scripts/preflight-wsl.sh --concept-text 'Japanese 80s city pop night drive, neon coast, bittersweet summer romance'
./scripts/start-wsl.sh --concept-text 'Japanese 80s city pop night drive, neon coast, bittersweet summer romance'
```

Notes:
- the wrappers auto-detect the Windows WSL gateway for `comfyui_base_url`
- they expect ComfyUI input/output under `/mnt/c/Users/Desktop/Documents/ComfyUI/`
- `start-wsl.sh` runs the real generation pipeline and will create outputs / consume time

## Tests

```powershell
pytest
```
