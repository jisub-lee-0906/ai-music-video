# REF Platform Edge Prompt Study (2026-04-01)

## Goal
- Find the strongest `Flux.2.dev REF` prompt grammar for platform-edge forward-walk shots.
- Test whether rail contact or edge-line proximity better preserves the platform-edge archetype.

## Fixed Setup
- Anchor image:
  - [character_master_00044_.png](C:/Users/Desktop/Documents/ComfyUI/output/anchors/character_master_00044_.png)
- Probe command:
  - `python -m ai_mv.cli.app ref-v2-probe-batch`
- Shot family:
  - platform-edge forward walk

## Iteration 1
- Prompt:
  - `The same Korean female idol with a high ponytail walks along the wet platform edge at night, one hand trailing the rail.`
- Output:
  - [platform_edge_v01_end_00001_.png](C:/Users/Desktop/Documents/ComfyUI/output/keyframes/platform_edge_v01_end_00001_.png)
- Result:
  - clear single heroine
  - platform edge reads
  - rail contact survives
- Mismatch:
  - frame is a little posed
  - locomotion is softer than the wording
- Assessment:
  - solid baseline

## Iteration 2
- Prompt:
  - `The same Korean female idol with a high ponytail keeps to the wet platform edge at night and moves forward, one hand brushing the yellow line rail.`
- Output:
  - [platform_edge_v02_end_00001_.png](C:/Users/Desktop/Documents/ComfyUI/output/keyframes/platform_edge_v02_end_00001_.png)
- Result:
  - strongest platform-edge specificity
  - yellow edge stays visually dominant
  - forward continuation survives
- Mismatch:
  - `yellow line rail` is slightly awkward as wording, but the image still benefits from it
- Assessment:
  - best archetype fidelity

## Iteration 3
- Prompt:
  - `The same Korean female idol with a high ponytail steps forward beside the wet platform edge at night, one hand sliding along the guard rail.`
- Output:
  - [platform_edge_v03_end_00001_.png](C:/Users/Desktop/Documents/ComfyUI/output/keyframes/platform_edge_v03_end_00001_.png)
- Result:
  - forward walk survives
  - one heroine remains strong
- Mismatch:
  - the space turns into a roadside barrier instead of a platform edge
- Assessment:
  - weak place fidelity

## Iteration 4
- Prompt:
  - `The same Korean female idol with a high ponytail moves past the wet platform edge at night, the yellow line staying close at her feet.`
- Output:
  - [platform_edge_v04_end_00001_.png](C:/Users/Desktop/Documents/ComfyUI/output/keyframes/platform_edge_v04_end_00001_.png)
- Result:
  - best locomotion read
  - yellow line underfoot stays literal
  - platform identity remains clear
- Mismatch:
  - no rail contact
  - slightly less cinematic than the best threshold and stair examples
- Assessment:
  - very strong platform-edge pattern

## Iteration 5
- Prompt:
  - `The same Korean female idol with a high ponytail clears the wet platform edge and keeps walking, one hand leaving the guard rail behind her.`
- Output:
  - [platform_edge_v05_end_00001_.png](C:/Users/Desktop/Documents/ComfyUI/output/keyframes/platform_edge_v05_end_00001_.png)
- Result:
  - identity remains clear
- Mismatch:
  - platform disappears
  - environment collapses into an empty studio-like space
- Assessment:
  - bad for this archetype

## Best Prompt So Far
- Selected prompt:
  - `The same Korean female idol with a high ponytail moves past the wet platform edge at night, the yellow line staying close at her feet.`
- Strong alternate:
  - `The same Korean female idol with a high ponytail keeps to the wet platform edge at night and moves forward, one hand brushing the yellow line rail.`
- Best output:
  - [platform_edge_v04_end_00001_.png](C:/Users/Desktop/Documents/ComfyUI/output/keyframes/platform_edge_v04_end_00001_.png)

## What This Taught Us

### 1. Platform-edge shots want edge proximity more than rail release
- The yellow edge line is a stronger archetype anchor than the rail.
- If the rail dominates, the model may turn the image into a roadside barrier scene.

### 2. `at her feet` is strong
- Surface proximity near the heroine's feet helps this model preserve the platform geometry.
- That works better than abstract `keep walking` continuation.

### 3. `clear/leaving behind` is dangerous here
- It makes the platform vanish.
- This archetype is not about exiting the space.
- It is about moving while staying near the edge.

## Best Current REF Prompt Pattern for Platform-Edge Shots
- Recommended pattern:
  - `The same Korean female idol [identity hook] moves past the wet platform edge at night, the yellow line staying close at her feet.`

## Avoid
- `clears the platform edge`
- `leaving the guard rail behind her`
- guard-rail-heavy language that turns the shot roadside

## Current Cross-Archetype Summary
- Threshold crossing:
  - source surface -> destination surface + contact release
- Stair descent:
  - continuous stepped surface + continuous handrail contact
- Passage compression:
  - wall proximity + forward movement + trailing rail
- Platform edge:
  - edge proximity near the feet + forward continuation
