# REF Window Contact Prompt Study (2026-04-01)

## Goal
- Find the strongest `Flux.2.dev REF` prompt grammar for window-contact shots.
- Measure whether this archetype can be stabilized without duplicate-body drift.

## Fixed Setup
- Anchor image:
  - [character_master_00044_.png](C:/Users/Desktop/Documents/ComfyUI/output/anchors/character_master_00044_.png)
- Probe command:
  - `python -m ai_mv.cli.app ref-v2-probe-batch`
- Shot family:
  - station window / glass contact

## Iteration 1
- Prompt:
  - `The same Korean female idol with a high ponytail leans toward the station window at night, one hand sliding along the metal edge.`
- Output:
  - [window_contact_v01_end_00001_.png](C:/Users/Desktop/Documents/ComfyUI/output/keyframes/window_contact_v01_end_00001_.png)
- Result:
  - strong identity continuity
  - window is literal
  - contact is strong
  - reflection remains secondary
- Mismatch:
  - the shot becomes very leaned-in and intimate
  - weak forward continuation
- Assessment:
  - best pure contact image

## Iteration 2
- Prompt:
  - `The same Korean female idol with a high ponytail keeps close to the station window at night and moves forward, one hand trailing the metal edge.`
- Output:
  - [window_contact_v02_end_00001_.png](C:/Users/Desktop/Documents/ComfyUI/output/keyframes/window_contact_v02_end_00001_.png)
- Result:
  - one heroine
  - movement survives
  - reflection does not duplicate the body
  - platform context stays readable
- Mismatch:
  - still slightly posed
  - the window interaction is softer than in Iteration 1
- Assessment:
  - best balance of contact and continuation

## Iteration 3
- Prompt:
  - `The same Korean female idol with a high ponytail moves past the station window at night, one hand sliding along the lower metal rail.`
- Output:
  - [window_contact_v03_end_00001_.png](C:/Users/Desktop/Documents/ComfyUI/output/keyframes/window_contact_v03_end_00001_.png)
- Result:
  - identity remains strong
  - forward side motion reads
- Mismatch:
  - window becomes more backdrop than interaction
  - contact weakens
- Assessment:
  - usable, but weaker archetype signal

## Iteration 4
- Prompt:
  - `The same Korean female idol with a high ponytail draws closer to the rain-streaked station window at night, one hand resting on the metal edge.`
- Output:
  - [window_contact_v04_end_00001_.png](C:/Users/Desktop/Documents/ComfyUI/output/keyframes/window_contact_v04_end_00001_.png)
- Result:
  - rain-streaked glass is very literal
  - station context survives
  - heroine remains clean
- Mismatch:
  - contact becomes static
  - the frame reads observational rather than progressive
- Assessment:
  - strong mood, weaker continuation

## Iteration 5
- Prompt:
  - `The same Korean female idol with a high ponytail leaves the station window behind her at night, one hand lifting from the metal edge.`
- Output:
  - [window_contact_v05_end_00001_.png](C:/Users/Desktop/Documents/ComfyUI/output/keyframes/window_contact_v05_end_00001_.png)
- Result:
  - single heroine
  - station remains readable
- Mismatch:
  - window contact mostly disappears
  - image becomes a generic station-side pose
- Assessment:
  - weak for this archetype

## Best Prompt So Far
- Selected prompt:
  - `The same Korean female idol with a high ponytail keeps close to the station window at night and moves forward, one hand trailing the metal edge.`
- Strong alternate:
  - `The same Korean female idol with a high ponytail leans toward the station window at night, one hand sliding along the metal edge.`
- Best output:
  - [window_contact_v02_end_00001_.png](C:/Users/Desktop/Documents/ComfyUI/output/keyframes/window_contact_v02_end_00001_.png)

## What This Taught Us

### 1. Window contact can work if contact stays literal and reflection stays secondary
- This archetype is not automatically broken.
- The model can keep one heroine and a readable reflection if the prompt is surface/contact-led.

### 2. `keeps close ... and moves forward` is safer than pure leaning
- Pure leaning gives better contact but weaker continuity.
- Adding forward movement makes the shot more useful in a keyframe chain.

### 3. `leaves the window behind` is too weak
- It dissolves the archetype.
- Window shots need present-tense contact, not exit phrasing.

## Best Current REF Prompt Pattern for Window Contact Shots
- Recommended pattern:
  - `The same Korean female idol [identity hook] keeps close to the station window at night and moves forward, one hand trailing the metal edge.`

## Avoid
- `leaves the window behind`
- overly abstract reflection phrasing
- contact-rest phrasing when chain continuity matters

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
