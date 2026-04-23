# AI MV Final 7 Percent Implementation Plan

> **For Hermes:** Use subagent-driven-development skill to implement this plan task-by-task.

**Goal:** Move ai-music-video from structurally solid / rhythm-aware assembly to output-level MV differentiation and publishability.

**Architecture:** Keep the current IA2V-only video canon and Flux2 still canon intact. Add the remaining value in four product-facing layers: stronger section-dependent edit behavior, stronger review signals against safe/repetitive edits, direct mapping from review failures into executable assembly revisions, and final-run visual validation against real outputs.

**Tech Stack:** Python, pytest, ffmpeg/comfy-backed pipeline, current ai_mv review/publishability/rerender stack.

---

## Remaining work summary

1. Aggressive edit-pattern branching
2. Review-time anti-safe / anti-repetition scoring
3. Assembly-revision execution that changes actual edit behavior, not only metadata
4. Real-run visual validation loop

## Priority order

### Slice 1 — Aggressive section-role cut pattern branching

**Objective:** Make chorus / verse / bridge / release materially diverge in actual cut behavior rather than only metadata labels.

**Files:**
- Modify: `src/ai_mv/core/planning/render_items.py`
- Modify: `src/ai_mv/core/stages/assemble_mv.py`
- Test: `tests/unit/test_stage_entrypoints.py`
- Test: `tests/unit/test_planning_render_items.py`

**Definition of done:**
- `edit_intent` gains real pattern-family variation within the same high-level role
- chorus behavior no longer just means “center + bar snap”; it chooses among multiple denser edit families
- verse/support behavior no longer defaults to one safe hold pattern
- tests prove actual trim/cadence divergence across section roles and pattern families

**Acceptance target:**
- Two chorus shots with different local conditions should be able to produce meaningfully different trim behavior
- Support/verse should not collapse into one repeated `cut_in/cut_out + beat snap + hold` pattern

---

### Slice 2 — Review-time anti-safe / anti-repetition scoring

**Objective:** Penalize outputs that are structurally correct but too similar, too flat, or too safe.

**Files:**
- Modify: `src/ai_mv/core/review/models.py`
- Modify: `src/ai_mv/core/review/publishability.py`
- Test: `tests/unit/test_review_subsystem.py`

**Definition of done:**
- review uses new assembly cadence metadata (`cadence_profile`, `snap_unit`, `trimmed_coverage_sec`) directly
- add explicit signals for repetition / over-safety / weak chorus payoff
- publishability can fail for “technically okay but editorially bland” cases

**Acceptance target:**
- review should distinguish:
  - rhythm-aware but repetitive
  - rhythm-aware and section-differentiated
- publishability should stop over-rewarding safe uniform edits

---

### Slice 3 — Assembly revision actions must change real behavior

**Objective:** Ensure assembly-first actions such as transition revision or chorus weighting revision actually alter assembly decisions instead of only producing reports.

**Files:**
- Modify: `src/ai_mv/core/stages/prepare_rerender.py`
- Modify: `src/ai_mv/core/stages/execute_rerender.py`
- Modify: `src/ai_mv/core/stages/rerender_review.py`
- Modify: `src/ai_mv/core/stages/assemble_mv.py`
- Test: `tests/unit/test_stage_entrypoints.py`
- Test: `tests/unit/test_review_subsystem.py`

**Definition of done:**
- assembly revision actions mutate real assembly parameters or decision branches
- rerender review can report whether the assembly revision improved the targeted issue
- “revise assembly weights” and “revise transition selection” are no longer mostly advisory

**Acceptance target:**
- assembly-first rerender path must produce different assembly metadata and different trim/transition outcomes from the baseline

---

### Slice 4 — Real-run visual validation loop

**Objective:** Close the gap between code-level confidence and actual publishable MV quality.

**Files:**
- Modify as needed after inspection: `src/ai_mv/core/stages/review_outputs.py`, `src/ai_mv/core/stages/rerender_escalation.py`, `src/ai_mv/analysis/*`
- Test: targeted unit tests for any new report payloads
- Artifact/ops: generate frame extracts / review packets from a real run

**Definition of done:**
- evaluate at least one real non-smoke run’s final video, extracted final frames, and representative clip frames
- confirm whether remaining issues are editorial repetition, continuity, insufficient chorus payoff, or model/render quality
- turn the findings into the next concrete engineering slice instead of guessing from structure alone

**Acceptance target:**
- final roadmap becomes evidence-based rather than code-only inference

---

## Conservative completion estimate

- **Structure / architecture:** 100%
- **Actual product completion:** 93%

## What the remaining 7% really is

This is not missing plumbing anymore. The remaining gap is mainly:
- stronger editorial differentiation
- less safe convergence
- clearer chorus payoff
- better review rejection of bland-but-valid output
- confirmation on real final video artifacts

## Recommended next execution order

1. Slice 1 — aggressive section-role cut pattern branching
2. Slice 2 — anti-safe / anti-repetition review scoring
3. Slice 3 — executable assembly revision behavior
4. Slice 4 — real-run visual validation

## Verification commands

```bash
source .venv/bin/activate
pytest tests/unit/test_planning_render_items.py tests/unit/test_stage_entrypoints.py -q
pytest tests/unit/test_review_subsystem.py -q
pytest -q
```

## Notes

- Do not reintroduce legacy video workflow policy.
- Keep current workflow JSONs immutable defaults.
- Prefer changes that materially alter output behavior, not naming-only cleanup.
- The next best slice is Slice 1, because that is the highest-leverage fix for the user’s “too safe / too similar” concern.
