# Seedance v2 REF Probe Review (2026-03-31)

## Scope
- Run state reviewed: `seedance-v2-visual-probe-20260331a`
- Prompt source used for mapping: [workflow_inputs_preview.json](D:/workspace/ai-music-video/artifacts/preflight/seedance-v2-render-verbalizer-20260331o/workflow_inputs_preview.json)
- Image source reviewed: `C:\Users\Desktop\Documents\ComfyUI\output`

## High-Level Result
- `TTI` is strong enough to serve as an anchor.
- `REF` is not yet reliable enough for the intended one-person cinematic MV pipeline.
- The dominant failure is not random noise. It is consistent prompt-to-image behavior:
  - environment tokens overpower heroine/action
  - start/end action delta is often too small
  - anchor wardrobe/footwear continuity drifts under scene pressure
  - some prompts invite centered architectural staging instead of natural keyframes

## TTI
- Prompt:
  - `cinematic live-action Korean pop music video with premium realism... Neutral presentation pose, pale grey backdrop, soft controlled studio lighting, clean full-body cinematic key reference.`
- Image:
  - [character_master_00042_.png](C:/Users/Desktop/Documents/ComfyUI/output/anchors/character_master_00042_.png)
- Result:
  - clear face, ponytail, cardigan, denim skirt, silver boots
  - clean silhouette and readable footwear
  - no background competition
- Conclusion:
  - `TTI` is not the main bottleneck right now

## 1:1 REF Mapping

### intro_b1
- Prompt start:
  - `The same Korean female idol moves beneath the rain-washed station sign at a rainy station entrance at night, the wet ground shining under thin neon ripples.`
- Prompt end:
  - `The same Korean female idol passes fully under the station sign and into the brighter strip of rain-lit pavement.`
- Images:
  - [intro_b1_start_00005_.png](C:/Users/Desktop/Documents/ComfyUI/output/keyframes/intro_b1_start_00005_.png)
  - [intro_b1_end_00005_.png](C:/Users/Desktop/Documents/ComfyUI/output/keyframes/intro_b1_end_00005_.png)
- What happened:
  - very strong match to anchor identity and outfit
  - environment supports the heroine instead of swallowing her
  - start and end are almost the same frame with only a tiny gait shift
- Prompt lesson:
  - compact environment tokens plus direct walking action work well
  - but the start/end delta is too weak, so chain progression feels underpowered

### verse1_b1
- Prompt start:
  - `The same Korean female idol tightens her grip on the umbrella handle in a narrow station-side passage at night, raindrops beading along the wet umbrella edge beside a folded ticket.`
- Prompt end:
  - `The same Korean female idol draws the folded ticket partway free while keeping the umbrella steady at her side in the narrow station-side passage at night.`
- Image:
  - [verse_1_b1_end_00003_.png](C:/Users/Desktop/Documents/ComfyUI/output/keyframes/verse_1_b1_end_00003_.png)
- What happened:
  - the model turned this into a centered doorway composition
  - the action became broader and more theatrical than the prompt implies
  - anchor continuity softened but did not fully collapse
- Prompt lesson:
  - prop-heavy micro-actions like `umbrella handle`, `folded ticket`, `at her side` can pull the model into a staged tableau instead of a natural MV frame
  - the frame becomes architecture-first when the action is small and the setting suggests symmetry

### pre_chorus_b1
- Prompt start:
  - `The same Korean female idol leans into the narrowing gate opening at a station edge at night and braces against the closing slats.`
- Prompt end:
  - `The same Korean female idol pushes farther through the tightening gap and shifts her weight toward the exit.`
- Image:
  - [pre_chorus_b1_end_00002_.png](C:/Users/Desktop/Documents/ComfyUI/output/keyframes/pre_chorus_b1_end_00002_.png)
- What happened:
  - the heroine becomes secondary
  - the clock and wall dominate the composition
  - the image reads like a stylized platform mood shot rather than a heroine-centered keyframe
- Prompt lesson:
  - `narrowing gate`, `closing slats`, `station edge`, `threshold` are good dramatic ideas
  - but when the visual world already contains strong station symbols, the model may replace the intended action with a more legible station icon such as a large clock or wall geometry
  - compression prompts are especially vulnerable to environment takeover

### bridge_b1
- Prompt start:
  - `The same Korean female idol edges through a tight station pocket at night as station lights dim over faded glass reflections.`
- Prompt end:
  - `The same Korean female idol shifts a little farther through the quiet light while the reflections thin behind her.`
- Image:
  - [bridge_b1_end_00002_.png](C:/Users/Desktop/Documents/ComfyUI/output/keyframes/bridge_b1_end_00002_.png)
- What happened:
  - the heroine is tiny and far from the viewer
  - the frame is almost entirely about the ticket gate space
  - the prompt's `tight station pocket` became architectural depth instead of personal compression
