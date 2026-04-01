# REF Stair Prompt Study (2026-04-01)

## Goal
- Test whether the threshold-crossing prompt structure also works for stair-descent shots.
- Find the prompt shape that keeps stair geometry readable in `Flux.2.dev REF`.

## Fixed Setup
- Anchor image:
  - [character_master_00044_.png](C:/Users/Desktop/Documents/ComfyUI/output/anchors/character_master_00044_.png)
- Probe command:
  - `python -m ai_mv.cli.app ref-v2-probe`
- Shot family:
  - station stair descent

## Iteration 1
- Prompt:
  - `The same Korean female idol with a high ponytail steps down the wet station stairs at night, one hand sliding along the metal handrail.`
- Output:
  - [stair_v1_end_00001_.png](C:/Users/Desktop/Documents/ComfyUI/output/keyframes/stair_v1_end_00001_.png)
- Result:
  - strong identity continuity
  - stairs remain literal
  - handrail contact is clear
  - the frame feels cinematic without losing the stair geometry
- Mismatch:
  - the heroine is still slightly posed and centered
- Assessment:
  - best overall balance

## Iteration 2
- Prompt:
  - `The same Korean female idol with a high ponytail drops one step lower on the wet station stairs at night, one hand holding the cold handrail.`
- Output:
  - [stair_v2_end_00001_.png](C:/Users/Desktop/Documents/ComfyUI/output/keyframes/stair_v2_end_00001_.png)
- Result:
  - stair geometry remains readable
  - the descending posture is understandable
  - handrail stays literal
- Mismatch:
  - the pose becomes more static and fashion-photo-like
  - `holding the cold handrail` reads like a held pose more than movement
- Assessment:
  - usable, but less dynamic

## Iteration 3
- Prompt:
  - `The same Korean female idol with a high ponytail moves down from one stair tread to the next at night, one hand leaving the metal handrail.`
- Output:
  - [stair_v3_end_00001_.png](C:/Users/Desktop/Documents/ComfyUI/output/keyframes/stair_v3_end_00001_.png)
- Result:
  - descending motion reads
  - stairs remain clear
  - the frame is simpler and more action-led
- Mismatch:
  - the station feel weakens
  - the environment becomes generic outdoor steps
  - releasing the handrail reduces station specificity
- Assessment:
  - good motion, weaker place fidelity

## Best Prompt So Far
- Selected prompt:
  - `The same Korean female idol with a high ponytail steps down the wet station stairs at night, one hand sliding along the metal handrail.`
- Best output:
  - [stair_v1_end_00001_.png](C:/Users/Desktop/Documents/ComfyUI/output/keyframes/stair_v1_end_00001_.png)

## What This Taught Us

### 1. Stair shots need geometry more than threshold wording
- For stairs, the model responds best when the stairs themselves are the dominant surface.
- `wet station stairs` works better than abstract transition wording.

### 2. `Sliding along the handrail` works better than `holding` or `leaving`
- `holding` makes the frame feel posed.
- `leaving` weakens the location and turns the scene generic.
- `sliding along` preserves both motion and place.

### 3. Stair shots want `surface + contact`, not `surface A -> surface B`
- Threshold shots benefited from:
  - source surface -> destination surface
- Stair shots benefit more from:
  - one continuous stepped surface
  - one continuous contact line

## Best Current REF Prompt Pattern for Stair Shots
- Recommended pattern:
  - `The same Korean female idol [identity hook] steps down the wet station stairs at night, one hand sliding along the metal handrail.`

## Avoid
- `holding the rail`
- `leaving the rail`
- over-abstract step phrasing like `from one tread to the next` when station specificity matters

## Current Cross-Archetype Lesson
- Threshold shots prefer:
  - source surface -> destination surface + contact release
- Stair shots prefer:
  - continuous stepped surface + continuous contact detail
