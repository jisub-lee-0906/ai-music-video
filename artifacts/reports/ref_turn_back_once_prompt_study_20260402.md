# REF Turn Back Once Prompt Study (2026-04-02)

## Goal
- Find the strongest `Flux.2.dev REF` grammar for a moving `turn back once` keyframe.
- Keep the heroine in forward motion while preserving a readable look-back.

## Fixed Setup
- Anchor image:
  - [character_master_00044_.png](C:/Users/Desktop/Documents/ComfyUI/output/anchors/character_master_00044_.png)
- Probe command:
  - `python -m ai_mv.cli.app ref-v2-probe-batch`
- Shot family:
  - turn back once while continuing forward

## Iteration 1
- Prompt:
  - `The same Korean female idol with a high ponytail turns back once on the wet sidewalk at night, her body still moving forward.`
- Output:
  - [turn_back_v01_end_00001_.png](C:/Users/Desktop/Documents/ComfyUI/output/keyframes/turn_back_v01_end_00001_.png)
- Result:
  - single heroine
  - wet street remains clear
- Mismatch:
  - head turn is weak
  - image becomes mostly rear-view walking
- Assessment:
  - too weak for this archetype

## Iteration 2
- Prompt:
  - `The same Korean female idol with a high ponytail looks back over one shoulder on the wet street at night while her next step keeps going.`
- Output:
  - [turn_back_v02_end_00001_.png](C:/Users/Desktop/Documents/ComfyUI/output/keyframes/turn_back_v02_end_00001_.png)
- Result:
  - best balance of look-back and forward motion
  - one heroine only
  - face remains readable
  - wet street remains literal
- Mismatch:
  - slightly posed
- Assessment:
  - best overall

## Iteration 3
- Prompt:
  - `The same Korean female idol with a high ponytail glances back once at night as she moves along the wet curb.`
- Output:
  - [turn_back_v03_end_00001_.png](C:/Users/Desktop/Documents/ComfyUI/output/keyframes/turn_back_v03_end_00001_.png)
- Result:
  - readable look-back
  - curb remains visible
  - chain-friendly body direction survives
- Mismatch:
  - a little calmer than Iteration 2
- Assessment:
  - strong alternate

## Iteration 4
- Prompt:
  - `The same Korean female idol with a high ponytail turns her head back once at night while her body keeps moving along the wet pavement.`
- Output:
  - [turn_back_v04_end_00001_.png](C:/Users/Desktop/Documents/ComfyUI/output/keyframes/turn_back_v04_end_00001_.png)
- Result:
  - head turn is clear
  - body motion survives
- Mismatch:
  - slightly more stylized than Iteration 2
- Assessment:
  - usable, but less natural

## Iteration 5
- Prompt:
  - `The same Korean female idol with a high ponytail looks back once from the wet crosswalk at night, one foot still carrying her forward.`
- Output:
  - [turn_back_v05_end_00001_.png](C:/Users/Desktop/Documents/ComfyUI/output/keyframes/turn_back_v05_end_00001_.png)
- Result:
  - crosswalk remains literal
- Mismatch:
  - rear-view dominates
  - face readability weakens
- Assessment:
  - weaker than the street/curb versions

## Best Prompt So Far
- Selected prompt:
  - `The same Korean female idol with a high ponytail looks back over one shoulder on the wet street at night while her next step keeps going.`
- Strong alternate:
  - `The same Korean female idol with a high ponytail glances back once at night as she moves along the wet curb.`
- Best output:
  - [turn_back_v02_end_00001_.png](C:/Users/Desktop/Documents/ComfyUI/output/keyframes/turn_back_v02_end_00001_.png)

## What This Taught Us

### 1. `over one shoulder` is strong
- It preserves facial readability better than broader `turns back once`.
- This gives the model a clearer body/head split.

### 2. Forward motion must stay explicit
- `while her next step keeps going`
- is stronger than purely emotional or retrospective language.

### 3. Crosswalk versions tend to drift rear-view
- This family works better on open street/curb language than on strong crosswalk geometry.

## Best Current REF Prompt Pattern for Turn-Back Shots
- Recommended pattern:
  - `The same Korean female idol [identity hook] looks back over one shoulder on the wet street at night while her next step keeps going.`
- Recommended alternate:
  - `The same Korean female idol [identity hook] glances back once at night as she moves along the wet curb.`

## Current Cross-Archetype Summary
- Threshold crossing:
  - source surface -> destination surface + contact release
- Stair descent:
  - continuous stepped surface + continuous handrail contact
- Passage compression:
  - wall proximity + forward movement + trailing rail
- Platform edge:
  - edge proximity near the feet + forward continuation
- Gate pass:
  - beyond-the-gate continuation + destination space ahead
- Window contact:
  - present-tense surface contact + forward continuation
- Curb crossing:
  - plain crosswalk locomotion + destination curb
- Sidewalk continuation:
  - plain locomotion + optional free-arm motion or curb-at-feet proximity
- Doorway handoff:
  - doorway crossing + literal destination space beyond
- Brace / pause:
  - simple braced contact, but still the weakest family
- Ramp / underpass descent:
  - slope descent + trailing rail
- Turn back once:
  - over-shoulder look-back + explicit forward continuation
