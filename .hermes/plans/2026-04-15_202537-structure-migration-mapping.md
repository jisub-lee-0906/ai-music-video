# ai-mv Structure Migration Mapping

> **For Hermes:** Use subagent-driven-development skill to implement this plan task-by-task.

**Goal:** Map the current repository file-by-file into a target architecture aligned with the new charter: multi-style, concept-text-first, final-MV-first, strong ComfyUI dependence, strict review/rerender loop, and aggressive legacy deletion.

**Architecture:** Keep the current execution backbone (`cli` → `entrypoints` → `core/orchestration` → `engines`/`infra`) where it still matches the charter, but remove legacy UX paths, extract style-specific logic from shared layers, and promote review/rerender into a dedicated `core/review` domain. The mapping below is intentionally opinionated: every file should be either kept, moved, generalized, merged, or deleted.

**Tech Stack:** Python 3.11+, ComfyUI workflows, ffmpeg/ffprobe, Codex/LLM-assisted review, pytest

---

## 1. Target Architecture Snapshot

Recommended target tree:

```text
src/ai_mv/
  cli/
  entrypoints/
  core/
    orchestration/
    contracts/
    review/
    artifacts/
    state/
    planning/
  styles/
    citypop/
    ...future styles...
  engines/
    audio_gen/
    qwen_image/
    ltx_i2v/
    ltx_ia2v/
    ltx_flf2v/
  infra/
  utils/
```

High-level rule set:
- `core` must be style-neutral.
- `styles` owns style-specific prompts, motifs, defaults, planning hints.
- `core/review` becomes a first-class subsystem.
- external UX must converge on `concept_text` only.
- legacy/public compatibility paths are removed rather than preserved.

---

## 2. Decision Legend

- KEEP: structure is fundamentally aligned; minor cleanup only
- REFACTOR-IN-PLACE: keep path for now but significantly rewrite internals
- MOVE: relocate to a better package/domain
- SPLIT: break a large file into multiple modules
- MERGE: consolidate into fewer files
- DELETE: remove completely
- DEPRECATE-BRIEFLY: short transition only if needed to reduce risk

---

## 3. File-by-File Mapping

### 3.1 Root / packaging / metadata

| Current file | Decision | Target path | Reason |
|---|---|---|---|
| `pyproject.toml` | REFACTOR-IN-PLACE | same | Keep package metadata and CLI entrypoint, but update description away from citypop-only wording and ensure dependency strategy reflects LLM/review direction. |
| `README.md` | REFACTOR-IN-PLACE | same | Rewrite to match canonical product: multi-style, `concept_text`-first, final MV first, no `profile`/`--brief`. |
| `profiles/director_brief_example.yaml` | DELETE | none | Conflicts directly with the new single-input contract and aggressive legacy removal policy. |
| `uv.lock` | KEEP | same | Package lockfile is orthogonal to architecture. |

### 3.2 Docs

| Current file | Decision | Target path | Reason |
|---|---|---|---|
| `docs/README.md` | REFACTOR-IN-PLACE | same | Must stop describing the repo as a citypop-only rebuild and instead index new product docs. |
| `docs/citypop-mv-master-plan.md` | MOVE | `docs/archived/citypop-mv-master-plan.md` or convert into `styles/citypop/README.md` | Citypop remains useful as a style pack reference, not as repository-wide product truth. |
| `docs/repo-restructure.md` | REFACTOR-IN-PLACE | maybe `docs/architecture/target-structure.md` | Good raw material, but it assumes citypop as universal truth. Rewrite around style-neutral core. |
| `docs/legacy-deletion-plan.md` | REFACTOR-IN-PLACE | same or `docs/architecture/legacy-removal.md` | Still highly relevant; align with actual delete list from this mapping. |
| `docs/workflow-usage.md` | KEEP | same | Workflow usage stays central because ComfyUI dependence remains strong. Generalize style assumptions if needed. |
| `docs/workflow-binding-notes.md` | KEEP | same | Mapper/workflow contract documentation is still valuable. |
| `docs/m1-implementation-spec.md` | REFACTOR-IN-PLACE | maybe `docs/archived/m1-citypop-spec.md` or rewrite as generic MVP spec | Useful, but current framing is too tied to citypop-first rebuild. |
| `docs/m2-ia2v-spec.md` | KEEP | same | Routing spec still relevant if generalized out of citypop assumptions. |
| `docs/m3-flf2v-spec.md` | KEEP | same | Same as above. |
| `docs/implementation-change-map.md` | REFACTOR-IN-PLACE | same or archive | Update with the new charter and this mapping. |
| `docs/first-run-checklist.md` | KEEP | same | Runtime/operator checklist remains useful. |
| `docs/sample-config.yaml` | DELETE or archive | none or `docs/archived/` | If the external UX is truly `concept_text` only, public config examples should not be first-class. Keep only as internal/dev reference if needed. |
| `docs/plans/*.md` | KEEP | same | Historical plans are useful context but should not define canonical architecture. |

