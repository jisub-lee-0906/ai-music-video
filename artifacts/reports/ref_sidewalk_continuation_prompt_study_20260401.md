# REF Sidewalk Continuation Prompt Study (2026-04-01)

## Goal
- Find the strongest `Flux.2.dev REF` prompt grammar for open-sidewalk continuation shots.
- Prefer a grammar that remains useful outside the current station-centered profile.

## Fixed Setup
- Anchor image:
  - [character_master_00044_.png](C:/Users/Desktop/Documents/ComfyUI/output/anchors/character_master_00044_.png)
- Probe command:
  - `python -m ai_mv.cli.app ref-v2-probe-batch`
- Shot family:
  - open sidewalk continuation

## Iteration 1
- Prompt:
  - `The same Korean female idol with a high ponytail keeps walking along the wet sidewalk at night, the curb staying close at her side.`
- Output:
  - [sidewalk_v01_end_00001_.png](C:/Users/Desktop/Documents/ComfyUI/output/keyframes/sidewalk_v01_end_00001_.png)
- Result:
  - clean open-world continuation
  - curb and sidewalk remain literal
  - one heroine only
- Mismatch:
  - slightly posed
  - continuation is solid but not especially dynamic
- Assessment:
  - strong baseline

## Iteration 2
- Prompt:
  - `The same Korean female idol with a high ponytail moves forward along the wet sidewalk at night, one arm swinging free beside the curb.`
- Output:
  - [sidewalk_v02_end_00001_.png](C:/Users/Desktop/Documents/ComfyUI/output/keyframes/sidewalk_v02_end_00001_.png)
- Result:
  - best balance of locomotion and open-world realism
  - sidewalk stays literal
  - curb remains visible but secondary
  - chain-friendly forward movement is clear
- Mismatch:
  - none significant
- Assessment:
  - best overall

## Iteration 3
- Prompt:
  - `The same Korean female idol with a high ponytail walks past the curb line on the wet sidewalk at night, city lights stretching ahead.`
- Output:
  - [sidewalk_v03_end_00001_.png](C:/Users/Desktop/Documents/ComfyUI/output/keyframes/sidewalk_v03_end_00001_.png)
- Result:
  - broad city-night feeling is strong
- Mismatch:
  - too generic
  - sidewalk identity weakens
  - `city lights stretching ahead` broadens the space too much
- Assessment:
  - atmospheric, but weaker as a reusable keyframe grammar

## Iteration 4
- Prompt:
  - `The same Korean female idol with a high ponytail follows the wet sidewalk at night, her next step carrying her beyond the curb shadow.`
- Output:
  - [sidewalk_v04_end_00001_.png](C:/Users/Desktop/Documents/ComfyUI/output/keyframes/sidewalk_v04_end_00001_.png)
- Result:
  - simple locomotion remains
- Mismatch:
  - gaze drops
  - curb specificity weakens
  - `curb shadow` is too abstract
- Assessment:
  - usable, not ideal

## Iteration 5
- Prompt:
  - `The same Korean female idol with a high ponytail keeps to the outer sidewalk at night and moves forward, the wet curb close at her feet.`
- Output:
  - [sidewalk_v05_end_00001_.png](C:/Users/Desktop/Documents/ComfyUI/output/keyframes/sidewalk_v05_end_00001_.png)
- Result:
  - very strong sidewalk/city-edge identity
  - curb proximity survives clearly
  - one-heroine continuity remains strong
- Mismatch:
  - slightly less dynamic than Iteration 2
- Assessment:
  - strongest curb-specific alternate

## Best Prompt So Far
- Selected prompt:
  - `The same Korean female idol with a high ponytail moves forward along the wet sidewalk at night, one arm swinging free beside the curb.`
- Strong alternate:
  - `The same Korean female idol with a high ponytail keeps to the outer sidewalk at night and moves forward, the wet curb close at her feet.`
- Best output:
  - [sidewalk_v02_end_00001_.png](C:/Users/Desktop/Documents/ComfyUI/output/keyframes/sidewalk_v02_end_00001_.png)

## What This Taught Us

### 1. Open-sidewalk continuation likes plain locomotion
- This archetype does not need heavy contact detail.
- Simple forward motion works better than symbolic distance language.

### 2. `one arm swinging free` is useful in open-world shots
- It supports motion without forcing rail, wall, gate, or machine props into the frame.
- This makes it portable across genres.

### 3. `city lights stretching ahead` is too broad
- It weakens the sidewalk identity and turns the shot generic.

### 4. `curb close at her feet` is a strong alternate
- Similar to the platform-edge lesson, proximity near the feet helps preserve surface geometry.

## Best Current REF Prompt Pattern for Sidewalk Continuation
- Recommended movement pattern:
  - `The same Korean female idol [identity hook] moves forward along the wet sidewalk at night, one arm swinging free beside the curb.`
- Recommended curb-specific pattern:
  - `The same Korean female idol [identity hook] keeps to the outer sidewalk at night and moves forward, the wet curb close at her feet.`

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
