# REF Passage Prompt Study (2026-04-01)

## Goal
- Find the strongest `Flux.2.dev REF` prompt grammar for narrow side-passage compression shots.
- Keep the TTI anchor fixed.
- Compare prompt structure against actual image response.

## Fixed Setup
- Anchor image:
  - [character_master_00044_.png](C:/Users/Desktop/Documents/ComfyUI/output/anchors/character_master_00044_.png)
- Probe command:
  - `python -m ai_mv.cli.app ref-v2-probe`
- Shot family:
  - narrow station-side passage / compression movement

## Batch Round

### Iteration 1
- Prompt:
  - `The same Korean female idol with a high ponytail moves through the narrow station-side passage at night, one hand sliding along the metal edge.`
- Output:
  - [passage_v01_end_00001_.png](C:/Users/Desktop/Documents/ComfyUI/output/keyframes/passage_v01_end_00001_.png)
- Result:
  - single heroine
  - strong identity continuity
  - passage remains literal
- Mismatch:
  - too calm and posed
  - not enough compression pressure
- Assessment:
  - readable, but not tight enough

### Iteration 2
- Prompt:
  - `The same Korean female idol with a high ponytail leans into the narrow station-side passage at night, one hand sliding along the wall rail.`
- Output:
  - [passage_v02_end_00001_.png](C:/Users/Desktop/Documents/ComfyUI/output/keyframes/passage_v02_end_00001_.png)
- Result:
  - strong wall proximity
  - contact is literal
  - narrowness reads clearly
- Mismatch:
  - too static
  - becomes a held lean instead of forward continuation
- Assessment:
  - good compression, weak movement

### Iteration 3
- Prompt:
  - `The same Korean female idol with a high ponytail threads through the tight station passage at night, one hand brushing the metal rail.`
- Output:
  - [passage_v03_end_00001_.png](C:/Users/Desktop/Documents/ComfyUI/output/keyframes/passage_v03_end_00001_.png)
- Result:
  - identity stays clean
- Mismatch:
  - the model inflates the space into a broad platform walkway
  - `threads through` does not preserve narrowness
- Assessment:
  - poor archetype fidelity

### Iteration 4
- Prompt:
  - `The same Korean female idol with a high ponytail keeps close to the passage wall at night, one hand trailing the rail as she moves forward.`
- Output:
  - [passage_v04_end_00001_.png](C:/Users/Desktop/Documents/ComfyUI/output/keyframes/passage_v04_end_00001_.png)
- Result:
  - strong compression
  - narrowness survives
  - forward intent survives
- Mismatch:
  - darker, slightly muddy frame
  - less facial readability
- Assessment:
  - strong compression signal, moderate readability

### Iteration 5
- Prompt:
  - `The same Korean female idol with a high ponytail clears the narrow passage at night, one hand leaving the metal edge behind her.`
- Output:
  - [passage_v05_end_00001_.png](C:/Users/Desktop/Documents/ComfyUI/output/keyframes/passage_v05_end_00001_.png)
- Result:
  - narrowness remains
- Mismatch:
  - turns into a two-wall pose
  - almost no forward movement
- Assessment:
  - weak for REF continuity

## Refinement Round

### Iteration 6
- Prompt:
  - `The same Korean female idol with a high ponytail moves forward through the narrow station-side passage at night, one hand trailing the wall rail.`
- Output:
  - [passage_v06_end_00001_.png](C:/Users/Desktop/Documents/ComfyUI/output/keyframes/passage_v06_end_00001_.png)
- Result:
  - best readability
  - single heroine
  - strong forward walk
  - rail contact survives
- Mismatch:
  - composition becomes symmetrical and cleaner
  - compression pressure weakens
- Assessment:
  - best readable movement, weaker compression mood

### Iteration 7
- Prompt:
  - `The same Korean female idol with a high ponytail keeps close to the narrow passage wall at night and moves forward, one hand trailing the metal rail.`
- Output:
  - [passage_v07_end_00001_.png](C:/Users/Desktop/Documents/ComfyUI/output/keyframes/passage_v07_end_00001_.png)
- Result:
  - narrowness is strong
  - wall proximity is strong
  - forward continuation survives
  - one-heroine continuity remains solid
- Mismatch:
  - face is slightly less readable than the threshold/stair best cases
  - acceptable
- Assessment:
  - best overall compression archetype match

## Best Prompt So Far
- Selected prompt:
  - `The same Korean female idol with a high ponytail keeps close to the narrow passage wall at night and moves forward, one hand trailing the metal rail.`
- Best output:
  - [passage_v07_end_00001_.png](C:/Users/Desktop/Documents/ComfyUI/output/keyframes/passage_v07_end_00001_.png)

## What This Taught Us

### 1. Passage compression needs wall proximity in the sentence
- `moves through the passage` alone is too weak.
- The model opens the space unless the prompt explicitly says she stays close to the wall.

### 2. Compression needs motion plus proximity
- `leans into` gives proximity but kills continuation.
- `moves forward` gives continuation but can flatten the shot.
- The best result combines both:
  - `keeps close ... and moves forward`

### 3. `Threads through` is bad for this archetype
- It sounds dynamic in text, but the model turns it into a broad walkway shot.

### 4. Contact should trail, not dominate
- `one hand trailing the rail` keeps the rail secondary.
- Stronger contact language tends to turn into pose.

## Best Current REF Prompt Pattern for Compression Shots
- Recommended pattern:
  - `The same Korean female idol [identity hook] keeps close to the narrow passage wall at night and moves forward, one hand trailing the metal rail.`

## Avoid
- `threads through`
- `leans into` as the main action
- `clears the passage`
- overly symmetrical walkway language

## Current Cross-Archetype Summary
- Threshold crossing:
  - source surface -> destination surface + contact release
- Stair descent:
  - continuous stepped surface + continuous handrail contact
- Passage compression:
  - wall proximity + forward movement + trailing rail
