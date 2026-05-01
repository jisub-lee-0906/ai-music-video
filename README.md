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
# read final_video from artifacts/latest_success/manifest.json, then pass that path here
ai-mv extract-frames --video <final_video_path_from_manifest> --output-dir .analysis/final-review --kind final --sample-count 8
ai-mv quality-findings-template --shot-id S001 --shot-id S002 --output .analysis/review-findings.json
ai-mv review-packet --video <final_video_path_from_manifest> --output-dir .analysis/final-review-packet --kind final --sample-count 8 --shot-id S001 --shot-id S002
# packet now includes review-packet.json, review-findings.json, review-notes.md, and contact-sheet.json
ai-mv validate-latest --output-dir .analysis/latest-validation --sample-count 8
# validate-latest reads artifacts/latest_success/manifest.json, extracts final frames, builds a review packet, and writes validation-summary.json with run_summary review severity such as `review_severity_drift`, `review_severity_coverage`, `review_severity_visual_quality`, and `review_severity_assembly_quality`, plus `review_signal_buckets` and `review_signal_bucket_failed_checks` for compact failed-check triage
```

## Artifact contract

The pipeline writes two canonical JSON artifacts:
- `manifest.json`
- `run_summary.json`

For normal runs (`scope=run`) they are written to:
- `artifacts/runs/<run_id>/...`
- `artifacts/latest/...`
- `artifacts/latest_success/...` only when `status == done`

For preflight runs (`scope=preflight`) they are written to:
- `artifacts/preflight/<run_id>/...`
- `artifacts/preflight/latest/...`
- `artifacts/preflight/latest_success/...` only when `status == done`

Operational meaning:
- `latest` = most recent artifact for that scope, including failed runs
- `latest_success` = last known successful artifact for that scope
- a failed run updates `latest` but must not overwrite `latest_success`

Artifact schema notes:
- both `manifest.json` and `run_summary.json` carry `schema_version`
- the current canonical schema version is `ai_mv_schema_v2`
- `manifest.json` is the canonical source for structured pipeline outputs
- `run_summary.json` is the compact operational summary for quick inspection and downstream automation
- `run_summary.json` preserves review severity both as `review_severity` and as shallow fields for status dashboards: `review_severity_drift`, `review_severity_coverage`, `review_severity_visual_quality`, and `review_severity_assembly_quality`
- `run_summary.json` also preserves compact evidence-category triage via `review_signal_buckets` and `review_signal_bucket_failed_checks`
- use those severity and signal-bucket fields to distinguish visual artifact risk, assembly/editing risk, and failed-check evidence category without opening the full review report

Important:
- the final video file itself is not mirrored into `artifacts/latest/` or `artifacts/latest_success/`
- instead, read `final_video` from `artifacts/latest/manifest.json` or `artifacts/latest_success/manifest.json`
- `manifest.json` also records canonical sections such as `input`, `song`, `plan`, `stills`, `clips`, `assembly`, `review`, and `artifacts`

## WSL Usage

If you run the repo from WSL while ComfyUI stays on Windows, the core CLI now auto-detects the WSL gateway, default mounted ComfyUI input/output directories, and a local Codex binary when those integrations are still blank or Windows-oriented in config. The wrapper scripts remain the easiest smoke-run path because they also enable the short smoke envelope, but they are now convenience wrappers rather than the only safe way to launch the CLI.

### Recommended WSL entrypoints

For the shortest first-run path, keep using:
- concept-text driven run only
- target music duration: 15–20 seconds
- ia2v-centered canonical path enabled
- `planning.enable_flf2v=false` unless explicitly testing bridge transitions
- still generation + ia2v clip generation on the canonical four-workflow stack
- `./scripts/preflight-wsl.sh` and `./scripts/start-wsl.sh` should be treated as wrappers around the same canonical ia2v-centered runtime
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
- the default runtime is now shared-Comfy-safe: `ai-mv start` will not interrupt an in-flight Krita job or clear the shared ComfyUI queue unless you explicitly opt in
- if the ComfyUI queue is already busy (for example because Krita is rendering), `ai-mv start` fails fast instead of killing the other job; rerun after the queue is empty
- the WSL wrappers now guard against duplicate Windows ComfyUI backends on ports such as `8000` and `8001`; run `./scripts/check-shared-comfy-wsl.sh` if the frontend appears to show a different queue/history than ai-music-video
- for Krita + Blender + ai-music-video sharing, keep one canonical backend on `8000`; see `docs/shared-comfyui.md`
- if you intentionally want ai-music-video to take exclusive control of ComfyUI for a run, set `AI_MV_INTERRUPT_COMFY_BEFORE_START=1` and `AI_MV_CLEAR_COMFY_QUEUE_BEFORE_START=1`
- when Windows ComfyUI is bound to `0.0.0.0:8000` for WSL access and you still want ComfyUI-Manager installs for Krita, keep Manager `network_mode=personal_cloud` rather than `public`
- do not treat `ia2v`, `flf2v`, perfect identity consistency, or precise sync as first-run pass criteria

## Tests

```powershell
pytest
```
