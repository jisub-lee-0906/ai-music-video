# AI Instruction Addendum for ai-mv Research and Design

Use this together with:
- `.hermes/plans/2026-04-16_194323-official-research-handoff.md`
- skill: `ai-mv-official-research-sources`

## Why this addendum exists

The current AI context is still missing some precise execution rules.
Without these rules, a future session may:
- over-trust local assumptions
- treat pretty stills as success
- mix still prompting and video prompting
- redesign review without benchmark grounding
- ignore upstream ComfyUI workflow reality

## Missing instructions that should be treated as explicit requirements

### 1. Separate prompt contracts by workflow role
Do not use one shared prompt style for all of these:
- Qwen still generation
- LTX i2v
- LTX ia2v
- LTX flf2v

Required interpretation:
- still prompts should optimize for identity, scene clarity, composition, and motion-safe keyframe usability
- i2v prompts should optimize for stable motion from a single still, not dense still-image decoration
- ia2v prompts should optimize for performance energy, audio responsiveness, and camera restraint
- flf2v prompts should optimize for transition intent between endpoints, using short bridge-style instructions rather than long scene prose

### 2. Treat upstream workflow repos as stronger evidence than local naming
If local workflow JSON names, node assumptions, or binding choices differ from upstream official repos, prefer upstream official evidence.

Priority order for truth:
1. official docs
2. official model card
3. official engine / ComfyUI integration repo
4. official paper / technical report
5. local repo assumptions

### 3. Distinguish 3 different success levels
Every evaluation must explicitly separate:
1. technical completion
2. attractive isolated stills/clips
3. coherent publishable final MV

Do not let the agent collapse these into one notion of "works".

### 4. Review must be split into measurable vs judgment-based signals
Whenever proposing review improvements, classify each check as one of:
- measurable deterministic signal
- heuristic proxy
- model-judged / LLM-judged signal

Examples:
- measurable: coverage, drift, fps, resolution, missing assets
- heuristic proxy: likely weak transition, likely over-busy still
- model-judged: style fit, publishability, emotional coherence

### 5. Do not redesign routing without checking smoke-mode / WSL overrides first
Before discussing whether the repo is making bad workflow choices, first verify whether:
- `planning.enable_ia2v`
- `planning.enable_flf2v`
- WSL smoke mode
are forcing a simplified path.

Otherwise the AI may misdiagnose a config override as a planning-policy failure.

### 6. Judge stills as animation sources, not only as images
For still-generation analysis, the agent must always ask:
- Is this still usable as an i2v source?
- Is it too busy, symmetric, collage-like, or fragile for motion?
- Does it preserve a strong single subject and readable action axis?

### 7. flf2v requires endpoint compatibility, not just bridge labeling
A shot should not be considered flf2v-ready merely because it has:
- `render_mode=flf2v`
- `bridge_to_shot_id`

It should also be evaluated for:
- visual continuity between first and last still
- whether a transition is genuinely needed
- whether the bridge is better expressed as motion than as a cut

### 8. Music-model limits must constrain planning assumptions
The agent must not assume the music model provides:
- perfect structural coherence
- stable style adherence
- precise vocal nuance
- deterministic high-quality outputs

Audio planning and downstream visual planning should be written with explicit awareness of model limitations documented by ACE-Step.

### 9. Use benchmark categories as review vocabulary
When improving review logic, prefer benchmark-backed categories from:
- VBench / VBench++ / VBench-2.0
- HEIM
- GenEval
- T2I-CompBench++

This means the AI should describe candidate review checks in terms such as:
- faithfulness
- alignment
- composition
- aesthetics
- robustness
- temporal coherence
- motion quality
- continuity
instead of inventing vague new labels.

### 10. Produce repo-local recommendations in 3 buckets
Whenever the AI finishes a research pass, recommendations should be grouped as:
- Safe now: low-risk changes supported by strong official evidence
- Needs experiment: plausible but should be verified with controlled runs
- Unknown / unresolved: upstream evidence is incomplete or conflicting

This prevents overconfident design changes from weak evidence.

## Required output style for future sessions
When the next session analyzes one of these topics, its report should include:
- Official source consulted
- What the source explicitly says
- What the repo currently does
- Confirmed mismatch or confirmed alignment
- Safe next action
- Open uncertainty

## Best immediate use of this addendum
Apply it when reviewing these files:
- `src/ai_mv/styles/citypop/prompting.py`
- `src/ai_mv/core/planning/render_items.py`
- `src/ai_mv/core/planning/routing.py`
- `src/ai_mv/core/stages/render_stills.py`
- `src/ai_mv/core/stages/render_clips.py`
- `src/ai_mv/core/review/quality_signals.py`
- `src/ai_mv/core/review/rerender_policy.py`
- `src/ai_mv/engines/ltx_i2v/mapper.py`
- `src/ai_mv/engines/ltx_ia2v/mapper.py`
- `src/ai_mv/engines/ltx_flf2v/mapper.py`

## Short instruction for another AI session
Load `ai-mv-official-research-sources`, then use this addendum as a hard constraint set. Do not generalize prompt or review behavior from intuition. Verify every major claim against official upstream sources and explicitly separate technical completion from final-MV quality.