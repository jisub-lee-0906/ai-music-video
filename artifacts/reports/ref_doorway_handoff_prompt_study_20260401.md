# REF Doorway Handoff Prompt Study (2026-04-01)

## Goal
- Find the strongest `Flux.2.dev REF` prompt grammar for doorway handoff shots.
- Avoid doorway set-piece inflation, duplicate-body blur, and over-symbolic portal imagery.

## Fixed Setup
- Anchor image:
  - [character_master_00044_.png](C:/Users/Desktop/Documents/ComfyUI/output/anchors/character_master_00044_.png)
- Probe command:
  - `python -m ai_mv.cli.app ref-v2-probe-batch`
- Shot family:
  - doorway handoff / narrow opening transition

## Iteration 1
- Prompt:
  - `The same Korean female idol with a high ponytail steps through the narrow doorway at night, one hand leaving the metal frame.`
- Output:
  - [doorway_handoff_v01_end_00001_.png](C:/Users/Desktop/Documents/ComfyUI/output/keyframes/doorway_handoff_v01_end_00001_.png)
- Result:
  - doorway remains literal
  - one heroine only
- Mismatch:
  - doorway still dominates
  - motion is weaker than the wording
- Assessment:
  - usable, but too doorway-centered

## Iteration 2
- Prompt:
  - `The same Korean female idol with a high ponytail moves past the doorway at night, one hand trailing the frame edge as she goes forward.`
- Output:
  - [doorway_handoff_v02_end_00001_.png](C:/Users/Desktop/Documents/ComfyUI/output/keyframes/doorway_handoff_v02_end_00001_.png)
- Result:
  - one heroine
  - doorway remains readable
- Mismatch:
  - scene drifts away from the intended world
  - becomes a generic open doorway
- Assessment:
  - weak place fidelity

## Iteration 3
- Prompt:
  - `The same Korean female idol with a high ponytail clears the doorway at night and carries her next step into the wet passage beyond.`
- Output:
  - [doorway_handoff_v03_end_00001_.png](C:/Users/Desktop/Documents/ComfyUI/output/keyframes/doorway_handoff_v03_end_00001_.png)
- Result:
  - strongest continuity logic
  - wet passage beyond reads clearly
  - doorway stays secondary
- Mismatch:
  - heroine turns away from camera more than ideal
- Assessment:
  - best overall handoff structure

## Iteration 4
- Prompt:
  - `The same Korean female idol with a high ponytail crosses the doorway line at night, the wet pavement opening just beyond her feet.`
- Output:
  - [doorway_handoff_v04_end_00001_.png](C:/Users/Desktop/Documents/ComfyUI/output/keyframes/doorway_handoff_v04_end_00001_.png)
- Result:
  - clean one-heroine frame
  - wet pavement beyond survives
  - doorway does not overdominate
- Mismatch:
  - more posed and static than Iteration 3
- Assessment:
  - strongest alternate

## Iteration 5
- Prompt:
  - `The same Korean female idol with a high ponytail keeps moving beyond the doorway at night, one hand lifting from the metal edge.`
- Output:
  - [doorway_handoff_v05_end_00001_.png](C:/Users/Desktop/Documents/ComfyUI/output/keyframes/doorway_handoff_v05_end_00001_.png)
- Result:
  - motion blur is strong
- Mismatch:
  - duplicate-body / blur problem
  - doorway edge becomes unstable
- Assessment:
  - bad for this archetype

## Best Prompt So Far
- Selected prompt:
  - `The same Korean female idol with a high ponytail clears the doorway at night and carries her next step into the wet passage beyond.`
- Strong alternate:
  - `The same Korean female idol with a high ponytail crosses the doorway line at night, the wet pavement opening just beyond her feet.`
- Best output:
  - [doorway_handoff_v03_end_00001_.png](C:/Users/Desktop/Documents/ComfyUI/output/keyframes/doorway_handoff_v03_end_00001_.png)

## What This Taught Us

### 1. Doorway shots need destination space more than frame contact
- If the prompt focuses on the frame edge, the doorway itself dominates or destabilizes.
- The stronger pattern is:
  - doorway crossing
  - plus a literal space beyond it

### 2. `metal frame` is risky
- It tends to over-center the doorway or create blur artifacts.
- Doorway handoff works better without explicit frame-contact detail.

### 3. `wet passage beyond` is a strong stabilizer
- It gives the model somewhere to send the heroine.
- This reduces the “frozen in the doorway” failure.

## Best Current REF Prompt Pattern for Doorway Handoff
- Recommended pattern:
  - `The same Korean female idol [identity hook] clears the doorway at night and carries her next step into the wet passage beyond.`
- Recommended alternate:
  - `The same Korean female idol [identity hook] crosses the doorway line at night, the wet pavement opening just beyond her feet.`

## Avoid
- `metal frame`
- `hand lifting from the frame`
- doorway-edge-heavy contact language
- phrasing that makes the doorway itself the scene subject
