# REF Curb Crossing Prompt Study (2026-04-01)

## Goal
- Find the strongest `Flux.2.dev REF` prompt grammar for curb / crosswalk crossing shots.
- Prefer a pattern that remains useful outside the current station-world profile.

## Fixed Setup
- Anchor image:
  - [character_master_00044_.png](C:/Users/Desktop/Documents/ComfyUI/output/anchors/character_master_00044_.png)
- Probe command:
  - `python -m ai_mv.cli.app ref-v2-probe-batch`
- Shot family:
  - curb / crosswalk crossing

## Iteration 1
- Prompt:
  - `The same Korean female idol with a high ponytail steps off the curb into the wet crosswalk at night, one hand leaving the street rail.`
- Output:
  - [curb_crossing_v01_end_00001_.png](C:/Users/Desktop/Documents/ComfyUI/output/keyframes/curb_crossing_v01_end_00001_.png)
- Result:
  - curb and crosswalk are both literal
  - one-heroine continuity is strong
  - step-off action survives
- Mismatch:
  - street rail is a little decorative
  - frame is slightly posed
- Assessment:
  - strong literal crossing

## Iteration 2
- Prompt:
  - `The same Korean female idol with a high ponytail crosses the wet crosswalk toward the far curb at night, one arm swinging free.`
- Output:
  - [curb_crossing_v02_end_00001_.png](C:/Users/Desktop/Documents/ComfyUI/output/keyframes/curb_crossing_v02_end_00001_.png)
- Result:
  - clean frontal locomotion
  - crosswalk remains literal
  - no extra objects dominate
- Mismatch:
  - far curb is not especially emphasized
- Assessment:
  - best clean generic crossing image

## Iteration 3
- Prompt:
  - `The same Korean female idol with a high ponytail moves across the wet street at night, the far curb drawing closer under the city lights.`
- Output:
  - [curb_crossing_v03_end_00001_.png](C:/Users/Desktop/Documents/ComfyUI/output/keyframes/curb_crossing_v03_end_00001_.png)
- Result:
  - strongest broad-city crossing feeling
  - locomotion is very clear
- Mismatch:
  - curb/crosswalk geometry weakens
  - image becomes a more generic wet-street walk
- Assessment:
  - strong atmosphere, weaker crossing precision

## Iteration 4
- Prompt:
  - `The same Korean female idol with a high ponytail reaches the far curb from the wet crosswalk at night, one foot finding the dry edge.`
- Output:
  - [curb_crossing_v04_end_00001_.png](C:/Users/Desktop/Documents/ComfyUI/output/keyframes/curb_crossing_v04_end_00001_.png)
- Result:
  - strongest curb arrival specificity
  - dry edge / far curb idea survives
- Mismatch:
  - less dynamic than Iteration 2
  - more side-profile than chain-forward
- Assessment:
  - best arrival-state image

## Iteration 5
- Prompt:
  - `The same Korean female idol with a high ponytail steps through the crosswalk at night and closes the distance to the far curb.`
- Output:
  - [curb_crossing_v05_end_00001_.png](C:/Users/Desktop/Documents/ComfyUI/output/keyframes/curb_crossing_v05_end_00001_.png)
- Result:
  - crosswalk remains literal
- Mismatch:
  - heroine turns away from camera
  - chain readability weakens
- Assessment:
  - weakest of the set

## Best Prompt So Far
- Selected prompt:
  - `The same Korean female idol with a high ponytail crosses the wet crosswalk toward the far curb at night, one arm swinging free.`
- Strong alternate:
  - `The same Korean female idol with a high ponytail reaches the far curb from the wet crosswalk at night, one foot finding the dry edge.`
- Best output:
  - [curb_crossing_v02_end_00001_.png](C:/Users/Desktop/Documents/ComfyUI/output/keyframes/curb_crossing_v02_end_00001_.png)

## What This Taught Us

### 1. Curb-crossing is more stable than gate-crossing
- This archetype does not need station hardware.
- Plain crosswalk language already anchors the scene well.

### 2. `toward the far curb` is strong
- It gives a destination without overcomplicating the frame.
- This works better than `closes the distance` or purely atmospheric distance phrasing.

### 3. Small free-arm motion works
- `one arm swinging free` supports locomotion without introducing machine or rail clutter.
- This is useful for open-world movement shots.

### 4. Arrival-state wording is also viable
- `one foot finding the dry edge` is a good end-frame grammar when the shot should resolve on arrival.

## Best Current REF Prompt Pattern for Curb Crossing
- Recommended movement pattern:
  - `The same Korean female idol [identity hook] crosses the wet crosswalk toward the far curb at night, one arm swinging free.`
- Recommended arrival pattern:
  - `The same Korean female idol [identity hook] reaches the far curb from the wet crosswalk at night, one foot finding the dry edge.`

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
