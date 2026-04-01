# REF Threshold Prompt Study (2026-04-01)

## Goal
- Find the most reliable prompt shape for `Flux.2.dev REF` on threshold-crossing shots.
- Keep the TTI anchor fixed.
- Change only the REF prompt and compare the resulting image 1:1.

## Fixed Setup
- Anchor image:
  - [character_master_00044_.png](C:/Users/Desktop/Documents/ComfyUI/output/anchors/character_master_00044_.png)
- Probe command:
  - `python -m ai_mv.cli.app ref-v2-probe`
- Shot family:
  - station threshold / exit / street crossing

## Iteration 1
- Prompt:
  - `The same Korean female idol with a high ponytail steps through the station gate opening at night, one hand brushing the metal edge.`
- Output:
  - [threshold_v1_end_00001_.png](C:/Users/Desktop/Documents/ComfyUI/output/keyframes/threshold_v1_end_00001_.png)
- Result:
  - identity continuity is strong
  - one heroine only
  - hand-to-edge contact is clear
  - gate structure is literal
- Mismatch:
  - the image becomes a door/gate set-piece
  - the motion reads more posed than crossing-led
- Assessment:
  - good fidelity, but too doorway-dominant

## Iteration 2
- Prompt:
  - `The same Korean female idol with a high ponytail crosses the wet curb beyond the station exit line at night, one hand trailing the rail.`
- Output:
  - [threshold_v2_end_00001_.png](C:/Users/Desktop/Documents/ComfyUI/output/keyframes/threshold_v2_end_00001_.png)
- Result:
  - strong sideward locomotion
  - wet road surface reads clearly
  - rail contact survives
  - environment stays secondary
- Mismatch:
  - `station exit line` does not stay literal
  - the shot becomes more roadside than threshold-specific
- Assessment:
  - very healthy crossing image, weaker threshold specificity

## Iteration 3
- Prompt:
  - `The same Korean female idol with a high ponytail passes the station threshold into the wet street at night, one hand sliding off the gate rail.`
- Output:
  - [threshold_v3_end_00001_.png](C:/Users/Desktop/Documents/ComfyUI/output/keyframes/threshold_v3_end_00001_.png)
- Result:
  - strong single heroine
  - threshold-to-street movement reads
  - rail contact survives
  - release into the street reads more clearly than Iteration 1
- Mismatch:
  - composition is still a little front-facing and staged
  - the gate geometry is stronger than the crossing motion
- Assessment:
  - strong overall, but still slightly set-piece-like

## Iteration 4
- Prompt:
  - `The same Korean female idol with a high ponytail steps off the station threshold onto the wet street at night, one hand leaving the gate rail.`
- Output:
  - [threshold_v4_end_00001_.png](C:/Users/Desktop/Documents/ComfyUI/output/keyframes/threshold_v4_end_00001_.png)
- Result:
  - best locomotion read
  - threshold release is literal
  - wet street surface reads clearly
  - gate rail stays secondary
  - anchor identity continuity remains strong
- Mismatch:
  - still slightly cleaner and more centered than a raw MV frame
  - acceptable
- Assessment:
  - best overall balance of movement, place, and identity

## Iteration 5
- Prompt:
  - `The same Korean female idol with a high ponytail crosses out from the station exit onto the wet sidewalk at night, one hand trailing the metal rail.`
- Output:
  - [threshold_v5_end_00001_.png](C:/Users/Desktop/Documents/ComfyUI/output/keyframes/threshold_v5_end_00001_.png)
- Result:
  - single heroine remains strong
  - wet sidewalk reads literally
  - rail contact survives
- Mismatch:
  - `station exit` becomes frontage more than threshold
  - the shot is calmer and more generic than Iteration 4
- Assessment:
  - usable, but less cinematic and less specific

## Best Prompt So Far
- Selected prompt:
  - `The same Korean female idol with a high ponytail steps off the station threshold onto the wet street at night, one hand leaving the gate rail.`
- Best output:
  - [threshold_v4_end_00001_.png](C:/Users/Desktop/Documents/ComfyUI/output/keyframes/threshold_v4_end_00001_.png)

## What This Taught Us

### 1. `steps off ... onto ...` is stronger than `steps through ...`
- `steps through the station gate opening` over-emphasized the doorway itself.
- `steps off the station threshold onto the wet street` preserves the motion path better.

### 2. Contact release works better than contact hold
- `one hand leaving the gate rail` worked better than:
  - `one hand brushing the metal edge`
  - `one hand sliding off the gate rail`
- release language supports forward continuation.

### 3. `threshold -> street` is a strong REF pattern
- This model responds well when the prompt explicitly moves from one concrete surface to another.
- The best pattern here is:
  - source surface
  - destination surface
  - one contact release detail

### 4. Small identity hooks still help
- `with a high ponytail` remains useful even in REF.
- It improves continuity without turning the prompt into a checklist.

## Best Current REF Prompt Pattern for Crossing Shots
- Recommended pattern:
  - `The same Korean female idol [small identity hook] [steps/crosses/passes] [off/from source surface] [onto/into destination surface] at night, one hand [leaving/trailing] [rail/edge].`

## Avoid
- `gate opening`
- `door seam`
- `opening line`
- `reflection`
- `glass`
- `brushing the edge` when the shot should feel like continuation

## Next Archetypes
- stair descent
- side passage compression
- pre-chorus threshold handoff
