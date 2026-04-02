# Seedance v2 Visual Success Criteria

This document fixes the first-pass success target for the current station-side profile.

Primary references:
- `docs/seedance_v2_prompting_reference.md`
- `artifacts/reports/ref_archetype_grammar_map_20260401.md`

## Phase 1 Goal

Close the current station-side profile before generic expansion.

The pipeline is considered green only when all of the following are true:

- `TTI`
  - the same heroine anchor is reusable across downstream REF shots
  - face, hair, outfit, silhouette, and footwear remain readable
  - the background does not compete with the anchor
- `REF`
  - single-heroine continuity remains stable
  - prompts stay subject-first and action-readable
  - primary surface stays grounded and visible
  - start and end read as adjacent states
  - pasted-on-background feeling is acceptably low in probe images
- `WAN`
  - prompts read as bridges between start and end frames, not new scenes
  - the bridge action stays in the same place and preserves subject continuity
  - clip output does not drift into new-scene invention
- `Full Run`
  - Intro, Bridge, and Final Chorus maintain chain continuity
  - final release does not collapse into a symbolic tableau
  - severe duplicate subject, identity drift, and pasted-on-background failures are absent

## Operating Rule

The current profile must pass this success bar before broader profile generalization begins.
