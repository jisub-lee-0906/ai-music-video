# Baseline

This document fixes the current runtime baseline before the next major planner pass.

## Active workflow set

- `audio_ace_step_1_5_checkpoint.json`
- `image_flux2_text_to_image.json`
- `flux1_dev_uso_reference_image_gen.json`
- `video_wan2_2_14B_flf2v.json`

Workflow names are centralized in [workflow_names.py](/D:/AI-MV/src/ai_mv/core/workflow_names.py) and are the source of truth for runners, bootstrap checks, and doctor checks.

## Planner contracts

- Audio planner outputs `genre_description`, `lyrics_blocks`, `lyrics`, `bpm`, `keyscale`, `seed`, `duration`.
- Repeated-return context must propagate through `section_label`.
- Shared profile steering fields are:
  - `profile_summary`
  - `audio_direction`
  - `hook_direction`
  - `visual_direction`
  - `negative_direction`

## Language rule

- `audio.language` controls lyrics generation and lyrics validation only.
- `audio.language` does not localize:
  - `genre_description`
  - profile steering fields
  - visual brief prompts
  - TTI prompts
  - USO prompts
  - WAN prompts
- Visual and diffusion prompts remain English-first because the current workflows and downstream text encoders are tuned for English prompt grammar.

## Intentional dynamic paths

- CLI command dispatch and stage registry are dynamic entrypoints and should not be treated as dead code.
- Mapper `required_inputs()` helpers are runtime contracts for workflow patching and should not be inlined away.
- Runner-level mutation helpers used only through retries or orchestration remain intentional even if they have narrow call sites.

## Known retained exceptions

- Private helpers that are only referenced by tests or dynamic orchestration are intentionally kept.
- Dead-code cleanup before the next major pass removes only symbols with clear zero references and no dynamic lookup role.
