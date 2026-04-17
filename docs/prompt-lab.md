# Prompt Lab

Use this document when testing prompt syntax outside the main ai-mv pipeline.

Purpose:
- isolate model/workflow prompt behavior from repo-side prompt assembly
- learn the best-performing syntax before encoding it into style packs or stage logic
- document prompt patterns as reusable evidence instead of folklore

Why this exists:
- the main repo currently transforms prompts through multiple layers
  - style prompt seed/draft builders
  - render-item merging
  - still-stage sanitization and single-keyframe constraints
  - clip-mode-specific prompt reshaping
- if a render fails inside the full pipeline, it is hard to tell whether the root cause is:
  - model/workflow prompt sensitivity
  - style-pack wording
  - repo-side prompt post-processing
  - routing or config
- this lab separates those concerns.

## Scope

The prompt lab is for direct workflow-facing experiments, not full MV runs.

In-scope:
- Qwen still prompt syntax
- LTX i2v prompt syntax
- LTX ia2v prompt syntax
- LTX flf2v prompt syntax
- negative-prompt patterns
- seed sensitivity notes
- aspect-ratio or resolution notes when they materially affect prompt adherence

Out-of-scope:
- final MV quality claims from a single isolated prompt win
- changing pipeline routing based on one ad-hoc experiment
- mixing prompt syntax conclusions with style-pack product truth before repetition

## Core rule

First prove the syntax directly against the target model/workflow.
Only then encode the winning pattern into:
- `styles/*/prompting.py`
- `core/planning/render_items.py`
- `core/stages/render_stills.py`
- `core/stages/render_clips.py`

## Required separation

Treat these as three different questions:

1. Model syntax question
- What wording does the target model/workflow respond to best?

2. Repo contract question
- What fields should ai-mv produce for that workflow?

3. Repo post-processing question
- What sanitization or constraints are still safe after the winning syntax is known?

Do not answer 2 or 3 before 1 is grounded.

## Experiment tracks

### A. Still-image track
Target:
- Qwen still generation

What to optimize for:
- prompt adherence
- single-scene integrity
- no comic-panel/contact-sheet/collage failure
- motion-safe keyframe suitability
- stable subject/environment framing

Compare syntax families:
- comma-token list
- short declarative sentence
- structured field style
- cinematic imperative style

Example evaluation questions:
- Did the requested subject appear clearly?
- Did the requested environment appear clearly?
- Is the image one scene rather than multiple inset scenes?
- Is the still usable as an i2v/flf2v source image?

### B. i2v track
Target:
- LTX i2v

What to optimize for:
- stable motion from a single source still
- restrained camera language
- continuity-friendly motion wording
- low identity drift / low pose collapse

### C. ia2v track
Target:
- LTX ia2v

What to optimize for:
- performance or music-responsive motion wording
- audio-reactive language that does not destabilize identity
- section-appropriate energy

### D. flf2v track
Target:
- LTX flf2v

What to optimize for:
- endpoint compatibility
- bridge/transition wording
- short transition prompts rather than generic full-shot prompts

## Benchmark case design

Use a fixed benchmark set instead of random prompts.
Each benchmark case should record:
- case_id
- workflow target
- concept intent
- must-have visual elements
- must-not-have artifacts
- composition target
- motion-safety requirement
- section role if relevant

Recommended representative cases:
- close-up emotional portrait
- walking street scene
- performance/singing shot
- chorus energy shot
- bridge transition shot
- dense neon environment shot
- reflective night-window shot
- identity continuity follow-up shot

## Evaluation rubric

For each output, score or tag at least these:
- subject fidelity
- environment fidelity
- composition fidelity
- style fidelity
- single-scene integrity
- motion-safe source suitability
- continuity friendliness
- artifact presence

Failure tags should be explicit, for example:
- panel_layout
- collage_layout
- split_screen
- duplicate_subject
- identity_drift
- weak_environment_match
- weak_subject_match
- overdecorated_prompt_response
- motion_fragile_frame

## Minimum repetition rule

Do not promote a syntax pattern into repo truth from one good result.
Minimum recommendation:
- test the same syntax on multiple benchmark cases
- test multiple seeds when seed sensitivity is suspected
- record both wins and failures

## Promotion rule into main repo

Only promote a prompt pattern into the main repo when all are true:
- it beats or matches current syntax on multiple benchmark cases
- its failures are understood and documented
- it maps cleanly to the ai-mv prompt contract
- it does not rely on one lucky seed only

## Deliverables from this lab

The prompt lab should continuously produce two artifacts:

1. Best Syntax Catalog
- workflow-specific winning grammar patterns
- bad grammar patterns to avoid
- notes on sensitivity and failure modes

2. Experiment Log
- exact prompts
- negative prompts
- seeds
- sizes/settings
- results and failure tags

Use the templates in `docs/templates/` for both.

## Relationship to current repo code

Current repo prompt assembly locations to update only after lab findings are stable:
- `src/ai_mv/core/planning/render_items.py`
- `src/ai_mv/core/stages/render_stills.py`
- `src/ai_mv/core/stages/render_clips.py`
- `src/ai_mv/styles/citypop/prompting.py`
- `src/ai_mv/styles/synthwave/prompting.py`

Current still post-processing already adds a strong single-keyframe constraint layer. That is useful for production safety, but it should not be confused with first-principles prompt-syntax research.

## Practical workflow

1. Select one workflow track.
2. Select one benchmark case.
3. Write 2-4 syntax variants.
4. Keep all non-prompt settings stable.
5. Render.
6. Log exact settings and results.
7. Tag failure modes.
8. Repeat on more benchmark cases.
9. Update the Best Syntax Catalog.
10. Only then modify ai-mv code.

## Decision rule for current project phase

At the current maturity level of ai-mv, prioritize this order:
1. still prompt syntax reliability
2. still prompt contract inside ai-mv
3. clip prompt syntax by workflow
4. final publishability refinement

Reason:
- weak still adherence poisons downstream clip quality and makes review improvements less valuable.