### 3.3 CLI layer

| Current file | Decision | Target path | Reason |
|---|---|---|---|
| `src/ai_mv/cli/app.py` | KEEP | same | Thin entrypoint is appropriate. |
| `src/ai_mv/cli/args.py` | REFACTOR-IN-PLACE | same | Remove `--brief`, `--audio-brief`, `--audio-hook-brief` as public contract; keep `--concept-text` and maybe only minimal internal dev flags. |
| `src/ai_mv/cli/commands.py` | REFACTOR-IN-PLACE | same | Remove `legacy_brief` path and collapse command dispatch to canonical arguments. |
| `src/ai_mv/cli/__init__.py` | KEEP | same | No issue. |

### 3.4 Entrypoints

| Current file | Decision | Target path | Reason |
|---|---|---|---|
| `src/ai_mv/entrypoints/start.py` | REFACTOR-IN-PLACE | same | Keep overall orchestration role, but collapse input loading to `concept_text` only and remove brief-writing branches. |
| `src/ai_mv/entrypoints/preflight.py` | REFACTOR-IN-PLACE | same | Same as `start.py`; preflight remains useful. |
| `src/ai_mv/entrypoints/doctor.py` | KEEP | same | Strongly aligned with WSL/Comfy/runtime operability goals. |
| `src/ai_mv/entrypoints/status.py` | KEEP | same | Status reporting remains useful for long-running media jobs. |

### 3.5 Core orchestration

| Current file | Decision | Target path | Reason |
|---|---|---|---|
| `src/ai_mv/core/orchestration/pipeline.py` | REFACTOR-IN-PLACE | same | Keep as the canonical stage sequencer, but update stage naming/responsibility to emphasize review/rerender loop and style-neutral planning. |
| `src/ai_mv/core/orchestration/preflight.py` | KEEP | same | Useful as pre-run validation entry for workflow-heavy pipeline. |
| `src/ai_mv/core/orchestration/config_defaults.py` | REFACTOR-IN-PLACE | same | Remove profile/brief assumptions; convert defaults to match concept-text-first and multi-style architecture. |
| `src/ai_mv/core/orchestration/bootstrap_guard.py` | REFACTOR-IN-PLACE | same | Validate generic style/runtime assumptions, not citypop-only defaults. |
| `src/ai_mv/core/orchestration/input_gate.py` | KEEP | same | Input validation remains important; rewrite around canonical payload contract. |
| `src/ai_mv/core/orchestration/stage_runs.py` | KEEP | same | Structural helper still fits. |
| `src/ai_mv/core/orchestration/transitions.py` | KEEP | same | Likely still relevant if transitions remain generic stage state logic. |
| `src/ai_mv/core/orchestration/scheduler.py` | KEEP or MERGE | same or merge into rerender subsystem | Depends on actual usage; may become more valuable if rerender loops become richer. |
| `src/ai_mv/core/orchestration/wsl_overrides.py` | KEEP | same | Still consistent with strong WSL/Windows ComfyUI support. |

### 3.6 Core stages

