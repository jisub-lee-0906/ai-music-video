# Frame-Based Visual Validation

Use this document when validating ai-mv outputs visually without relying on music-quality judgment.

Purpose:
- inspect stills, clips, and assembled MV outputs through representative frames
- make continuity and corruption failures explicit
- create a repeatable visual-review method for humans and vision models

## Why this exists

At the current stage of ai-mv, music quality and section-role quality are not reliably judgeable by the coding agent alone.
The strongest available validation path is therefore:
- direct still-image inspection
- representative frame extraction from clips
- representative frame extraction from final assembled MV outputs

This does not solve all quality judgment, but it exposes the most actionable visual failure modes.

## Validation layers

### 1. Still validation
Inspect the generated still image directly.

Focus on:
- prompt adherence
- single-scene integrity
- subject clarity
- environment fidelity
- motion-safe source suitability
- absence of panel/collage/contact-sheet failures

### 2. Clip validation
For each clip, extract representative frames.

Current default strategy:
- first frame
- middle frame
- last frame

Focus on:
- identity continuity inside the shot
- pose / subject stability
- terminal-frame corruption
- duplicate-subject emergence
- layered overlay intrusion
- whether motion remains in the same scene/world

### 3. Final MV validation
For the assembled MV, extract evenly spaced sampled frames.

Current default strategy:
- N evenly spaced sampled frames from the full duration
- intended for sequence-level review, not per-shot animation debugging

Focus on:
- whether the sequence reads like one music video rather than disconnected images
- global continuity drift
- abrupt scene or identity collapse
- whether weak clips contaminate the final assembled output

## Artifact taxonomy

Recommended explicit failure tags:
- panel_layout
- collage_layout
- split_screen
- weak_subject_match
- weak_environment_match
- motion_fragile_frame
- duplicate_subject
- identity_drift
- continuity_break
- terminal_frame_corruption
- layered_overlay_intrusion
- unrelated_scene_intrusion

Use these tags in experiment logs, review notes, and future review payloads.

## Current extraction command

The repo now supports direct frame extraction through the CLI:

```bash
ai-mv extract-frames --video path/to/clip.mp4 --output-dir .analysis/clip-review --kind clip
ai-mv extract-frames --video path/to/final.mp4 --output-dir .analysis/final-review --kind final --sample-count 8
ai-mv quality-findings-template --shot-id S001 --shot-id S002 --output .analysis/review-findings.json
ai-mv review-packet --video path/to/final.mp4 --output-dir .analysis/final-review-packet --kind final --sample-count 8 --shot-id S001 --shot-id S002
```

Output behavior:
- `--kind clip`
  - writes `first.png`, `middle.png`, `last.png`
- `--kind final`
  - writes `final_01.png`, `final_02.png`, ... according to `--sample-count`
- `quality-findings-template`
  - writes a JSON scaffold shaped like `payload.review_inputs.quality_findings`
  - includes `known_quality_finding_codes` for the currently supported artifact taxonomy
- `review-packet`
  - writes `review-packet.json`, `review-findings.json`, and `review-notes.md`
  - precomputes expected frame paths under `frames/`
  - bundles frame-review bookkeeping into one folder

## Recommended workflow

1. Validate stills first.
2. For suspect clips, run `extract-frames --kind clip`.
3. For assembled outputs, run `extract-frames --kind final`.
4. Review the extracted images in order.
5. Record failure tags explicitly.
6. If you want one folder that already contains the manifest, findings scaffold, and notes file, generate a packet first:
   - `ai-mv review-packet --video path/to/final.mp4 --output-dir .analysis/final-review-packet --kind final --sample-count 8 --shot-id S001 --shot-id S002`
7. If you only need the JSON scaffold, generate it directly:
   - `ai-mv quality-findings-template --shot-id S001 --shot-id S002 --output .analysis/review-findings.json`
8. Fill `review_inputs.quality_findings[{shot_id}]` with the observed tags.
9. Only then decide whether the issue belongs to:
   - still prompt syntax
   - still prompt contract
   - clip prompt syntax
   - workflow routing
   - review/rerender policy

## Promotion rule into review automation

Do not automate a visual failure check until:
- the failure is repeatedly observable in extracted frames
- humans can label it consistently
- the failure has a stable local reason code

This keeps the deterministic review layer grounded in evidence instead of aesthetic guesswork.
