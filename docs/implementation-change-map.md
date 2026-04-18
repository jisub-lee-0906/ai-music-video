# Current-State Legacy Change Map

This document replaces the older implementation map that mixed completed work, obsolete plans, and citypop-first assumptions.

Use this file as a live ledger of what legacy still remains.
For canonical product direction, defer to:
- `../.hermes/plans/2026-04-15_202152-product-direction-charter.md`
- `../.hermes/plans/2026-04-15_202537-structure-migration-mapping.md`

## 1. Status legend

- `DONE`
  Legacy already removed or canonicalized.
- `TRANSITIONAL`
  Legacy kept only as a compatibility seam.
- `ACTIVE STYLE PACK`
  Citypop-specific code that is still valid as one style pack, not repo-wide truth.
- `REWRITE NEXT`
  Still inaccurate enough that it should be cleaned up soon.
- `KEEP`
  Still aligned with the current architecture.

## 2. Done: major legacy already cleared

### Canonical stage naming
- `DONE` old canonical planner name `plan_citypop_mv.py`
- `DONE` current canonical stage is `src/ai_mv/core/stages/plan_mv.py`

### Review/report naming cleanup
- `DONE` `citypop_identity` removed from review output surface
- `DONE` `not_kpop_or_cyberpunk` removed from review output surface

### Legacy bootstrap surface
- `DONE` `apply_citypop_defaults` removed

### Legacy profile/example artifacts
- `DONE` `profiles/director_brief_example.yaml` removed

### Canonical payload naming
- `DONE` `style_bible` is now the canonical payload field
- `DONE` `citypop_bible` is no longer canonical

### Obsolete doc path
- `DONE` old `docs/citypop-mv-master-plan.md` path removed
- `DONE` drift-prone archived citypop master-plan copy removed from `docs/` during docs cleanup

## 3. Transitional legacy still present

These are the most obvious remaining legacy seams.
They are not fully removed yet.

### `citypop_bible` compatibility paths
Status: `TRANSITIONAL`

Current locations:
- `src/ai_mv/core/orchestration/input_gate.py`
- `src/ai_mv/core/orchestration/stage_runs.py`
- `src/ai_mv/core/artifacts/manifest.py`
- related compatibility tests under `tests/unit/`

Why still present:
- protects older payloads while the canonical field is now `style_bible`

Target direction:
- remove backfill/normalization once no caller depends on the alias
- then delete compatibility tests that exist only for this seam

### Compatibility-focused tests
Status: `TRANSITIONAL`

Examples:
- `tests/unit/test_stage_payloads_generic_style.py`
- `tests/unit/test_legacy_alias_compatibility.py`

Why still present:
- they prove the remaining alias seams are intentional and bounded

Target direction:
- delete them when the underlying compatibility seams are deleted

## 4. Active style-pack code, not repo-wide truth

These are citypop-heavy surfaces, but they are not automatically wrong.
They are acceptable as long as they remain style-pack scoped.

### Citypop style pack
Status: `ACTIVE STYLE PACK`

Files:
- `src/ai_mv/styles/citypop/bible.py`
- `src/ai_mv/styles/citypop/prompting.py`
- `src/ai_mv/styles/citypop/rules.py`

Why they stay:
- citypop is still a supported style pack
- the problem was citypop leaking into core truth, not citypop existing at all

### Style resolution and fallbacks
Status: `REWRITE NEXT`

Primary file:
- `src/ai_mv/styles/resolver.py`

Why it still needs attention:
- current fallback/default behavior is still citypop-weighted
- multi-style direction would be cleaner if defaults and fallback policy become more explicit and less citypop-first

### Example/test content using citypop prompts
Status: `ACTIVE STYLE PACK`

Examples:
- `tests/unit/test_style_citypop_pack.py`
- `tests/unit/test_style_resolver.py`
- some citypop-oriented example strings in docs and tests

Interpretation rule:
- acceptable as style-pack coverage
- not acceptable as universal product definition

## 5. Docs that still needed truth-sync

### `docs/repo-restructure.md`
Status before this cycle: `REWRITE NEXT`
Status after this cycle: `DONE`

What changed:
- removed obsolete claims that `plan_citypop_mv.py` and `citypop_bible` are still the target canonical architecture
- rewrote the file around the actual current pipeline and remaining seams

### `docs/implementation-change-map.md`
Status before this cycle: `REWRITE NEXT`
Status after this cycle: `DONE`

What changed:
- replaced obsolete future-plan language with a current-state legacy ledger

### Historical plans formerly under `docs/plans/`
Status: `DONE`

What changed:
- removed from `docs/` to reduce confusion and stop historical implementation notes from acting like active product truth
- any future rationale worth keeping should be rewritten into current-state docs instead of restored as raw historical plans

## 6. Keep: current architecture that matches repo direction

### Current stages
Status: `KEEP`

Canonical current stage files:
- `src/ai_mv/core/stages/acestep_music.py`
- `src/ai_mv/core/stages/plan_mv.py`
- `src/ai_mv/core/stages/render_stills.py`
- `src/ai_mv/core/stages/render_clips.py`
- `src/ai_mv/core/stages/assemble_mv.py`
- `src/ai_mv/core/stages/review_outputs.py`

### Extracted planning subsystem
Status: `KEEP`

Files:
- `src/ai_mv/core/planning/sections.py`
- `src/ai_mv/core/planning/routing.py`
- `src/ai_mv/core/planning/shot_plan.py`
- `src/ai_mv/core/planning/render_items.py`

### Extracted review subsystem
Status: `KEEP`

Files:
- `src/ai_mv/core/review/policy.py`
- `src/ai_mv/core/review/rerender_policy.py`
- `src/ai_mv/core/review/quality_signals.py`
- `src/ai_mv/core/review/benchmark_dimensions.py`
- `src/ai_mv/core/review/signal_buckets.py`
- `src/ai_mv/core/review/publishability.py`
- `src/ai_mv/core/review/models.py`

## 7. Highest-priority remaining cleanup targets

1. delete `citypop_bible` compatibility normalization once safe
2. make style fallback policy less citypop-first in `styles/resolver.py`
3. audit historical plan docs and either archive or truth-label them more aggressively
4. continue improving review/rerender quality gates toward the actual success metric: publishable final MV quality

## 8. Bottom line

No, legacy is not fully gone yet.

But the remaining legacy is now much narrower than before:
- mostly compatibility seams
- style-pack-local citypop logic
- historical docs and examples

The largest remaining risk is no longer old core wrappers.
The largest remaining risk is leaving transitional compatibility and historical documentation around long enough that they start acting like product truth again.