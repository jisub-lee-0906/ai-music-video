# Full Run REF Prompt/Image Review 2026-04-03

Run:
- `visual-fullrun-20260403a`

Reference prompt source:
- `D:\workspace\ai-music-video\artifacts\preflight\visual-grammar-gate-20260403d\workflow_inputs_preview.json`

Anchor:
- `C:\Users\Desktop\Documents\ComfyUI\output\anchors\character_master_00002_.png`

## Executive Summary

The current full-run REF outputs do not consistently match the intended prompt structure.

The main problem is not random scene failure. The stronger failure is:
- anchor identity and wardrobe drift
- archetype collapse into generic doorway/corridor/street imagery
- loss of the intended playable surface

Some shots still align well enough to the prompt structure, but many shots drift so far from the anchor that the prompt-to-image mapping becomes unusable for reliable production.

## 1:1 Review

### intro_b1
Prompt:
- Start: `The same Korean female idol steps along the wet platform edge into the turnstile lane.`
- End: `The same Korean female idol passes through the turnstile and lands just inside the station.`

Image:
- `C:\Users\Desktop\Documents\ComfyUI\output\keyframes\intro_b1_start_00001_.png`
- `C:\Users\Desktop\Documents\ComfyUI\output\keyframes\intro_b1_end_00001_.png`

Assessment:
- Strong match.
- Anchor identity is preserved.
- Turnstile/gate crossing reads correctly.
- This is a usable success case.

### intro_b2
Prompt:
- End: `The same Korean female idol leans toward the opening and readies to pass through.`

Image:
- `C:\Users\Desktop\Documents\ComfyUI\output\keyframes\intro_b2_end_00001_.png`

Assessment:
- Mismatch.
- The image collapses into a generic white corridor with double doors.
- Station-side world is lost.
- Anchor outfit is lost.
- The prompt gets overinterpreted as a literal interior doorway set-piece.

### verse1_b1
Prompt:
- End: `The same Korean female idol takes the next steps lower and keeps the rail in reach.`

Image:
- `C:\Users\Desktop\Documents\ComfyUI\output\keyframes\verse_1_b1_end_00001_.png`

Assessment:
- Severe mismatch.
- The intended stair-descent/rail geometry is not visible.
- The image reuses the same corridor-door family as `intro_b2`.
- Anchor outfit is lost.
- This suggests REF is not preserving either the archetype or the anchor strongly enough here.

### pre_chorus_b2
Prompt:
- End: `The same Korean female idol pushes through the opening with her weight forward.`

Image:
- `C:\Users\Desktop\Documents\ComfyUI\output\keyframes\pre_chorus_b2_end_00001_.png`

Assessment:
- Partial match at the action level, bad match at the image level.
- The image does show a body pushing through an opening.
- But it exaggerates into a theatrical double-door pose.
- It does not read like a natural MV threshold handoff.
- Anchor outfit is lost.

### chorus_b2
Prompt:
- End: `The same Korean female idol passes beyond the turnstile and keeps going.`

Image:
- `C:\Users\Desktop\Documents\ComfyUI\output\keyframes\chorus_b2_end_00001_.png`

Assessment:
- Weak match.
- The image still uses the generic doorway family instead of a believable gate-pass or turnstile continuation.
- Identity/outfit drift persists.

### verse2_b1
Prompt:
- End: `The same Korean female idol keeps moving along the edge as her grip tightens.`

Image:
- `C:\Users\Desktop\Documents\ComfyUI\output\keyframes\verse_2_b1_end_00001_.png`

Assessment:
- Mismatch.
- The image again drifts into a door/corridor family.
- The intended edge-contact/guided movement is not clear.
- Anchor outfit is lost.

### bridge_b1
Prompt:
- End: `The same Korean female idol keeps the shortened stride and leaves widening footprints behind.`

Image:
- `C:\Users\Desktop\Documents\ComfyUI\output\keyframes\bridge_b1_end_00004_.png`

Assessment:
- Structure match, anchor mismatch.
- The image finally respects the wet-ground footprint idea.
- The composition is usable as a “compression/reset” frame.
- But the full-run output still loses the curated anchor outfit and returns a different school-uniform-like character.
- This means the prompt grammar improved the shot archetype, but anchor reuse is still failing.

### bridge_b2
Prompt:
- End: `The same Korean female idol continues across as the lane opens toward the curb.`

Image:
- `C:\Users\Desktop\Documents\ComfyUI\output\keyframes\bridge_b2_end_00001_.png`

Assessment:
- Medium match on motion.
- The street continuation is readable.
- But anchor identity/outfit is still off.

### final_chorus_b1
Prompt:
- End: `The same Korean female idol lengthens her stride and keeps moving down the path.`

Image:
- `C:\Users\Desktop\Documents\ComfyUI\output\keyframes\final_chorus_b1_end_00002_.png`

Assessment:
- Partial match.
- Crosswalk/open-street release is visible.
- But the image feels too centered and static for a release crossing.
- Anchor drift persists.

### final_chorus_b3
Prompt:
- End: `The same Korean female idol clears the threshold and keeps going on the far side.`

Image:
- `C:\Users\Desktop\Documents\ComfyUI\output\keyframes\final_chorus_b3_end_00003_.png`

Assessment:
- Weak match.
- The prompt intends threshold clearing.
- The image collapses into a generic platform/yellow-line walk.
- The threshold handoff is not clearly visible.

### final_chorus_b4
Prompt:
- End: `The same Korean female idol clears the station exit and continues into the open street.`

Image:
- `C:\Users\Desktop\Documents\ComfyUI\output\keyframes\final_chorus_b4_end_00001_.png`

Assessment:
- Mismatch.
- The image becomes an exaggerated off-balance pose on a platform lane.
- It does not read like an exit crossing into open street.

## Key Failure Modes

### 1. Anchor drift is the biggest blocker
The anchor image is stable:
- `C:\Users\Desktop\Documents\ComfyUI\output\anchors\character_master_00002_.png`

But many REF outputs switch to:
- white shirt + black tie
- blue pleated skirt
- white sneakers

This is not a small variance. It is a full wardrobe/character regime shift.

### 2. Threshold/doorway prompts over-collapse into corridor-set imagery
Prompt families involving:
- opening
- doorway
- passing through
- threshold

often become:
- white corridor
- symmetric double doors
- over-staged portal shots

### 3. Some successful archetype improvements survived
The archetype work is not wasted.

Clear improvements are visible in:
- gate/turnstile crossing
- wet-platform footprint trail
- platform-edge / crosswalk surface grounding

So the prompt grammar work is helping with scene structure.

### 4. But image-model conditioning still beats prompt structure in hard cases
When the prompt enters:
- doorway handoff
- threshold release
- indoor neutral passage

the image model often snaps to a familiar but wrong visual cliché.

## Current Interpretation

The project is no longer blocked mainly by dirty prompt wording.

It is now blocked by:
- incomplete REF anchor preservation
- some archetypes still triggering the wrong visual prior in Flux REF

This means the next work should not be “just more wording cleanup.”

It should focus on:
- stronger anchor preservation in REF generation
- reducing archetypes that trigger corridor/portal collapse
- retesting only the failing families with the current anchor

## Recommended Next Targets

1. Stabilize anchor reuse before wider prompt tuning.
2. Re-study doorway/threshold family with the actual full-run anchor, not only isolated probe wins.
3. Split `threshold_crossing` into:
   - outdoor crossing
   - doorway crossing
   because they are not behaving the same in the model.
4. Keep `bridge_b1` wet-footprint family; that was a real improvement.
