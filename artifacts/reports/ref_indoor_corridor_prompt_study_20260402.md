# REF Indoor Corridor Prompt Study (2026-04-02)

## Goal
- Find the strongest `Flux.2.dev REF` grammar for a neutral indoor corridor shot.
- Prefer a structure that remains portable across profiles and genres.

## Fixed Setup
- Anchor image:
  - [character_master_00044_.png](C:/Users/Desktop/Documents/ComfyUI/output/anchors/character_master_00044_.png)
- Probe command:
  - `python -m ai_mv.cli.app ref-v2-probe-batch`
- Shot family:
  - neutral indoor corridor continuation

## Iteration 1
- Prompt:
  - `The same Korean female idol with a high ponytail walks down the quiet indoor corridor at night, one hand trailing the wall rail.`
- Output:
  - [indoor_corridor_v01_end_00001_.png](C:/Users/Desktop/Documents/ComfyUI/output/keyframes/indoor_corridor_v01_end_00001_.png)
- Result:
  - corridor remains literal
  - one heroine only
- Mismatch:
  - too dim and soft
  - readability weakens
- Assessment:
  - usable, but weak baseline

## Iteration 2
- Prompt:
  - `The same Korean female idol with a high ponytail moves forward through the narrow indoor corridor at night, the wall staying close at her side.`
- Output:
  - [indoor_corridor_v02_end_00001_.png](C:/Users/Desktop/Documents/ComfyUI/output/keyframes/indoor_corridor_v02_end_00001_.png)
- Result:
  - best overall balance
  - corridor remains literal
  - one heroine continuity is strong
  - movement survives without adding unnecessary props
- Mismatch:
  - none significant
- Assessment:
  - best overall

## Iteration 3
- Prompt:
  - `The same Korean female idol with a high ponytail keeps to the indoor corridor wall at night and moves forward, one hand brushing the rail.`
- Output:
  - [indoor_corridor_v03_end_00001_.png](C:/Users/Desktop/Documents/ComfyUI/output/keyframes/indoor_corridor_v03_end_00001_.png)
- Result:
  - wall proximity remains clear
  - one heroine only
- Mismatch:
  - scene opens back into a semi-outdoor walkway
  - indoor neutrality weakens
- Assessment:
  - weaker than Iteration 2

## Iteration 4
- Prompt:
  - `The same Korean female idol with a high ponytail walks past the indoor corridor lights at night, her next step carrying her down the hall.`
- Output:
  - [indoor_corridor_v04_end_00001_.png](C:/Users/Desktop/Documents/ComfyUI/output/keyframes/indoor_corridor_v04_end_00001_.png)
- Result:
  - corridor remains literal
- Mismatch:
  - too generic
  - `corridor lights` dominates more than needed
- Assessment:
  - safe but bland

## Iteration 5
- Prompt:
  - `The same Korean female idol with a high ponytail follows the narrow corridor at night, one arm swinging free while the wall stays close beside her.`
- Output:
  - [indoor_corridor_v05_end_00001_.png](C:/Users/Desktop/Documents/ComfyUI/output/keyframes/indoor_corridor_v05_end_00001_.png)
- Result:
  - narrowness remains
  - movement survives
- Mismatch:
  - image drifts toward a darker alley-like passage
- Assessment:
  - good movement, weaker indoor neutrality

## Best Prompt So Far
- Selected prompt:
  - `The same Korean female idol with a high ponytail moves forward through the narrow indoor corridor at night, the wall staying close at her side.`
- Best output:
  - [indoor_corridor_v02_end_00001_.png](C:/Users/Desktop/Documents/ComfyUI/output/keyframes/indoor_corridor_v02_end_00001_.png)

## What This Taught Us

### 1. Neutral indoor shots want wall proximity more than rail contact
- Rail contact pushes the image toward walkway/bridge variants.
- Wall proximity keeps the corridor archetype neutral and portable.

### 2. `corridor lights` is too generic
- It makes the shot readable, but bland.
- The stronger anchor is the corridor volume itself.

### 3. `narrow indoor corridor` is a useful portable noun
- It works beyond the current station profile.
- It is a good generic planner target for indoor transitional shots.

## Best Current REF Prompt Pattern for Indoor Corridor
- Recommended pattern:
  - `The same Korean female idol [identity hook] moves forward through the narrow indoor corridor at night, the wall staying close at her side.`

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
- Indoor corridor:
  - narrow corridor volume + wall proximity + forward continuation
