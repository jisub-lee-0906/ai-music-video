# ai-mv

`ai-mv` is a Python 3.11 CLI for concept-text-first music-video generation using local ComfyUI workflows, ACE-Step music generation, Flux still generation, IA2V video generation, assembly, and review artifacts.

## Current product canon

The current product target is simple on the outside and strict inside:

1. User enters one `concept_text`.
2. The pipeline generates or maps music and timing sections.
3. Planning builds a story contract, shot plan, render plan, and production policy.
4. Flux TTI upper-body identity anchor is generated once on a clean white background.
5. Flux reference pose/action anchor bank is generated from that identity anchor.
6. Shot keyframes use the selected pose/action anchor as the primary reference.
7. IA2V-only video generation turns approved stills into clips.
8. Assembly publishes transition metadata, raw coverage status, and bridge-shot repair needs.
9. Review/rerender artifacts identify drift, coverage, visual-quality, and assembly-quality risks.

Important boundaries:
- Flux TTI is for the first upper-body identity anchor, not for every character pose.
- Flux reference is for full-body, pose/action anchors, and shot keyframes.
- IA2V is the only current video-generation path.
- World/environment anchors are continuity support only; they must not replace the identity anchor path.
- A generated final file is not treated as publish-ready unless review evidence supports it.

## Current pipeline

The runtime stage order is:

1. `audio`
2. `plan`
3. `stills`
4. `clips`
5. `assemble`
6. `review`
7. conditional `rerender` / `escalation`

In practice this means:
- derive music direction from `concept_text`
- generate music and timing structure
- build section, story, shot, material, and render plans
- render identity/pose anchors and shot stills through Flux workflows
- block risky stills before IA2V when still QA detects clone or second-person ambiguity
- render IA2V clips from stills and music timing
- assemble a final MV candidate
- publish review and repair evidence before claiming quality

## Implementation status

Implemented:
- concept-text CLI entrypoint
- ACE-Step audio stage
- story/section/shot planning
- Flux identity anchor and Flux reference pose/action anchor routing
- selected pose anchor reference routing for keyframes
- IA2V clip generation from stills
- still QA gate before IA2V
- assembly plan with `transition_pairs`
- assembly plan with `coverage_summary`
- artifact publication through `manifest.json` and `run_summary.json`
- validation/review packet utilities

Still in progress before a reliable one-prompt 3-minute MV product:
- bridge-shot planning from `transition_pairs.needs_bridge`
- automatic raw-coverage repair before sync padding
- IA2V handle generation and best trim-window selection
- frame-level transition scoring between adjacent clips
- stronger visual identity/clone detection on real artifacts
- full-run rerender budgeting and quality gates

## Requirements

- Python `>=3.11`
- local ComfyUI reachable from this environment
- `ffmpeg` and `ffprobe` on `PATH`
- workflow JSON templates in `workflows/`
- ACE-Step, Flux, and IA2V ComfyUI dependencies installed in the shared ComfyUI backend

Default integration values live in `src/ai_mv/core/orchestration/config_defaults.py`.

## Install

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e .[dev]
```

## Main commands

```bash
ai-mv doctor
ai-mv preflight --concept-text "dreamy synthwave night drive with lonely neon romance"
ai-mv start --concept-text "dreamy synthwave night drive with lonely neon romance"
ai-mv status --run-id 20260406-215500
ai-mv validate-latest --output-dir .analysis/latest-validation --sample-count 8
```

`validate-latest` reads `artifacts/latest_success/manifest.json`, extracts final frames, builds review artifacts, and writes `validation-summary.json` with review severity fields including `review_severity_drift`, `review_severity_coverage`, `review_severity_visual_quality`, and `review_severity_assembly_quality`, plus `review_signal_buckets` and `review_signal_bucket_failed_checks` for compact failed-check triage.

Additional review/audio commands may exist for internal debugging, but the user-facing path should stay centered on `start`, `status`, and `validate-latest`.

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

## WSL usage

When WSL drives a Windows-hosted ComfyUI backend, use the shared backend under:

```text
C:\Users\Desktop\Documents\ComfyUI\
C:\Users\Desktop\Documents\ComfyUI\
```

Recommended wrapper commands:

```bash
./scripts/doctor-wsl.sh
./scripts/preflight-wsl.sh --concept-text 'dreamy synthwave night drive with lonely neon romance'
./scripts/start-wsl.sh --concept-text 'dreamy synthwave night drive with lonely neon romance'
```

Notes:
- wrappers auto-detect the Windows WSL gateway for `comfyui_base_url`
- wrappers expect ComfyUI input/output under `C:\Users\Desktop\Documents\ComfyUI\`
- `start-wsl.sh` runs the real generation pipeline and will create outputs / consume time
- the default runtime is shared-Comfy-safe and should not interrupt Krita/Blender jobs unless explicit runtime flags opt in
- for Krita + Blender + ai-music-video sharing, keep one canonical backend on port `8000`; see `docs/shared-comfyui.md`

## Tests

```bash
source .venv/bin/activate
pytest -q
```
