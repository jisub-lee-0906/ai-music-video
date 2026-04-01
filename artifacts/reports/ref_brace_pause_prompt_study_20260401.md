# REF Brace / Pause Prompt Study (2026-04-01)

## Goal
- Find a usable `Flux.2.dev REF` grammar for low-motion keyframes.
- Avoid dead pose shots while keeping the frame readable and cinematic.

## Fixed Setup
- Anchor image:
  - [character_master_00044_.png](C:/Users/Desktop/Documents/ComfyUI/output/anchors/character_master_00044_.png)
- Probe command:
  - `python -m ai_mv.cli.app ref-v2-probe-batch`
- Shot family:
  - brace / pause / held step

## Iteration 1
- Prompt:
  - `The same Korean female idol with a high ponytail pauses at the wet rail at night, one hand braced on the metal bar.`
- Output:
  - [brace_pause_v01_end_00001_.png](C:/Users/Desktop/Documents/ComfyUI/output/keyframes/brace_pause_v01_end_00001_.png)
- Result:
  - clean single heroine
  - rail contact is literal
  - readable and usable
- Mismatch:
  - becomes a simple posed hold
  - little chain pressure
- Assessment:
  - safest baseline

## Iteration 2
- Prompt:
  - `The same Korean female idol with a high ponytail steadies herself beside the wet rail at night, one hand braced on the metal bar and her next step still held back.`
- Output:
  - [brace_pause_v02_end_00001_.png](C:/Users/Desktop/Documents/ComfyUI/output/keyframes/brace_pause_v02_end_00001_.png)
- Result:
  - one heroine
  - good body-line variation
- Mismatch:
  - too fashion-pose-like
  - held-back step does not read strongly
- Assessment:
  - weak as a continuity frame

## Iteration 3
- Prompt:
  - `The same Korean female idol with a high ponytail keeps close to the wet rail at night and holds for a beat, one hand braced on the metal bar.`
- Output:
  - [brace_pause_v03_end_00001_.png](C:/Users/Desktop/Documents/ComfyUI/output/keyframes/brace_pause_v03_end_00001_.png)
- Result:
  - profile is clear
  - rail remains literal
- Mismatch:
  - turns into a static contemplative pose
  - not useful enough as a dynamic keyframe
- Assessment:
  - too still

## Iteration 4
- Prompt:
  - `The same Korean female idol with a high ponytail leans into the wet rail at night, one hand braced on the metal bar as she holds her step.`
- Output:
  - [brace_pause_v04_end_00001_.png](C:/Users/Desktop/Documents/ComfyUI/output/keyframes/brace_pause_v04_end_00001_.png)
- Result:
  - stronger physical tension
  - rail contact remains literal
- Mismatch:
  - becomes almost investigative / peering
  - too specific and less reusable
- Assessment:
  - stronger tension, weaker generality

## Iteration 5
- Prompt:
  - `The same Korean female idol with a high ponytail braces at the wet rail at night, one hand fixed on the metal bar while the next step waits.`
- Output:
  - [brace_pause_v05_end_00001_.png](C:/Users/Desktop/Documents/ComfyUI/output/keyframes/brace_pause_v05_end_00001_.png)
- Result:
  - strongest emotional pressure
  - face remains readable
- Mismatch:
  - too front-facing and staged
  - not as natural as the best moving archetypes
- Assessment:
  - strongest tension shot, weaker naturalism

## Best Prompt So Far
- Selected prompt:
  - `The same Korean female idol with a high ponytail pauses at the wet rail at night, one hand braced on the metal bar.`
- Strong alternate:
  - `The same Korean female idol with a high ponytail braces at the wet rail at night, one hand fixed on the metal bar while the next step waits.`
- Best output:
  - [brace_pause_v01_end_00001_.png](C:/Users/Desktop/Documents/ComfyUI/output/keyframes/brace_pause_v01_end_00001_.png)

## What This Taught Us

### 1. Low-motion archetypes are harder
- They drift into fashion pose or contemplative hold faster than moving archetypes.
- This is currently the weakest REF family in the map.

### 2. Simpler is safer
- `pauses at the wet rail ... one hand braced`
- works better than more interpretive phrasing about held-back steps.

### 3. Tension language can over-stage the frame
- `next step waits`
- `holds for a beat`
- `steadies herself`
- often creates a more designed pose than a chain-ready keyframe.

## Best Current REF Prompt Pattern for Brace / Pause
- Recommended safe pattern:
  - `The same Korean female idol [identity hook] pauses at the wet rail at night, one hand braced on the metal bar.`
- Recommended tension alternate:
  - `The same Korean female idol [identity hook] braces at the wet rail at night, one hand fixed on the metal bar while the next step waits.`

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
