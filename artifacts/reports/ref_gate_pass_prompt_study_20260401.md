# REF Gate Pass Prompt Study (2026-04-01)

## Goal
- Find the strongest `Flux.2.dev REF` prompt grammar for gate / turnstile pass shots.
- Separate literal crossing from machine-dominant set-piece inflation.

## Fixed Setup
- Anchor image:
  - [character_master_00044_.png](C:/Users/Desktop/Documents/ComfyUI/output/anchors/character_master_00044_.png)
- Probe command:
  - `python -m ai_mv.cli.app ref-v2-probe-batch`
- Shot family:
  - gate / turnstile pass

## Iteration 1
- Prompt:
  - `The same Korean female idol with a high ponytail passes through the station gate at night, one hand leaving the turnstile rail.`
- Output:
  - [gate_pass_v01_end_00001_.png](C:/Users/Desktop/Documents/ComfyUI/output/keyframes/gate_pass_v01_end_00001_.png)
- Result:
  - single heroine
  - gate is literal
- Mismatch:
  - machine dominates the frame
  - the shot becomes a ticket-gate set-piece
- Assessment:
  - too gate-centric

## Iteration 2
- Prompt:
  - `The same Korean female idol with a high ponytail steps past the turnstile line at night, one hand trailing the gate rail.`
- Output:
  - [gate_pass_v02_end_00001_.png](C:/Users/Desktop/Documents/ComfyUI/output/keyframes/gate_pass_v02_end_00001_.png)
- Result:
  - strong identity continuity
  - the heroine remains large and readable
- Mismatch:
  - still too symmetrical
  - turnstile hardware remains very dominant
- Assessment:
  - better than Iteration 1, still inflated

## Iteration 3
- Prompt:
  - `The same Korean female idol with a high ponytail clears the ticket gate onto the wet pavement at night, one hand sliding off the rail.`
- Output:
  - [gate_pass_v03_end_00001_.png](C:/Users/Desktop/Documents/ComfyUI/output/keyframes/gate_pass_v03_end_00001_.png)
- Result:
  - wet pavement reads clearly
  - crossing out of the gate survives
- Mismatch:
  - still leans a little posed
  - gate hardware remains important
- Assessment:
  - strong partial match

## Iteration 4
- Prompt:
  - `The same Korean female idol with a high ponytail crosses the gate line at night and moves onto the wet pavement, one hand leaving the metal rail.`
- Output:
  - [gate_pass_v04_end_00001_.png](C:/Users/Desktop/Documents/ComfyUI/output/keyframes/gate_pass_v04_end_00001_.png)
- Result:
  - locomotion survives
  - wet pavement survives
- Mismatch:
  - space simplifies too much
  - gate identity weakens into a generic barrier
- Assessment:
  - healthy movement, weaker gate archetype

## Iteration 5
- Prompt:
  - `The same Korean female idol with a high ponytail moves beyond the turnstile at night, the wet pavement opening ahead of her.`
- Output:
  - [gate_pass_v05_end_00001_.png](C:/Users/Desktop/Documents/ComfyUI/output/keyframes/gate_pass_v05_end_00001_.png)
- Result:
  - best overall balance
  - heroine is the subject
  - turnstile stays literal but secondary
  - forward continuation survives
  - wet pavement beyond the gate reads clearly
- Mismatch:
  - slightly cleaner and broader than a raw MV frame
- Assessment:
  - best gate-pass pattern so far

## Best Prompt So Far
- Selected prompt:
  - `The same Korean female idol with a high ponytail moves beyond the turnstile at night, the wet pavement opening ahead of her.`
- Best output:
  - [gate_pass_v05_end_00001_.png](C:/Users/Desktop/Documents/ComfyUI/output/keyframes/gate_pass_v05_end_00001_.png)

## What This Taught Us

### 1. `moves beyond` works better than `passes through`
- `passes through` makes the turnstile itself too important.
- `moves beyond the turnstile` keeps the gate visible while preserving continuation.

### 2. Gate shots want destination space
- Adding:
  - `the wet pavement opening ahead of her`
- helps the model keep the gate as a crossing point instead of a closed object.

### 3. Rail contact is not necessary here
- Unlike threshold and stairs, gate-pass shots do not need contact detail to succeed.
- Overusing rail contact makes the machine too central.

## Best Current REF Prompt Pattern for Gate Pass Shots
- Recommended pattern:
  - `The same Korean female idol [identity hook] moves beyond the turnstile at night, the wet pavement opening ahead of her.`

## Avoid
- `passes through the station gate`
- `steps past the turnstile line`
- heavy rail-contact language
- highly symmetrical gate-center staging

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