| Current file | Decision | Target path | Reason |
|---|---|---|---|
| `src/ai_mv/core/stages/acestep_music.py` | REFACTOR-IN-PLACE | maybe rename later to `music_generation.py` | Music generation is mandatory, so this stays important; however it should be engine-neutral at stage level. |
| `src/ai_mv/core/stages/plan_citypop_mv.py` | SPLIT + MOVE | `src/ai_mv/core/planning/*` + `src/ai_mv/styles/citypop/*` | This is the most obvious architectural mismatch. Core planning must become style-neutral; citypop-specific worldview moves to style pack. |
| `src/ai_mv/core/stages/render_stills.py` | REFACTOR-IN-PLACE | same | Keep role, but remove citypop assumptions from prompt assembly and let styles feed prompt context. |
| `src/ai_mv/core/stages/render_clips.py` | REFACTOR-IN-PLACE | same | Keep orchestration role; tighten routing contracts and review feedback integration. |
| `src/ai_mv/core/stages/assemble_mv.py` | KEEP / REFACTOR-IN-PLACE | same | Still aligned; likely needs richer artifact metadata for final-quality-focused pipeline. |
| `src/ai_mv/core/stages/review_outputs.py` | MOVE + SPLIT | `src/ai_mv/core/review/review_stage.py`, `review_models.py`, `rerender_policy.py`, `quality_signals.py` | Review is too important to remain a thin stage file. Promote to dedicated subsystem. |
| `src/ai_mv/core/stages/ffmpeg_muxer.py` | MOVE | `src/ai_mv/engines/ffmpeg_mux/` or keep under `core/stages` if purely stage-local | If it is workflow-engine-like, it belongs with engine adapters rather than stage wrappers. |
| `src/ai_mv/core/stages/payload_views.py` | KEEP or MOVE | maybe `core/contracts/payload_builders.py` | Useful helper, but possibly better placed near contracts. |

### 3.7 Core contracts and planning

| Current file | Decision | Target path | Reason |
|---|---|---|---|
| `src/ai_mv/core/contracts/stage_io.py` | KEEP | same | Fundamental contract definition. |
| `src/ai_mv/core/contracts/errors.py` | KEEP | same | Shared error contracts stay useful. |
| `src/ai_mv/core/contracts/intent_models.py` | KEEP / REFACTOR-IN-PLACE | same | Good place for concept/style interpretation contracts. |
| `src/ai_mv/core/contracts/visual_plan_schema.py` | KEEP / REFACTOR-IN-PLACE | same | Still relevant, but should become style-neutral and final-output-oriented. |
| `src/ai_mv/core/contracts/visual_plan_normalize.py` | KEEP / REFACTOR-IN-PLACE | same | Same as above. |
| `src/ai_mv/core/contracts/prompt_schema.py` | KEEP | same | Important if LLM outputs remain schema-bounded. |
| `src/ai_mv/core/contracts/prompt_normalize.py` | SPLIT | `core/contracts/prompt_normalize.py` + smaller helpers or `core/planning/prompting/*` | 643-line size suggests contract and business logic are overly entangled. |
| `src/ai_mv/core/prompt_digests.py` | MOVE | `src/ai_mv/core/planning/prompt_digests.py` or `styles/common/` | Better grouped with planning/prompt helpers rather than top-level `core`. |
| `src/ai_mv/core/workflow_names.py` | KEEP / REFACTOR-IN-PLACE | same | Still important because workflow dependence remains strong. |
| `src/ai_mv/core/output_paths.py` | KEEP | same | Central artifact naming still makes sense. |

### 3.8 Core review / state / artifacts

