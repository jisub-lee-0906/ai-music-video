# REF Bridge / Platform Motion Study (2026-04-03)

## Goal
- Test `Flux.2.dev REF` prompt structures for a harder bridge-family shot.
- Specifically measure whether prompt-only changes can increase motion while preserving:
  - platform background
  - readable locomotion
  - trace/content detail
- Ignore current planner/profile constraints and study the image model response directly.

## Fixed Setup
- Anchor image:
  - [character_master_00002_.png](C:/Users/Desktop/Documents/ComfyUI/output/anchors/character_master_00002_.png)
- Workflow:
  - `ComfyUI Flux.2 dev image reference`
- Shot target:
  - bridge-like wet platform motion with footprint trace

## Motion Spectrum Findings

### Best Overall
- Prompt:
  - `The same Korean female idol cuts a crossing step along the wet platform edge at night, the yellow line tight at her feet and her footprints widening behind her.`
- Output:
  - [ref_bridge_b1_step_cross_line_end_00001_.png](C:/Users/Desktop/Documents/ComfyUI/output/keyframes/ref_bridge_b1_step_cross_line_end_00001_.png)
- Why it worked:
  - platform geometry stays obvious
  - yellow tactile line anchors the feet
  - motion reads as a real step change, not a pose
  - footprint trail survives as supporting content

### Strong Alternate
- Prompt:
  - `The same Korean female idol takes a shorter step along the wet platform edge at night, the yellow line close at her feet and her footprints widening behind her.`
- Output:
  - [ref_bridge_b1_step_short_line_end_00001_.png](C:/Users/Desktop/Documents/ComfyUI/output/keyframes/ref_bridge_b1_step_short_line_end_00001_.png)
- Why it worked:
  - very stable platform background
  - readable locomotion
  - slightly gentler than `cuts a crossing step`

### Geometry + Contact Alternate
- Prompt:
  - `The same Korean female idol takes the next step along the wet platform edge at night, one hand trailing the platform rail as her footprints widen behind her.`
- Output:
  - [ref_bridge_b1_rail_trace_end_00001_.png](C:/Users/Desktop/Documents/ComfyUI/output/keyframes/ref_bridge_b1_rail_trace_end_00001_.png)
- Why it worked:
  - keeps the platform literal
  - rail contact helps structure
- Limitation:
  - motion change is weaker than the best two prompts

## Failed Motion Directions

### Pose Exaggeration
- `arm_swing`
  - [ref_bridge_b1_arm_swing_end_00001_.png](C:/Users/Desktop/Documents/ComfyUI/output/keyframes/ref_bridge_b1_arm_swing_end_00001_.png)
- Result:
  - turns into a pose / dance-like frame
  - too much gesture, not enough story keyframe continuity

### Rear / Over-Rotation Drift
- `shoulder_turn`
  - [ref_bridge_b1_shoulder_turn_end_00001_.png](C:/Users/Desktop/Documents/ComfyUI/output/keyframes/ref_bridge_b1_shoulder_turn_end_00001_.png)
- Result:
  - rear-view drift
  - loses the intended forward bridge relation

### Environment-Dominant but Low Motion
- `column_pass`
  - [ref_bridge_b1_column_pass_end_00001_.png](C:/Users/Desktop/Documents/ComfyUI/output/keyframes/ref_bridge_b1_column_pass_end_00001_.png)
- Result:
  - strong platform layout
  - weak movement and weak dramatic function

## Factorized Axis Findings

### Motion Only
- Example:
  - [ref_bridge_b1_factorized_motion_only_01_end_00001_.png](C:/Users/Desktop/Documents/ComfyUI/output/keyframes/ref_bridge_b1_factorized_motion_only_01_end_00001_.png)
- Result:
  - motion appears
  - scene drifts into other archetypes such as street/crosswalk/steps
- Conclusion:
  - motion-only is unstable

### Background Only
- Example:
  - [ref_bridge_b1_factorized_background_only_03_end_00001_.png](C:/Users/Desktop/Documents/ComfyUI/output/keyframes/ref_bridge_b1_factorized_background_only_03_end_00001_.png)
- Result:
  - platform world stays very stable
  - motion nearly disappears
- Conclusion:
  - background is the best stabilizing base layer

### Content Only
- Example:
  - [ref_bridge_b1_factorized_content_only_01_end_00001_.png](C:/Users/Desktop/Documents/ComfyUI/output/keyframes/ref_bridge_b1_factorized_content_only_01_end_00001_.png)
- Result:
  - footprint detail survives
  - scene invents the wrong environment
- Conclusion:
  - trace/content detail cannot be the nucleus

## Prompt Structure Study

### Best Prompt Form
- Prompt:
  - `The same Korean female idol with a high ponytail takes a crossing step along the wet platform edge at night, the yellow tactile line close at her feet and her footprint trail widening behind her.`
- Output:
  - [ref_bridge_b1_flux_natural_compact_end_00001_.png](C:/Users/Desktop/Documents/ComfyUI/output/keyframes/ref_bridge_b1_flux_natural_compact_end_00001_.png)
- Assessment:
  - best overall balance of background, motion, and trace detail

### Strong Alternate
- Prompt:
  - `The same Korean female idol with a high ponytail takes a crossing step along the wet platform edge at night, her front foot cutting across the yellow tactile line while the dark rail tracks and platform columns stay visible behind her, and her footprint trail widens behind her.`
- Output:
  - [ref_bridge_b1_flux_geometry_reinforced_end_00001_.png](C:/Users/Desktop/Documents/ComfyUI/output/keyframes/ref_bridge_b1_flux_geometry_reinforced_end_00001_.png)
- Assessment:
  - slightly heavier and more literal
  - still strong

### Not Better as a Default
- `identity_reinforced`
  - [ref_bridge_b1_flux_identity_reinforced_end_00001_.png](C:/Users/Desktop/Documents/ComfyUI/output/keyframes/ref_bridge_b1_flux_identity_reinforced_end_00001_.png)
- `style_context_reinforced`
  - [ref_bridge_b1_flux_style_context_reinforced_end_00001_.png](C:/Users/Desktop/Documents/ComfyUI/output/keyframes/ref_bridge_b1_flux_style_context_reinforced_end_00001_.png)
- `json_structured`
  - [ref_bridge_b1_flux_json_structured_end_00001_.png](C:/Users/Desktop/Documents/ComfyUI/output/keyframes/ref_bridge_b1_flux_json_structured_end_00001_.png)
- Assessment:
  - readable, but not better than compact natural language in this workflow

## What This Taught Us

### 1. Build order matters
- Best order:
  - dominant surface geometry
  - locomotion change
  - one trace/content detail

### 2. Good motion is directional foot change, not gesture exaggeration
- Best:
  - `crossing step`
  - `shorter step`
  - `next step`
- Worse:
  - `arm swing`
  - `shoulder turn`

### 3. Compact natural language beats heavier formats here
- Short, direct subject-action-context prose performed better than:
  - over-specified identity strings
  - style-heavy add-ons
  - structured JSON prompt payloads

## Updated Bridge / Platform Motion Pattern
- Recommended pattern:
  - `The same Korean female idol with a high ponytail takes a crossing step along the wet platform edge at night, the yellow tactile line close at her feet and her footprint trail widening behind her.`

## Avoid
- gesture-first motion
- shoulder-turn-first motion
- content-only footprint prompts
- style-heavy padding when compact geometry-first prose already works
