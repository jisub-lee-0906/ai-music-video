# Keyframe-Style Still Prompts Implementation Plan

> Historical plan note:
> - This document was written before the current multi-style architecture stabilized.
> - References to `plan_citypop_mv.py`, `test_citypop_stages.py`, and citypop-era naming are historical and not current repo truth.
> - Current canonical references are:
>   - `../README.md`
>   - `../../.hermes/plans/2026-04-15_202152-product-direction-charter.md`
>   - `../../.hermes/plans/2026-04-15_202537-structure-migration-mapping.md`
> - Current planning stage is `src/ai_mv/core/stages/plan_mv.py` and current still-stage tests live under generic/unit planning and stage test files.
>
> **For Hermes:** Treat this file as historical implementation context only, not as the active architecture plan.

**Goal:** Ensure still-image generation consistently asks for a single cinematic keyframe image rather than collage/comic-panel/contact-sheet style multi-image compositions.

**Architecture:** Keep the current 3-stage prompt pipeline (`prompt_seed` → `prompt_draft` → `prompt_polish`) intact, but add a small, explicit single-frame constraint at the still-render boundary and a defensive negative prompt default for Qwen still generation. This is safer than refactoring planning logic because it changes only the still-image generation contract and remains rollbackable.

**Tech Stack:** Python, pytest, existing `ai_mv` stage pipeline, Qwen image workflow config.

---

## Root Cause Summary

Observed facts from the current codebase:
- `src/ai_mv/core/stages/plan_citypop_mv.py` builds only `prompt_seed`, `prompt_draft`, and `prompt_polish`.
- No meaningful project code currently injects explicit `comic panel`, `contact sheet`, or `collage` wording into positive prompts.
- `src/ai_mv/core/stages/render_stills.py` sends `prompt_polish` (fallback: `prompt_draft`, then `prompt_seed`) directly to Qwen still generation.
- Default `render.qwen_negative` is empty in both `src/ai_mv/core/orchestration/config_defaults.py` and `docs/sample-config.yaml`.

Likely failure mode:
- The image model is free to interpret stylized illustration prompts as multi-panel/comic-layout compositions because there is no explicit positive constraint for “single frame / single image keyframe” and no negative constraint blocking panelized layouts.

## Safety / Rollback

Rollback is one-commit reversible if we limit changes to:
- `src/ai_mv/core/stages/render_stills.py`
- `src/ai_mv/core/orchestration/config_defaults.py`
- `docs/sample-config.yaml`
- new/updated tests only

If results worsen, revert just those hunks and the previous prompt flow returns.

---

### Task 1: Lock expected behavior with tests

**Objective:** Add tests proving that still generation prefers single-keyframe language and carries a defensive negative prompt.

**Files:**
- Modify: `tests/unit/test_citypop_stages.py`

**Step 1: Write failing test**
- Add a test for `_still_prompt_text(...)` or the `run_render_stills(...)` call path that asserts the final positive prompt includes a single-image/keyframe constraint.
- Add a test that default config contains a non-empty `qwen_negative` with terms like `comic panel`, `contact sheet`, `collage`, `diptych`, `triptych`, `split screen`.

**Step 2: Run test to verify failure**
Run:
`pytest tests/unit/test_citypop_stages.py -v`

Expected:
- FAIL because the current prompt text does not explicitly require a single keyframe image.
- FAIL because `qwen_negative` is currently empty.

**Step 3: Minimal implementation target**
- Do not change planning-stage prompt semantics yet.
- Only constrain the still-render boundary.

**Step 4: Run tests after implementation**
Run:
`pytest tests/unit/test_citypop_stages.py -v`

Expected:
- PASS.

---

### Task 2: Add a still-render keyframe constraint

**Objective:** Make the final still positive prompt explicitly request a single keyframe-style frame.

**Files:**
- Modify: `src/ai_mv/core/stages/render_stills.py`

**Step 1: Implement minimal prompt wrapper**
- Keep existing prompt priority order.
- Wrap the selected prompt text with a small suffix or normalization helper, for example:
  - `single cinematic keyframe`
  - `single image`
  - `not a collage`
  - `not a comic page`
- Keep this helper still-only so clip prompts remain untouched.

**Step 2: Verification**
Run:
`pytest tests/unit/test_citypop_stages.py::test_render_stills_calls_qwen_runner -v`

Expected:
- PASS, and positive prompt now carries single-keyframe intent.

**Step 3: Guardrails**
- Do not rewrite `prompt_seed`, `prompt_draft`, or `prompt_polish` generation in `plan_citypop_mv.py` unless tests show it is necessary.
- Avoid large prompt-normalization layers.

---

### Task 3: Add a defensive default negative prompt

**Objective:** Prevent the image model from drifting into panelized or collage layouts even when user config omits `qwen_negative`.

**Files:**
- Modify: `src/ai_mv/core/orchestration/config_defaults.py`
- Modify: `docs/sample-config.yaml`

**Step 1: Set a minimal safe default**
Use a concise negative prompt such as:
`comic panel, comic page, manga page, contact sheet, collage, diptych, triptych, split screen, multiple frames, multi-panel layout`

**Step 2: Verification**
Run:
`pytest tests/unit/test_citypop_stages.py -v`

Expected:
- PASS.

**Step 3: Docs sync**
- Mirror the same default in `docs/sample-config.yaml`.

---

### Task 4: Smoke-check prompt output without full render

**Objective:** Verify the actual prompt payload looks correct before spending generation time.

**Files:**
- No code changes required.

**Step 1: Generate or inspect a preview payload**
- Run the existing preview/preflight path that emits `render_plan` and inspect the still prompt actually sent to Qwen.

**Step 2: Validate manually**
Confirm the final still prompt reads like:
- a single keyframe image
- one frame
- cinematic still / illustration
- no collage or panel wording

**Step 3: Optional artifact diff**
Compare before/after prompt text in `artifacts/.../manifest.json` or stage output.

---

### Task 5: Full validation

**Objective:** Confirm no regressions in related prompt/routing behavior.

**Files:**
- No new files required.

**Step 1: Run targeted tests**
Run:
`pytest tests/unit/test_citypop_stages.py tests/unit/test_pipeline.py tests/unit/test_audio_planner_prompt.py -v`

**Step 2: Expected result**
- All targeted tests pass.
- No change to clip routing or render mode selection.

---

## Recommended Minimal Implementation

Prefer this order:
1. Add tests.
2. Add still-only positive constraint helper.
3. Add non-empty `qwen_negative` default.
4. Run targeted tests.
5. Inspect one preview payload before any expensive render.

## Not In Scope

Do not do these in the same change:
- Rework `plan_citypop_mv.py` shot semantics
- Add a large generic prompt-normalization subsystem
- Change clip prompt behavior for i2v/ia2v/flf2v unless still-only fix proves insufficient

## Acceptance Criteria

- Still-image prompts explicitly request a single keyframe-style image.
- Default negative prompt discourages comic/multi-panel/contact-sheet layouts.
- Existing 3-stage prompt pipeline remains intact.
- Targeted tests pass.
- Change is easy to revert.
