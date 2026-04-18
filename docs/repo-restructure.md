# Repository Restructure Status

This document is a truth-synced replacement for the older restructure plan.
It describes the architecture that now exists in the repository, the legacy seams that still remain, and the next cleanup priorities.

## 1. Product and architecture baseline

Canonical product direction lives in:
- `../.hermes/plans/2026-04-15_202152-product-direction-charter.md`
- `../.hermes/plans/2026-04-15_202537-structure-migration-mapping.md`

This repo is now aligned to:
- concept-text-first UX
- multi-style MV generation
- mandatory music generation
- final-MV quality as the main success metric
- ComfyUI/workflow-backed rendering
- review/rerender loops instead of one-shot output claims

## 2. Current high-level pipeline

The current pipeline is:
1. `audio`
2. `plan`
3. `stills`
4. `clips`
5. `assemble`
6. `review`

Current stage files under `src/ai_mv/core/stages/`:
- `acestep_music.py`
- `plan_mv.py`
- `render_stills.py`
- `render_clips.py`
- `assemble_mv.py`
- `review_outputs.py`

Compatibility helpers also exist:
- `ffmpeg_muxer.py`
- `payload_views.py`
- `review_stage.py`

Important correction:
- `plan_citypop_mv.py` is no longer the target or canonical stage name.
- The canonical planning entrypoint is now `plan_mv.py`.

## 3. Current domain structure

### Shared planning layer
Current extracted planning modules under `src/ai_mv/core/planning/`:
- `sections.py`
- `routing.py`
- `shot_plan.py`
- `render_items.py`

These hold the style-neutral planning and render-item assembly logic that used to be mixed into larger stage files.

### Review subsystem
Current extracted review modules under `src/ai_mv/core/review/`:
- `policy.py`
- `rerender_policy.py`
- `quality_signals.py`
- `benchmark_dimensions.py`
- `signal_buckets.py`
- `publishability.py`
- `models.py`

The review report now contains:
- raw blocking/non-blocking checks
- rerender targets and reasons
- benchmark-dimension summaries
- evidence-type signal buckets
- publishability summary split into technical completion / isolated asset quality / final MV publishability

### Style layer
Current style packs under `src/ai_mv/styles/`:
- `citypop/`
- `synthwave/`
- `resolver.py`

This is a major shift from the older docs: style-specific assumptions are no longer supposed to live directly in `core`.

## 4. Current canonical payload concepts

The active payload/report surface is centered on keys such as:
- `concept_text`
- `style_name`
- `style_bible`
- `music_plan`
- `music_map`
- `shot_plan`
- `render_plan`
- `still_results`
- `clip_results`
- `final_video`
- `review_report`

Important correction:
- `style_bible` is the canonical field.
- `citypop_bible` still appears only as a transitional compatibility seam in some normalization paths and tests.

## 5. Remaining legacy seams

No, legacy has not been fully removed yet.

The main remaining legacy categories are:

### A. Transitional compatibility seams
These are still present intentionally but should eventually disappear:
- `citypop_bible` backfill/normalization in orchestration and manifest code
- tests that explicitly verify legacy alias compatibility

Examples:
- `src/ai_mv/core/orchestration/input_gate.py`
- `src/ai_mv/core/orchestration/stage_runs.py`
- `src/ai_mv/core/artifacts/manifest.py`
- `tests/unit/test_stage_payloads_generic_style.py`
- `tests/unit/test_legacy_alias_compatibility.py`

### B. Style-pack-specific code that is still real, not accidental legacy
These are not necessarily bugs, but they are still citypop-weighted implementation surfaces:
- `src/ai_mv/styles/citypop/*`
- `src/ai_mv/styles/resolver.py` default/fallback behavior
- citypop-oriented examples and tests

This is acceptable as long as:
- core stays style-neutral
- citypop remains one style pack, not repo-wide truth

### C. Historical docs that were pruned
The repo previously carried drift-prone historical docs under `docs/plans/` and `docs/archived/`.
Those have now been removed from `docs/` so they stop competing with canonical product truth.

## 6. What has already been removed

These older legacy items have already been removed or demoted from canonical status:
- `plan_citypop_mv.py` as the canonical planner stage
- `apply_citypop_defaults`
- legacy review aliases such as `citypop_identity` and `not_kpop_or_cyberpunk`
- `profiles/director_brief_example.yaml`
- obsolete `docs/citypop-mv-master-plan.md` path and its drift-prone archived copy under `docs/` removed
- canonical payload use of `citypop_bible` in favor of `style_bible`

## 7. Next cleanup priorities

Recommended next legacy-removal order:
1. remove `citypop_bible` transitional compatibility seams once no caller depends on them
2. reduce `styles/resolver.py` citypop-first fallback assumptions where possible
3. keep improving publishability-oriented review, because technical cleanup alone does not reach the success metric

## 8. Practical rule for future edits

When a file or doc disagrees with the charter, prefer:
1. charter
2. structure migration mapping
3. current README and current code
4. historical docs only as reference

If a doc still describes citypop-only behavior, old stage names, or removed artifacts as current truth, it should be rewritten or explicitly marked historical.