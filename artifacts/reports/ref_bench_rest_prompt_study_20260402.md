# REF Bench Rest Prompt Study (2026-04-02)

## Goal
- Find the strongest `Flux.2.dev REF` grammar for seated / bench-rest shots.
- Keep the seated image natural while preserving keyframe usefulness.

## Fixed Setup
- Anchor image:
  - [character_master_00044_.png](C:/Users/Desktop/Documents/ComfyUI/output/anchors/character_master_00044_.png)
- Probe command:
  - `python -m ai_mv.cli.app ref-v2-probe-batch`
- Shot family:
  - seated / bench rest

## Iteration 1
- Prompt:
  - `The same Korean female idol with a high ponytail sits on the wet bench at night, one hand resting on the seat beside her.`
- Output:
  - [bench_rest_v01_end_00001_.png](C:/Users/Desktop/Documents/ComfyUI/output/keyframes/bench_rest_v01_end_00001_.png)
- Result:
  - natural seated posture
  - one heroine only
  - bench remains literal
- Mismatch:
  - slightly too relaxed and complete
- Assessment:
  - strong baseline

## Iteration 2
- Prompt:
  - `The same Korean female idol with a high ponytail sits at the end of the wet bench at night, one foot still planted as if she could rise again.`
- Output:
  - [bench_rest_v02_end_00001_.png](C:/Users/Desktop/Documents/ComfyUI/output/keyframes/bench_rest_v02_end_00001_.png)
- Result:
  - strongest keyframe usefulness
  - seated state remains natural
  - subtle continuation survives
- Mismatch:
  - slightly more posed than Iteration 1
- Assessment:
  - best overall

## Iteration 3
- Prompt:
  - `The same Korean female idol with a high ponytail settles onto the wet bench at night, one hand braced lightly on the bench edge.`
- Output:
  - [bench_rest_v03_end_00001_.png](C:/Users/Desktop/Documents/ComfyUI/output/keyframes/bench_rest_v03_end_00001_.png)
- Result:
  - bench remains literal
- Mismatch:
  - too settled and still
  - weaker chain continuation
- Assessment:
  - too static

## Iteration 4
- Prompt:
  - `The same Korean female idol with a high ponytail rests on the narrow bench at night, her body still angled forward as if movement has not fully stopped.`
- Output:
  - [bench_rest_v04_end_00001_.png](C:/Users/Desktop/Documents/ComfyUI/output/keyframes/bench_rest_v04_end_00001_.png)
- Result:
  - strong continuation hint
  - dynamic body line
- Mismatch:
  - too stylized and reclined
  - drifts away from a simple seated rest
- Assessment:
  - useful alternate, less natural

## Iteration 5
- Prompt:
  - `The same Korean female idol with a high ponytail sits on the station-side bench at night, one hand holding the bench edge while her next step feels delayed.`
- Output:
  - [bench_rest_v05_end_00001_.png](C:/Users/Desktop/Documents/ComfyUI/output/keyframes/bench_rest_v05_end_00001_.png)
- Result:
  - one heroine only
  - seated state remains literal
- Mismatch:
  - over-designed and slightly heavy
  - station-specific again
- Assessment:
  - weaker than Iteration 2

## Best Prompt So Far
- Selected prompt:
  - `The same Korean female idol with a high ponytail sits at the end of the wet bench at night, one foot still planted as if she could rise again.`
- Strong alternate:
  - `The same Korean female idol with a high ponytail sits on the wet bench at night, one hand resting on the seat beside her.`
- Best output:
  - [bench_rest_v02_end_00001_.png](C:/Users/Desktop/Documents/ComfyUI/output/keyframes/bench_rest_v02_end_00001_.png)

## What This Taught Us

### 1. Seated shots need a small continuation hint
- Pure seated rest can work, but it risks feeling too finished.
- A small hint like:
  - `one foot still planted as if she could rise again`
- keeps the frame useful in a chain.

### 2. `settles onto` is too final
- It encourages a completed, static pose.

### 3. Strong forward-angle language can over-style the frame
- It increases drama, but risks losing naturalism.

## Best Current REF Prompt Pattern for Bench Rest
- Recommended pattern:
  - `The same Korean female idol [identity hook] sits at the end of the wet bench at night, one foot still planted as if she could rise again.`
- Recommended simple alternate:
  - `The same Korean female idol [identity hook] sits on the wet bench at night, one hand resting on the seat beside her.`

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
- Turn back once:
  - over-shoulder look-back + explicit forward continuation
- Indoor corridor:
  - narrow corridor volume + wall proximity + forward continuation
- Bench rest:
  - seated rest + small continuation hint
