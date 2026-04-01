# Seedance v2 Full Run REF Prompt/Image Review (2026-04-01)

Run:
- `seedance-v2-fullrun-20260401a`

Prompt source:
- [workflow_inputs_preview.json](D:/workspace/ai-music-video/artifacts/preflight/seedance-v2-ref-quality-pass-20260401ak/workflow_inputs_preview.json)

Scope:
- REF keyframes generated during the current full run while `wan_interpolation_v2` is pending.
- This review focuses on representative prompt/image pairs to identify the current model-response rules that should drive the next prompt-engineering pass.

## Overall Conclusion

The current prompts are not random. They do influence the image strongly, but `Flux.2.dev REF` is still over-interpreting certain prompt motifs into broader archetypal scenes.

What works:
- one heroine
- one clear forward action
- one concrete surface anchor
- direct crossing / stepping / passing actions

What breaks:
- `window + reflection + light` together
- `door seam / opening line / dark doorway` without a stronger physical surface
- `call light / blinking light / sign / glow` as secondary optical details
- compound transit imagery that gives the model permission to invent a different station or doorway set-piece

The best current prompts are the ones where the physical movement is stronger than the symbolic environment token.

## Representative 1:1 Review

### 1. `intro_b1`

Image:
- [intro_b1_end_00006_.png](C:/Users/Desktop/Documents/ComfyUI/output/keyframes/intro_b1_end_00006_.png)

Prompt:
- Location: `Rain-streaked station window beside a narrow strip of late-train light at the entrance wall`
- End prompt: `The same Korean female idol keeps pace along the rain-streaked glass beside the last train light, and the thin light slides across it behind her hand.`

Observed image:
- clean single heroine
- strong centered walk
- station platform rendered clearly
- purple neon trail dominates the floor
- no readable rain-streaked window contact

Assessment:
- Partial match.
- The forward movement and single-heroine read survived.
- The `window + thin light sliding across glass` structure did not survive.
- The model converted that optical wording into a generic neon transit-floor hero shot.

Prompt lesson:
- `window/light sliding across glass` is still too optical and indirect for REF.
- If the shot needs a window, the contact itself should be the action.

### 2. `verse1_b2`

Image:
- [verse1_b2_end_00007_.png](C:/Users/Desktop/Documents/ComfyUI/output/keyframes/verse1_b2_end_00007_.png)

Prompt:
- Location: `Cold handrail along a stairwell under a long shadow cast beneath the stairs`
- End prompt: `The same Korean female idol tightens her grip and steps one tread lower as her shadow stretches across the puddle below.`

Observed image:
- single heroine
- centered body
- full-body motion is readable
- scene changed into a broad street crosswalk in pale weather
- no rail, no stairwell, no one-tread descent

Assessment:
- Poor match.
- The action collapsed into a generic forward walk.
- `shadow / puddle below / one tread lower` was not strong enough to preserve stair geometry.

Prompt lesson:
- `stair descent` needs the stair or rail to be the dominant physical noun, not an atmospheric modifier.
- If the shot truly depends on stairs, the prompt needs less weather-like openness and more immediate contact.

### 3. `prechorus_b2`

Image:
- [prechorus_b2_end_00002_.png](C:/Users/Desktop/Documents/ComfyUI/output/keyframes/prechorus_b2_end_00002_.png)

Prompt:
- Location: `Door seam at the station gate where light gathers before the opening`
- End prompt: `The same Korean female idol closes the last gap and leans toward the opening line.`

Observed image:
- duplicated heroine-like presence through wet glass
- strong reflective door composition
- one hand on the handle reads clearly
- the model invented a two-body / mirror-body framing

Assessment:
- Poor match.
- The model over-committed to `door seam / opening / glass` and turned it into a reflection-duplication shot.
- The single-subject intent was weakened by the optical structure of the prompt itself.

Prompt lesson:
- `glass/door/opening/reflection` prompts still risk duplicate-body composition.
- If the goal is a threshold crossing, the prompt should emphasize hinge/edge/step-through, not reflective door imagery.

### 4. `chorus_b2`

Image:
- [chorus_b2_end_00004_.png](C:/Users/Desktop/Documents/ComfyUI/output/keyframes/chorus_b2_end_00004_.png)

Prompt:
- Location: `Doorway at the station frontage with a dark opening beyond the threshold`
- End prompt: `The same Korean female idol clears the door and lengthens her step into the open frontage.`

Observed image:
- single heroine
- crossing gesture is obvious
- doorway action is preserved
- station frontage became a theatrical open double-door set-piece
- body pose became slightly airborne / staged

Assessment:
- Medium match.
- The model understood `clear the door`.
- It did not preserve `station frontage`.
- It stylized the doorway into a broad symbolic opening.

Prompt lesson:
- `doorway + open frontage` is readable, but still too easy for the model to inflate into a stage-like reveal.
- Better than reflection prompts, but still vulnerable to set-piece inflation.

### 5. `verse2_b1`

