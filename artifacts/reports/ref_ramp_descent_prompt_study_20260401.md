# REF Ramp / Underpass Descent Prompt Study (2026-04-01)

## Goal
- Find the strongest `Flux.2.dev REF` grammar for ramp / underpass descent shots.
- Separate this archetype from both stair descent and flat sidewalk continuation.

## Fixed Setup
- Anchor image:
  - [character_master_00044_.png](C:/Users/Desktop/Documents/ComfyUI/output/anchors/character_master_00044_.png)
- Probe command:
  - `python -m ai_mv.cli.app ref-v2-probe-batch`
- Shot family:
  - ramp / underpass descent

## Iteration 1
- Prompt:
  - `The same Korean female idol with a high ponytail walks down the wet ramp at night, one hand sliding along the side rail.`
- Output:
  - [ramp_descent_v01_end_00001_.png](C:/Users/Desktop/Documents/ComfyUI/output/keyframes/ramp_descent_v01_end_00001_.png)
- Result:
  - one heroine
  - ramp remains literal
  - side-rail contact survives
- Mismatch:
  - space reads a little more like an elevated walkway than an underpass
- Assessment:
  - strong baseline

## Iteration 2
- Prompt:
  - `The same Korean female idol with a high ponytail moves lower along the underpass ramp at night, one hand trailing the metal rail.`
- Output:
  - [ramp_descent_v02_end_00001_.png](C:/Users/Desktop/Documents/ComfyUI/output/keyframes/ramp_descent_v02_end_00001_.png)
- Result:
  - strongest descent logic
  - underpass space remains literal
  - rail stays secondary
  - one heroine continuity remains strong
- Mismatch:
  - none significant
- Assessment:
  - best overall

## Iteration 3
- Prompt:
  - `The same Korean female idol with a high ponytail follows the wet ramp downward at night, the rail staying close at her side.`
- Output:
  - [ramp_descent_v03_end_00001_.png](C:/Users/Desktop/Documents/ComfyUI/output/keyframes/ramp_descent_v03_end_00001_.png)
- Result:
  - clean single heroine
  - ramp remains literal
- Mismatch:
  - slightly too centered and clean
  - underpass identity weakens
- Assessment:
  - usable, weaker specificity

## Iteration 4
- Prompt:
  - `The same Korean female idol with a high ponytail descends the wet underpass ramp at night, one hand brushing the concrete wall rail.`
- Output:
  - [ramp_descent_v04_end_00001_.png](C:/Users/Desktop/Documents/ComfyUI/output/keyframes/ramp_descent_v04_end_00001_.png)
- Result:
  - strong underpass identity
  - ramp geometry remains clear
  - one heroine remains readable
- Mismatch:
  - slightly more posed than Iteration 2
- Assessment:
  - strongest alternate

## Iteration 5
- Prompt:
  - `The same Korean female idol with a high ponytail steps down the sloped passage at night, one hand leaving the metal rail behind her.`
- Output:
  - [ramp_descent_v05_end_00001_.png](C:/Users/Desktop/Documents/ComfyUI/output/keyframes/ramp_descent_v05_end_00001_.png)
- Result:
  - descent survives
- Mismatch:
  - scene drifts toward stair-like logic
  - ramp specificity weakens
- Assessment:
  - weaker than the underpass-ramp phrasing

## Best Prompt So Far
- Selected prompt:
  - `The same Korean female idol with a high ponytail moves lower along the underpass ramp at night, one hand trailing the metal rail.`
- Strong alternate:
  - `The same Korean female idol with a high ponytail descends the wet underpass ramp at night, one hand brushing the concrete wall rail.`
- Best output:
  - [ramp_descent_v02_end_00001_.png](C:/Users/Desktop/Documents/ComfyUI/output/keyframes/ramp_descent_v02_end_00001_.png)

## What This Taught Us

### 1. Ramp descent is its own family
- It should not be written like stairs.
- It should not be written like flat passage continuation.
- `underpass ramp` is a useful archetype noun.

### 2. `moves lower along` is strong
- It preserves slope/descent without over-forcing stair geometry.
- This works better than `steps down the sloped passage`.

### 3. Rail contact should trail, not release
- `one hand trailing the metal rail` works better than:
  - `leaving the rail behind her`
- release phrasing weakens the ramp identity.

## Best Current REF Prompt Pattern for Ramp / Underpass Descent
- Recommended pattern:
  - `The same Korean female idol [identity hook] moves lower along the underpass ramp at night, one hand trailing the metal rail.`
- Recommended alternate:
  - `The same Korean female idol [identity hook] descends the wet underpass ramp at night, one hand brushing the concrete wall rail.`

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