| Current file | Decision | Target path | Reason |
|---|---|---|---|
| `src/ai_mv/core/state/state_store.py` | KEEP | same | Strong alignment with pipeline/runtime needs. |
| `src/ai_mv/core/state/state_models.py` | KEEP / REFACTOR-IN-PLACE | same | Useful if expanded to support review/rerender lifecycle richer states. |
| `src/ai_mv/core/state/state_snapshot.py` | KEEP | same | Snapshotting remains valuable. |
| `src/ai_mv/core/artifacts/paths.py` | KEEP | same | Aligned. |
| `src/ai_mv/core/artifacts/manifest.py` | REFACTOR-IN-PLACE | same | Expand to capture richer review/rerender/final quality context. |
| `src/ai_mv/core/artifacts/run_summary.py` | REFACTOR-IN-PLACE | same | Final-output-centric summary should become more meaningful. |
| `src/ai_mv/core/artifacts/publish.py` | KEEP / REFACTOR-IN-PLACE | same | Publishing artifacts remains core. |

### 3.9 Engines

| Current file | Decision | Target path | Reason |
|---|---|---|---|
| `src/ai_mv/engines/acestep_1_5_aio/*` | REFACTOR-IN-PLACE + possible rename | `src/ai_mv/engines/audio_gen/*` or keep current package until stable | Music generation is central, but package name is implementation-specific. Consider renaming when architecture stabilizes. |
| `src/ai_mv/engines/acestep_1_5_aio/planner.py` | SPLIT | same package or `engines/audio_gen/*` | 1000+ lines is too large; split into input normalization, lyric planning, timing policy, prompt building. |
| `src/ai_mv/engines/acestep_1_5_aio/policy.py` | KEEP / SPLIT | same | Probably still useful, but may be overly large. |
| `src/ai_mv/engines/acestep_1_5_aio/mapper.py` | KEEP | same | Workflow mapping is still core. |
| `src/ai_mv/engines/acestep_1_5_aio/runner.py` | KEEP | same | Core engine wrapper. |
| `src/ai_mv/engines/acestep_1_5_aio/prompting.py` | KEEP / MOVE | same or planning submodule | Depends on whether it's engine prompt assembly vs product planning logic. |
| `src/ai_mv/engines/acestep_1_5_aio/lyric_blocks.py` | KEEP | same | Domain helper for audio generation. |
| `src/ai_mv/engines/qwen_image/*` | KEEP | same | Strongly aligned with workflow-based still generation. |
| `src/ai_mv/engines/ltx_i2v/*` | KEEP | same | Aligned. |
| `src/ai_mv/engines/ltx_ia2v/*` | KEEP | same | Aligned. |
| `src/ai_mv/engines/ltx_flf2v/*` | KEEP | same | Aligned. |
| `src/ai_mv/engines/common/clip_timing.py` | KEEP | same | Generic helper likely still valid. |
| `src/ai_mv/engines/__init__.py` | KEEP | same | No issue. |

### 3.10 Infra

| Current file | Decision | Target path | Reason |
|---|---|---|---|
| `src/ai_mv/infra/comfy_client.py` | KEEP | same | Central integration point. |
| `src/ai_mv/infra/comfy_transport.py` | KEEP | same | Aligned with strong workflow realism. |
| `src/ai_mv/infra/comfy_local.py` | KEEP | same | Useful local execution helper. |
| `src/ai_mv/infra/comfy_outputs.py` | KEEP | same | Output harvesting remains relevant. |
| `src/ai_mv/infra/workflow_patcher.py` | KEEP / REFACTOR-IN-PLACE | same | Good fit if workflow binding remains explicit. |
| `src/ai_mv/infra/doctor_checks.py` | KEEP / REFACTOR-IN-PLACE | same | Needs stronger product-aware checks, but role remains right. |
| `src/ai_mv/infra/single_flight_lock.py` | KEEP | same | Useful guard for long media jobs. |
| `src/ai_mv/infra/timeout_policy.py` | KEEP | same | Useful infra concern. |
| `src/ai_mv/infra/codex_cli_client.py` | KEEP / REFACTOR-IN-PLACE | same | LLM role is expanding, not shrinking. Strengthen contracts and test isolation rather than delete it. |

### 3.11 Utils and observability