- Prompt lesson:
  - abstract environment phrases such as `tight station pocket`, `quiet light`, `faded glass reflections` are too easy for the model to resolve as a distant wide shot
  - when the action is minimal, the model uses architecture to satisfy the prompt

### bridge_b2
- Prompt start:
  - `The same Korean female idol turns back once, then faces the path ahead under the distant platform lights and city glow in a tight station pocket at night.`
- Prompt end:
  - `The same Korean female idol settles into the forward direction and starts moving again beneath the map-like glow.`
- Image:
  - [bridge_b2_end_00002_.png](C:/Users/Desktop/Documents/ComfyUI/output/keyframes/bridge_b2_end_00002_.png)
- What happened:
  - the model produced a compelling train-platform interaction frame
  - but the anchor outfit and footwear drifted badly
  - the action was reinterpreted as touching the train window between cars
- Prompt lesson:
  - `turns back once`, `path ahead`, `distant platform lights`, `city glow` are loose enough that the model invents a stronger physical action
  - when the prompt does not keep the heroine-body relationship specific enough, the model may choose a visually striking but continuity-breaking gesture

### final_chorus_b1
- Prompt start:
  - `The same Korean female idol steps into the neon doorway at the end of the night in the brightest station-side opening.`
- Prompt end:
  - `The same Korean female idol moves deeper through the doorway as the night falls back around the frame.`
- Image:
  - [final_chorus_b1_end_00002_.png](C:/Users/Desktop/Documents/ComfyUI/output/keyframes/final_chorus_b1_end_00002_.png)
- What happened:
  - the frame again becomes centered and architectural
  - the bright doorway is visually strong, but the heroine reads small and pinned to the threshold
  - the image feels more like a stylized location reveal than a heroine-driven payoff keyframe
- Prompt lesson:
  - `brightest opening`, `doorway`, `end of the night` create a strong set-piece image
  - without stronger heroine action weight, the model frames the doorway itself as the subject

## Cross-Shot Findings

### 1. Compact walk prompts perform best
- `intro_b1` worked because the action is simple, visible, and directly body-led.
- Walking through light is more reliable than introspective or prop-led micro-actions.

### 2. Environment stacks are still too strong
- Prompts that include multiple space-defining tokens such as:
  - `station edge`
  - `gate threshold`
  - `closing slats`
  - `glass reflections`
  - `clock`
  - `doorway`
- tend to produce location hero shots instead of heroine hero shots.

### 3. Abstract compression language is dangerous
- `tight station pocket`
- `quiet light`
- `map-like glow`
- `reflections thin behind her`
- These read poetically, but Flux2 REF seems to resolve them as environment mood rather than readable body action.

### 4. Tiny action deltas lead to weak chains
- `intro_b1` shows that start/end can both look good and still fail as a chain if the movement delta is too small.
- `start` and `end` need a clearer body-state difference than one half-step.

### 5. Anchor drift increases when scene pressure rises
- TTI anchor preserved outfit and boots well.
- Under heavy station composition or strong reinterpretation, REF drifted into:
  - different shoes
  - altered silhouette
  - weaker face continuity
- This suggests the prompt is letting scene novelty outrank anchor continuity.

### 6. Symmetry encourages staging
- Doorways, gates, and corridor-like passages repeatedly became centered compositions.
- That is visually clean but often not the intended natural MV keyframe language.

## Prompt Engineering Implications

### Keep
- single heroine
- direct body-led verbs
- one clear environment anchor
- one readable action
- one lighting cue at most

### Reduce
- stacked station symbols in a single prompt
- abstract poetic atmosphere terms
- prop-heavy micro-actions
- phrases that imply distant or architectural framing without saying so

### Increase
- body-state clarity between `start` and `end`
- action that reads in the torso/legs/hands at a glance
- continuity-friendly outfit/body readability in the action sentence itself
- prompts where environment supports motion instead of becoming the main spectacle

## Recommended Next Prompt Pass
- Make REF actions larger and more body-readable.
- Lower the number of environment nouns in compression and threshold shots.
- Prefer:
  - `steps through`
  - `crosses past`
  - `turns into`
  - `draws closer to`
  - `pulls through`
- Avoid:
  - `tight station pocket`
  - `quiet light`
  - `map-like glow`
  - `closing slats`
  - `faded glass reflections`
  - `end of the night`
- For start/end pairs:
  - `start` should show the beginning of a visible move
  - `end` should show the move clearly advanced, not merely repeated

## Bottom Line
- The prompt work is helping, but the current REF prompts are still too permissive about environment dominance.
- The model is telling us something consistent:
  - simple heroine-led motion works
  - symbolic station mood language causes the frame to drift away from the heroine
- The next engineering pass should simplify and de-poeticize the hardest REF prompts before another run.