Image:
- [verse2_b1_end_00001_.png](C:/Users/Desktop/Documents/ComfyUI/output/keyframes/verse2_b1_end_00001_.png)

Prompt:
- Location: `Glass door reflection beside a blinking call light in a station-side lane`
- End prompt: `The same Korean female idol moves beyond the door glass and leaves the blinking light behind her shoulder.`

Observed image:
- single heroine
- strong frontal presence
- ticket-like object appears in hand
- station hall invented
- reflection/call-light lane logic disappeared

Assessment:
- Poor match.
- `glass door reflection + blinking call light` did not create a lane-crossing image.
- Instead it triggered a generic transit-interior heroine shot.

Prompt lesson:
- `reflection + blinking light` is too weakly physical.
- The model replaces it with a broad “station interior” trope.

### 6. `bridge_b1`

Image:
- [bridge_b1_end_00003_.png](C:/Users/Desktop/Documents/ComfyUI/output/keyframes/bridge_b1_end_00003_.png)

Prompt:
- Location: `Night reflection in a window beside the gate in a narrow station-side passage`
- End prompt: `The same Korean female idol clears the gate line and leaves the dark window behind.`

Observed image:
- single heroine
- centered forward path
- bridge-like symmetry and compression read strongly
- actual gate/window/passage were lost
- the model turned the shot into an abstract illuminated catwalk

Assessment:
- Medium-poor match.
- The emotional compression survived.
- The literal geography did not.
- `window/reflection/gate` again became abstract architecture.

Prompt lesson:
- Even when the resulting image feels cinematic, `reflection` prompts still erase the intended place.
- This confirms that REF should prioritize crossing surfaces over optical motifs.

### 7. `finalchorus_b3`

Image:
- [finalchorus_b3_end_00008_.png](C:/Users/Desktop/Documents/ComfyUI/output/keyframes/finalchorus_b3_end_00008_.png)

Prompt:
- Location: `Wet crosswalk beside the station edge at the exit line`
- End prompt: `The same Korean female idol reaches the far side of the crosswalk and leaves the station edge behind her.`

Observed image:
- single heroine
- forward motion reads clearly
- “far side reached” reads
- transit exit feeling survives
- crosswalk turned into a gate/turnstile passage instead of a street crosswalk

Assessment:
- Good partial match.
- The important part is preserved: forward crossing and departure from the station edge.
- The exact surface changed, but the cinematic role survived.

Prompt lesson:
- `cross / far side / leave behind` is robust.
- Even when the surface mutates, the narrative function holds.

### 8. `finalchorus_b4`

Image:
- [finalchorus_b4_end_00004_.png](C:/Users/Desktop/Documents/ComfyUI/output/keyframes/finalchorus_b4_end_00004_.png)

Prompt:
- Location: `Gate lane opening onto a bright exit at the station-side edge`
- End prompt: `The same Korean female idol clears the gate line and keeps moving into the exit beyond it.`

Observed image:
- single heroine
- sustained forward walk
- exterior release feeling survives
- gate lane disappears
- image becomes a bright roadside / sidewalk continuation shot

Assessment:
- Good partial match.
- The key movement survived better than the specific gate geometry.
- This is still much healthier than earlier symbolic glow/reflection failures.

Prompt lesson:
- `clear / keep moving / exit beyond` works.
- The exact station object may drift, but the release motion holds.

## Current Model Response Rules

### What the model currently respects

- one heroine moving forward
- a single dominant locomotion verb
- crossing / clearing / passing as chain logic
- exterior release into a brighter, more open world

### What the model currently distorts

- `window + reflection`
  - often becomes mirrored bodies, abstract glass composition, or invented transit architecture
- `door seam / opening line / dark doorway`
  - often becomes theatrical portal imagery
- `call light / blinking light / sign / glow`
  - often becomes a generic station trope instead of a grounded local detail
- `stairwell / one tread lower / shadow below`
  - may still collapse into a generic forward walk unless the stair geometry is made more immediate

## Prompting Implications

### Keep

- one heroine
- one concrete movement verb
- one concrete surface or crossing anchor
- adjacent-state change that is easy to visualize

### Reduce

- reflection language
- abstract light movement around glass
- doorway symbolism
- secondary optical details like blinking call lights or moving window lines

### Prefer

- `hand on rail`
- `step through gate`
- `cross curb / crosswalk`
- `clear threshold`
- `move beyond edge`

### Avoid as REF defaults

- `reflection slips`
- `thin light slides across the glass`
- `leans toward the opening line`
- `checks the reflection`
- `blinking call light beside it`

## Practical Next Step

For the next prompt-engineering pass, treat `REF` as:
- body-led
- surface-led
- crossing-led

And treat these as high-risk motifs that should only appear when absolutely necessary:
- glass
- reflection
- doorway symbolism
- sliding light on surfaces
- blinking/sign/call-light details

This full-run sample confirms that prompt quality is still the main lever. The model is following the prompt's high-level action, but it is still over-stylizing optical and symbolic nouns into the wrong scene type.