| Current file | Decision | Target path | Reason |
|---|---|---|---|
| `src/ai_mv/utils/audio_timing.py` | KEEP | same | Pure helper. |
| `src/ai_mv/utils/text_utils.py` | KEEP | same | Pure helper. |
| `src/ai_mv/utils/bool_utils.py` | KEEP | same | Pure helper. |
| `src/ai_mv/utils/path_utils.py` | KEEP | same | Pure helper. |
| `src/ai_mv/utils/project_root.py` | KEEP | same | Environment helper. |
| `src/ai_mv/utils/json_utils.py` | KEEP | same | Pure helper. |
| `src/ai_mv/utils/time_utils.py` | KEEP | same | Useful helper incl. ffprobe utilities. |
| `src/ai_mv/observability/tracing.py` | KEEP / REFACTOR-IN-PLACE | same | Observability will become more important as rerender loops deepen. |

---

## 4. New Modules to Add

### Must add soon

| Create | Why |
|---|---|
| `src/ai_mv/styles/__init__.py` | Introduce explicit style layer. |
| `src/ai_mv/styles/citypop/__init__.py` | Preserve current citypop expertise without keeping it in `core`. |
| `src/ai_mv/styles/citypop/bible.py` | Relocate current citypop worldview/constants. |
| `src/ai_mv/styles/citypop/prompting.py` | Relocate citypop-specific prompt seed helpers. |
| `src/ai_mv/core/review/review_stage.py` | First-class review orchestration. |
| `src/ai_mv/core/review/review_models.py` | Review contract schemas/scores/reasons. |
| `src/ai_mv/core/review/rerender_policy.py` | Explicit rerender logic. |
| `src/ai_mv/core/review/quality_signals.py` | Measurable and LLM-assisted quality signals. |
| `src/ai_mv/core/planning/__init__.py` | Separate planning domain from stage wrappers. |
| `src/ai_mv/core/planning/intent_interpreter.py` | Turn `concept_text` into style/music/visual intent. |
| `src/ai_mv/core/planning/shot_planner.py` | Generic shot planning layer. |
| `src/ai_mv/core/planning/render_routing.py` | Keep i2v/ia2v/flf2v routing explicit but style-neutral. |

### Likely add later

| Create | Why |
|---|---|
| `src/ai_mv/styles/common/` | Shared style utilities once multiple style packs exist. |
| `src/ai_mv/core/review/llm_judge.py` | If LLM-based evaluation becomes large enough to isolate. |
| `src/ai_mv/engines/ffmpeg_mux/` | If ffmpeg assembly grows into a richer engine wrapper. |

---

## 5. Tests Mapping

### Delete or rename

| Current test | Decision | Reason |
|---|---|---|
| `tests/unit/test_citypop_plan.py` | RENAME + SPLIT | Replace with generic planning tests plus style-pack-specific tests. |
| `tests/unit/test_citypop_stages.py` | RENAME + SPLIT | Stage tests should become product-stage tests, not citypop-core tests. |
| `tests/unit/test_citypop_mappers.py` | MOVE/SPLIT | Keep only citypop-specific assertions under a style-pack test area. |
| `tests/performance/test_performance_placeholder.py` | DELETE or replace | Placeholder-style performance tests should become real benchmarks or be removed. |

### Keep and expand

| Current test | Decision | Reason |
|---|---|---|
| `tests/unit/test_cli_args.py` | KEEP + REWRITE | Lock canonical single-input CLI contract. |
| `tests/unit/test_start_entrypoint.py` | KEEP + REWRITE | Ensure no legacy public paths remain. |
| `tests/unit/test_preflight_entrypoint.py` | KEEP + REWRITE | Same as above. |
| `tests/unit/test_pipeline.py` | KEEP + EXPAND | Protect stage ordering, rerender loop, artifact contracts. |
| `tests/integration/test_pipeline_smoke.py` | KEEP + EXPAND | End-to-end skeleton remains essential. |
| `tests/unit/test_codex_cli_client.py` | KEEP + FIX | LLM integration becomes more important, not less. |
| `tests/unit/test_doctor_checks.py` | KEEP | Runtime operability matters. |
| `tests/unit/test_state_store.py` | KEEP | Core state contract. |
| `tests/unit/test_input_gate.py` | KEEP | Canonical input contract. |

### New tests to add

