# AI MV Official Research Handoff

> For the next Hermes session: load the skill `ai-mv-official-research-sources` first. Use only official docs, official model cards, official repos, author technical reports, and benchmark papers.

## Why this handoff exists

The repo needs better grounding for:
- workflow-specific prompting
- ComfyUI binding realism
- i2v / ia2v / flf2v behavior
- review / rerender evaluation criteria
- music-generation reality checks

A reusable skill has already been created:
- `ai-mv-official-research-sources`

That skill now includes:
- ComfyUI official docs
- LTX-Video official model card / GitHub / ComfyUI integration repo / paper
- Qwen-Image official model card / GitHub / technical report
- ACE-Step official model card / GitHub / paper
- HEIM
- GenEval
- T2I-CompBench++
- VBench
- VBench++
- VBench-2.0
- FVD reference paper
- TRIP
- Versatile Transition Generation with Image-to-Video Diffusion
- Diffusers evaluation docs

## Immediate investigation priority

### 1. LTX ComfyUI upstream reality check
Read first:
- `https://github.com/Lightricks/ComfyUI-LTXVideo`
- `https://huggingface.co/Lightricks/LTX-Video`
- arXiv `2501.00103` (`LTX-Video: Realtime Video Latent Diffusion`)

Goal:
- compare this repo's local workflow JSON assumptions and mapper bindings against official upstream ComfyUI workflows
- identify whether `i2v`, `ia2v`, and `flf2v` inputs in `src/ai_mv/engines/ltx_*` match upstream-supported structure

Repo files to inspect:
- `src/ai_mv/engines/ltx_i2v/mapper.py`
- `src/ai_mv/engines/ltx_ia2v/mapper.py`
- `src/ai_mv/engines/ltx_flf2v/mapper.py`
- `docs/workflow-usage.md`
- local workflow JSONs under `workflows/`

### 2. Qwen still prompt contract
Read first:
- `https://huggingface.co/Qwen/Qwen-Image`
- `https://github.com/QwenLM/Qwen-Image`
- arXiv `2508.02324` (`Qwen-Image Technical Report`)

Goal:
- determine what the official still model is best at
- decide whether current still prompts are too illustration-centric and not motion-safe enough for downstream video generation

Repo files to inspect:
- `src/ai_mv/styles/citypop/prompting.py`
- `src/ai_mv/core/planning/render_items.py`
- `src/ai_mv/core/stages/render_stills.py`

### 3. i2v-specific motion failure study
Read first:
- arXiv `2501.00103` (`LTX-Video`)
- arXiv `2403.17005` (`TRIP: Temporal Residual Learning with Image Noise Prior for Image-to-Video Diffusion Models`)

Goal:
- identify what kinds of stills and prompts cause image-to-video instability
- derive practical repo rules for what counts as an i2v-safe shot versus a shot that needs another workflow

Repo files to inspect:
- `src/ai_mv/core/planning/shot_plan.py`
- `src/ai_mv/core/planning/routing.py`
- `src/ai_mv/styles/citypop/rules.py`
- `src/ai_mv/styles/citypop/prompting.py`

### 4. flf2v / bridge transition investigation
Read first:
- arXiv `2508.01698` (`Versatile Transition Generation with Image-to-Video Diffusion`)
- `https://github.com/Lightricks/ComfyUI-LTXVideo`

Goal:
- determine whether bridge prompts should be short transition instructions instead of generic scene prompts
- define compatibility rules for first/last frame pairing

Repo files to inspect:
- `src/ai_mv/core/planning/routing.py`
- `src/ai_mv/core/planning/render_items.py`
- `src/ai_mv/core/stages/render_clips.py`
- `docs/m3-flf2v-spec.md`

### 5. review criteria upgrade
Read first:
- arXiv `2311.17982` (`VBench`)
- arXiv `2411.13503` (`VBench++`)
- arXiv `2503.21755` (`VBench-2.0`)
- arXiv `1812.01717` (`Towards Accurate Generative Models of Video: A New Metric & Challenges`)
- `https://huggingface.co/docs/diffusers/en/conceptual/evaluation`
- arXiv `2311.04287` (`HEIM`)

Goal:
- replace placeholder review checks with benchmark-grounded categories
- separate technical completeness from MV quality and rerender reasoning

Repo files to inspect:
- `src/ai_mv/core/review/quality_signals.py`
- `src/ai_mv/core/review/models.py`
- `src/ai_mv/core/review/rerender_policy.py`
- `src/ai_mv/core/stages/review_outputs.py`

### 6. still evaluation criteria expansion
Read first:
- arXiv `2311.04287` (`HEIM`)
- arXiv `2310.11513` (`GenEval`)
- arXiv `2307.06350` (`T2I-CompBench++`)

Goal:
- expand still review beyond “looks good” into alignment, composition, robustness, and broader deployment concerns

Repo files to inspect:
- `src/ai_mv/styles/citypop/prompting.py`
- `src/ai_mv/core/planning/render_items.py`
- any future still-review logic under `src/ai_mv/core/review/`

### 7. music-generation limits and guardrails
Read first:
- `https://huggingface.co/ACE-Step/ACE-Step-v1-3.5B`
- `https://github.com/ACE-Step/ACE-Step`
- arXiv `2506.00045` (`ACE-Step: A Step Towards Music Generation Foundation Model`)

Goal:
- align internal audio planning expectations with the model’s official limits
- avoid overclaiming control, coherence, style adherence, or vocal quality

Repo files to inspect:
- `src/ai_mv/engines/acestep_1_5_aio/planner.py`
- `src/ai_mv/engines/acestep_1_5_aio/prompting.py`
- `tests/unit/test_audio_planner_prompt.py`

## Most valuable 3 if time is short
1. `ComfyUI-LTXVideo`
2. `Qwen-Image` technical report + official repo
3. `VBench`

Why:
- these three most directly affect workflow binding accuracy, still/clip prompt separation, and review design

## Guardrails for the next session
- Do not rely on community anecdotes when official sources exist.
- Do not redesign prompt contracts without checking official model behavior first.
- Do not redesign review based only on aesthetic intuition; map review categories to benchmark concepts where possible.
- Treat `review_status=done` in the current repo as technical completeness, not proof of MV quality.

## Suggested next deliverable
Produce a short gap report with these sections:
- official-source findings
- repo mismatches
- safe immediate fixes
- later research questions
