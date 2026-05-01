# Manual quality findings

This document is the reviewer-facing companion to `ai-mv quality-findings-template`.
Use these codes in `.analysis/review-findings.json` under `review_inputs.quality_findings` so manual frame/MV review can flow back into `review_outputs`, `publishability_summary`, `rerender_plan`, and `rerender_execution_payloads`.

The scaffold source of truth is `src/ai_mv/core/review/quality_findings.py`. Keep this document aligned with `KNOWN_QUALITY_FINDING_CODES`.

## Current known quality finding codes

- `terminal_frame_corruption` — clip terminal frames contain corruption, ghosting, composite intrusion, or unrelated fragments.
- `continuity_break` — adjacent shots no longer read as the same subject/world/sequence.
- `duplicate_subject` — an unintended duplicate protagonist or duplicate body appears.
- `layered_overlay_intrusion` — abstract overlay, collage layer, or non-diegetic compositing intrudes into the shot.
- `identity_drift` — the protagonist identity/costume/face continuity drifts from the anchor or neighboring shot.
- `panel_layout` — the frame is panelized rather than a single motion-safe cinematic image.
- `collage_layout` — the frame reads as collage/poster art rather than a coherent video keyframe.
- `split_screen` — the frame contains split-screen layout that should not be used as a motion source.
- `weak_subject_match` — the rendered subject does not sufficiently match the intended/anchor subject.
- `weak_environment_match` — the rendered location/world does not sufficiently match the intended/anchor environment.
- `high_risk_interaction_without_backup` — a red-risk interaction/payoff shot is being used without a same-section symbolic insert, face reaction, world bridge, or other safer backup alternative.
- `red_risk_clip_held_too_long` — a red-risk IA2V interaction/payoff shot exceeds its production-policy duration cap and should be shortened or replaced with a safer backup insert.
- `motion_fragile_frame` — the still is too busy, symmetric, graphic, or fragile for clean IA2V motion.
- `unrelated_scene_intrusion` — an unrelated scene/object/world appears and breaks shot intent.
- `weak_character_payoff` — the final MV does not deliver enough protagonist/character payoff.
- `background_dominant_composition` — background or setting dominates when the shot needs subject payoff.
- `chorus_release_missing` — a chorus/release beat lacks a visible emotional lift or clear story-beat fulfillment.
- `final_payoff_missing` — the final/payoff beat does not visibly resolve the protagonist arc or required payoff.
- `repetitive_safe_editing` — final MV editing feels slideshow-like, over-safe, or repetitively cut and should route toward transition revision.

## Example

```json
{
  "review_inputs": {
    "quality_findings": {
      "S001": ["repetitive_safe_editing"],
      "S002": ["weak_subject_match", "identity_drift"]
    }
  }
}
```

## Review contract

- Prefer these structured codes over prose-only notes when a finding should affect rerender selection.
- Keep prose in `review-notes.md`, but duplicate actionable issues as codes in `review-findings.json`.
- `repetitive_safe_editing` is a final-MV/assembly review finding; it should not be used for isolated still attractiveness unless the repeated safe edit pattern is visible in the assembled sequence.
