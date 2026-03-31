# Seedance v2 Prompting Reference

Last updated: 2026-03-31

This document is the working reference for prompt writing in the Seedance-style v2 pipeline.

It is meant to be consulted continuously while improving planner outputs for:

- `FLUX.2 [dev]` text-to-image (`TTI`)
- `FLUX.2 [dev]` image editing / reference-image generation (`REF`)
- `Wan 2.2 FLF2V` first-last-frame interpolation (`WAN`)

This document separates:

- official model guidance from primary sources
- project-specific interpretation for this pipeline
- practical prompt rules that the planner should follow

## 1. Primary sources

Official sources used for this reference:

- [BFL FLUX.2 Prompting Guide](https://docs.bfl.ai/guides/prompting_guide_flux2)
- [BFL FLUX Prompting Fundamentals](https://docs.bfl.ai/guides/prompting_guide_t2i_fundamentals)
- [BFL FLUX.2 Image Editing](https://docs.bfl.ai/flux_2/flux2_image_editing)
- [BFL FLUX.2 Overview](https://docs.bfl.ai/flux_2)
- [ComfyUI Wan 2.2 official workflow tutorial](https://docs.comfy.org/tutorials/video/wan/wan2_2)
- [ComfyUI Wan 2.2 FLF2V announcement](https://blog.comfy.org/p/wan22-flf2v-comfyui-native-support)

## 2. Official guidance distilled

### 2.1 FLUX.2 text prompting fundamentals

From the BFL docs, the stable baseline is:

- Use `Subject + Action + Style + Context`
- Put the most important thing first
- Use structured natural language, not loose keyword bags
- Start short and add only details that materially change the image
- For photorealism, camera and lens references can help
- FLUX.2 does not use negative prompts

What matters most for this project:

- word order matters
- earlier tokens carry more weight
- the subject must not be buried behind atmosphere or setting
- prompts should describe what is desired, not a list of exclusions

### 2.2 FLUX.2 reference-image / image-editing guidance

From the BFL image-editing docs:

- image editing uses both text and input image
- reference images are best used by clearly describing each image's role
- multi-reference is explicitly useful for character consistency
- the text should describe what changes, while the input image carries visual identity

What matters most for this project:

- the anchor image should carry identity
- REF text should carry scene grounding and action
- ref prompts should not redundantly restate every facial detail the image already contains
- if multiple reference inputs exist, their role must be explicit

### 2.3 Wan 2.2 FLF2V guidance

From the official ComfyUI Wan 2.2 tutorial:

- upload the first frame
- upload the last frame
- write prompts appropriate to the first and last frames

What matters most for this project:

- WAN is not a fresh scene generator
- WAN prompt must fit both boundary frames
- WAN prompt should describe the motion or transition implied between start and end

## 3. Project interpretation

These rules are not directly stated in one official doc. They are the practical interpretation for this pipeline.

### 3.1 TTI role

`TTI` is not a beauty shot generator.

Its job is to create a reusable anchor image for later `REF` generation.

That means TTI must optimize for:

- single clearly readable subject
- stable face and hair read
- stable outfit silhouette
- stable footwear read
- clean body proportions
- minimal background competition
- a composition that remains useful when later pushed into new scenes

### 3.2 REF role

`REF` is the keyframe generator and the most important stage.

Its job is not to create a generic mood image.

Its job is to create a character-centered cinematic keyframe that reads:

- who this person is
- where she is
- what she is doing
- how her body is physically grounded in the space and light

REF must produce keyframes that chain naturally:

- `start1 -> end1 -> end1(start2) -> end2 -> end2(start3) -> end3`

That means `start` and `end` are not two independent captions. They are adjacent states in a continuous performance.

### 3.3 WAN role

`WAN` is the bridge between REF keyframes.

Its job is to describe the change between the two boundary frames, not to invent a new scene grammar.

WAN text should mainly capture:

- the subject's movement or shift
- the change in pose, direction, or momentum
- the stable surrounding environment
- light or atmosphere changes only if they are visible in the boundary frames

## 4. Pipeline prompt philosophy

The profile and the planner must do different jobs.

### 4.1 Profile

The profile should answer:

- what kind of music video the user wants
- what kind of world it belongs to
- who the protagonist is
- what emotional and visual direction is desired

The profile should not directly write render prompts.

The profile should avoid over-specifying:

- shot grammar
- camera plans
- transition instructions
- rigid family-based visual slotting
- canned prompt fragments

### 4.2 Planner

The planner should act like a director.

The planner should transform intent into natural render prose that feels authored, not normalized.

The planner should decide:

- what the protagonist is doing now
- how the environment supports that action
- what changes from start to end
- how one keyframe leads into the next

### 4.3 Prompt path rule

Internal sequencing metadata may exist for planning, but it must not contaminate render prompts.

Do not leak into final render prose:

- `camera`
- `shot`
- `frame`
- `cut`
- `continuity`
- `transition`
- `environment_family`
- `prop_family`
- any similar planning label

## 5. TTI prompt rules for FLUX.2 [dev]

### 5.1 Goal

Generate a strong character anchor that can survive later reference-image edits.

### 5.2 Required structure

TTI should usually follow:

`Subject -> pose/action -> visual identity -> simple context`

### 5.3 What to include

- single female subject only
- face visibility or readable three-quarter identity
- hair shape and color
- outfit silhouette
- footwear visibility
- neutral or simple background
- enough light to read facial structure and clothing

### 5.4 What to avoid

- crowded environment detail
- poetic environment-first openings
- multiple competing props
- ambiguous body pose
- cropped-away shoes when footwear continuity matters
- cinematic meta labels instead of visual description
- negative prompts

### 5.5 Good TTI pattern

Use prose like:

- subject first
- readable pose second
- identity details third
- minimal environment last

Example pattern:

`A Korean female idol with long dark hair stands facing slightly left, her face clearly visible, wearing a fitted black stage jacket, short skirt, and dark ankle boots, clean full-body portrait against a simple dim station exterior at night with soft reflected neon on the ground.`

### 5.6 Bad TTI pattern

Avoid patterns like:

- setting first, subject late
- moody abstraction before identity
- hidden face or hidden feet
- floating styling words with no physical description

Bad pattern:

`A lonely rainy night outside a station with cinematic reflections and melancholy atmosphere, a beautiful idol somewhere in the frame.`

Why bad:

- subject is buried
- anchor identity is weak
- composition is too ambiguous for stable downstream reuse

## 6. REF prompt rules for FLUX.2 [dev] reference-image generation

### 6.1 Goal

Use the anchor image to generate a strong keyframe of the same person in a specific scene state.

### 6.2 Required structure

REF should usually follow:

`Subject -> action -> grounded environment -> light`

In practice, the sentence may read naturally, but subject and action must remain front-loaded.

### 6.3 What the reference image should carry

The reference image should carry:

- face identity
- hair identity
- outfit identity
- overall character consistency

### 6.4 What the REF text should carry

The REF text should carry:

- where she is
- what she is physically doing
- what object or surface she touches, crosses, faces, or leaves
- what the local light is doing in the scene

### 6.5 REF rules

- keep one clear subject
- write an action that reveals the body in space
- prefer physical verbs over vague emotional verbs
- make the environment support the action
- keep the action visually legible
- use atmospheric detail only if it helps grounding
- make `start` and `end` adjacent, not unrelated

### 6.6 Prefer these action types

Prefer actions that create visible grounding:

- walking past
- stepping onto
- leaning on
- pushing through
- turning toward
- stopping at
- lifting a hand to
- brushing past
- climbing
- descending

These are usually stronger than:

- remembering
- watching
- feeling
- waiting
- standing there
- holding still

The weaker verbs are not banned, but they often produce static mood shots instead of usable keyframes.

### 6.7 Avoid these failure patterns

- environment dominating the sentence before the subject appears
- object admiration instead of embodied action
- body-part fixation such as toes, lips, eyelashes, fingers unless truly essential
- decorative prose that does not change the rendered pose
- background-only beauty language
- prompts that read like captions for a mood board rather than directions for a keyframe

### 6.8 Good REF pattern

`The same Korean female idol steps out along the wet station road, her dark hair shifting as she passes under red and blue neon reflected across the pavement.`

Why this works:

- subject is first
- the action is visible
- the space is physically connected to the body
- lighting is present but not dominant

### 6.9 Bad REF pattern

`A station threshold at night with a platform clock holding the darkness while she watches it in silence.`

Why this fails:

- the place and object dominate
- the subject is secondary
- the action is weak and static
- this tends to produce a mood image instead of a character keyframe

## 7. WAN prompt rules for Wan 2.2 FLF2V

### 7.1 Goal

Describe the visible transition between the start keyframe and the end keyframe.

### 7.2 Required structure

WAN should usually follow:

`Subject -> motion/change -> stable environment -> visible light/atmosphere`

### 7.3 WAN rules

- write to both frames at once
- describe the movement from start toward end
- avoid introducing a new subject or a new space
- avoid describing details not supported by either boundary frame
- keep the sentence compact and motion-led

### 7.4 Positive prompt emphasis

The positive prompt should emphasize:

- directional movement
- posture change
- interaction with the same space
- continuity of light and weather

### 7.5 Negative prompt use

Unlike FLUX.2, Wan pipelines may still use negative prompts at the workflow level.

For this project:

- negative prompts are allowed in `WAN`
- but they should stay minimal and targeted
- do not use a growing library of hardcoded quality slogans
- do not encode planner logic into WAN negatives

Good WAN negatives are simple suppression terms tied to failure modes already observed in outputs.

### 7.6 Good WAN pattern

`The same Korean female idol walks forward along the wet station pavement, shifting from a still pause into a steady stride while the neon reflections stay stretched under her feet.`

Why this works:

- motion is explicit
- the prompt bridges two states
- the space remains stable

### 7.7 Bad WAN pattern

`A cinematic transition shot between two dramatic frames as the camera follows her through a continuous emotional beat.`

Why this fails:

- contains planning meta
- does not describe visible motion clearly
- reads like workflow instruction, not render prose

## 8. Language and style rules

### 8.1 Render prose should be direct

Prefer direct visual prose over abstract poetic prose.

Good:

- physically readable
- body-grounded
- visually actionable

Bad:

- conceptual
- symbolic
- over-literary
- dependent on internal design vocabulary

### 8.2 Korean to English rendering

Korean beat content should not be discarded.

Translate it into natural English render prose that preserves:

- the concrete action
- the emotional direction
- the environmental cues

Do not transliterate planning notes. Rewrite them into visual prose.

### 8.3 Camera language

Official FLUX docs allow camera and lens references for photorealism.

For this project, use caution.

Allowed:

- explicit camera references in `TTI` only when they materially improve anchor readability
- rare camera references in `REF` only if they help a specific photoreal result without introducing meta-heavy prompt text

Avoid in normal planner render prose:

- `camera`
- `shot`
- `frame`
- `close-up`
- `cut`
- `dolly`
- `tracking shot`

Reason:

- even if some models can understand them, this pipeline wants render prose that describes the image itself, not production instructions

## 9. Hard bans for this pipeline

These should not appear in final render prompts unless there is a very specific exception:

- planning labels
- family labels
- camera-plan language
- continuity-plan language
- fallback filler prose
- hardcoded quality slogans
- templated identity-lock prose repeated across all scenes

Examples of bad contamination:

- `one woman only`
- `same face, same hair, same outfit`
- `same space`
- `keep moving naturally`
- `the place reads clearly`
- `abrupt viewpoint reset`

These may improve some failures in the short term, but they degrade authored prompt quality and push the system toward rigid postprocessing instead of better planning.

## 10. Prompt review checklist

Use this checklist before accepting planner output.

### 10.1 TTI checklist

- Is the subject first?
- Is there exactly one readable character?
- Are face, hair, outfit, and footwear readable?
- Is the background simple enough not to compete?
- Would this image work as a reusable identity anchor?

### 10.2 REF checklist

- Is the same person clearly the center of the frame?
- Does the text clearly say what she is doing?
- Is the action physically grounded in the environment?
- Does the environment support rather than overpower her?
- Does the prompt avoid meta language?
- Does the sentence feel like a keyframe, not a mood-board caption?
- Would this `end` naturally lead into the next shot's `start`?

### 10.3 WAN checklist

- Does the text describe change between the two boundary frames?
- Does it stay inside the same scene and identity?
- Is the motion visually explicit?
- Are there no new unsupported objects or narrative ideas?
- Is the negative prompt minimal instead of over-engineered?

## 11. Decision rules when outputs are bad

When results fail, diagnose in this order:

1. Is the subject buried behind setting?
2. Is the action too static or too vague?
3. Is the environment doing more work than the character?
4. Is the prompt too poetic to produce a stable pose?
5. Is the start/end difference too weak to guide WAN?
6. Is the anchor image itself insufficiently readable?

Fix by improving authored planner prompts first.

Do not fix by reintroducing:

- keyword sanitizers
- family-based render fallback
- templated subject-lock prose
- action replacement rules
- canned continuity phrases

## 12. Practical defaults for this project

Use these defaults unless evidence suggests otherwise.

### 12.1 TTI default

- one subject
- readable face
- readable full-body or strong three-quarter body
- outfit and shoes visible
- simple environment
- concise direct prose

### 12.2 REF default

- one subject
- one clear physical action
- one stable environment
- one readable local light description
- no planning meta
- no identity-lock slogans

### 12.3 WAN default

- one subject
- one visible transition
- same environment
- brief positive prompt
- minimal negative prompt

## 13. How to use this document in future prompt work

When changing planner prompting:

1. Check the relevant section in this document first.
2. Decide whether the issue belongs to `TTI`, `REF`, or `WAN`.
3. Prefer better authored prompt instructions over code-side cleanup.
4. Verify with preview text before image generation.
5. Verify with actual outputs after image generation.
6. Update this document when a rule changes based on evidence.

This document should remain the stable reference, while prompt wording evolves underneath it.