| Create | Purpose |
|---|---|
| `tests/unit/test_concept_text_contract.py` | Ensure all public entrypoints accept and normalize only canonical input. |
| `tests/unit/test_style_resolution.py` | Test how styles are inferred or selected internally from concept text. |
| `tests/unit/test_review_models.py` | Lock review schema and reason structure. |
| `tests/unit/test_rerender_policy.py` | Ensure rerender decisions are stable and review-driven. |
| `tests/unit/test_quality_signals.py` | Protect measurable quality heuristics. |
| `tests/unit/test_style_citypop_pack.py` | Keep citypop-specific behavior isolated within style layer. |

---

## 6. Migration Waves

### Wave 1: Product truth alignment
**Objective:** Make docs and public CLI truthful.

Files:
- `README.md`
- `docs/README.md`
- `src/ai_mv/cli/args.py`
- `src/ai_mv/cli/commands.py`
- `src/ai_mv/entrypoints/start.py`
- `src/ai_mv/entrypoints/preflight.py`
- tests around CLI/entrypoints

Outcome:
- no more public `profile`/`brief` contract
- docs no longer claim citypop-only product identity

### Wave 2: Style extraction
**Objective:** Move citypop-specific logic out of shared layers.

Files:
- `src/ai_mv/core/stages/plan_citypop_mv.py`
- add `src/ai_mv/styles/citypop/*`
- related tests

Outcome:
- `core` becomes style-neutral
- citypop becomes the first style pack instead of the product itself

### Wave 3: Review promotion
**Objective:** Turn review into a real subsystem.

Files:
- `src/ai_mv/core/stages/review_outputs.py`
- new `src/ai_mv/core/review/*`
- artifacts/state/reporting/tests

Outcome:
- rerender reasoning becomes explicit and testable
- final-output quality gates improve

### Wave 4: Large-file decomposition
**Objective:** Lower architectural risk and improve maintainability.

Files:
- `src/ai_mv/engines/acestep_1_5_aio/planner.py`
- `src/ai_mv/core/contracts/prompt_normalize.py`
- possibly `policy.py`

Outcome:
- smaller contract-driven modules
- more precise regression coverage

---

## 7. Risks and Tradeoffs

### Risk: aggressive deletion breaks current habits
Mitigation:
- do deletion in waves
- harden tests before removal
- if absolutely necessary, keep only a very short deprecation period

### Risk: style extraction creates temporary duplication
Mitigation:
- accept short-term duplication to gain architectural clarity
- deduplicate only after core/style boundary is stable

### Risk: review subsystem expansion increases complexity
Mitigation:
- keep contracts explicit
- isolate LLM-assisted review from deterministic signal extraction

### Risk: renaming too much at once causes churn
Mitigation:
- change product truth first
- extract style layer second
- rename engine packages later when behavior is stable

---

## 8. Most Important “Do Not Compromise” Rules

1. Do not keep `profile` and `legacy_brief` as public concepts.
2. Do not leave citypop worldview embedded as universal truth in `core`.
3. Do not treat review as a minor post-processing step.
4. Do not optimize for speed before final MV quality is protected.
5. Do not preserve confusing names just because they already exist.

---

## 9. Recommended First Execution Slice

If implementation begins immediately, the first slice should be:

1. Rewrite public docs and CLI contract around `concept_text`
2. Remove `legacy_brief` and public `--brief`
3. Add failing tests for single-input contract
4. Make those tests pass
5. Create `styles/citypop/` and move only the first chunk of citypop-specific constants/helpers there

This gives the fastest alignment between product truth and code truth.

---

## 10. Final Summary

The repository already has a usable orchestration skeleton, engine adapter layer, state/artifact layer, and runtime support. The real problem is not total lack of structure; it is that the current structure still encodes an older citypop-rebuild identity and several legacy public interfaces.

The correct migration path is therefore:
- not a total rewrite
- but a directed architectural extraction

In short:
- keep the orchestration spine
- delete legacy UX
- extract style-specific logic
- promote review/rerender to a first-class domain
- harden with regression tests
