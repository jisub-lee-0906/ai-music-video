# ai-mv Product Direction Charter

> **For Hermes:** Use subagent-driven-development skill to implement this plan task-by-task.

**Goal:** Redefine `ai-mv` as a concept-text-first, multi-style, final-MV-focused music video generation platform and use this document as the canonical decision source for future refactors.

**Architecture:** Keep ComfyUI/workflow orchestration as the execution backbone, but move style-specific logic out of `core` into pluggable style modules/presets. Simplify the external UX to a single `concept_text` input while allowing deep internal planning, LLM-assisted review, and rerender loops to maximize final MV quality.

**Tech Stack:** Python 3.11+, ComfyUI workflows, ffmpeg/ffprobe, Codex/LLM assistance, pytest, WSL wrappers

---

## 1. Canonical Product Definition

`ai-mv` is a personal-use AI music video generation platform that takes a single `concept_text` input and produces a publishable-quality final music video by orchestrating music generation, visual planning, still generation, clip generation, assembly, review, and rerender decisions.

This project is not:
- a citypop-only generator
- a profile-driven pipeline
- a generic workflow sandbox with no product opinion
- a middle-artifact-first toolkit

This project is:
- a final-output-first MV platform
- multi-style from the start
- quality-first over speed-first
- strongly dependent on ComfyUI/workflows as the execution engine
- willing to use LLMs not only for prompting but also for evaluation and rerender judgment

---

## 2. Success Criteria

The project is successful when:
- it can generate a commercially viable music video suitable for YouTube publication
- the final MV quality is more important than elegance of intermediate artifacts
- repeated runs are good often enough to be practically useful
- rerender/review loops meaningfully improve weak outputs
- the user can start a run with a very simple input experience

Primary success metric:
- `final_mv.mp4` is good enough to publish

Secondary metrics:
- music-video coherence
- visual consistency within a run
- style adherence to the requested concept
- rerender usefulness
- reproducibility of strong outputs

---

## 3. Product Priorities

Locked priority order from user answers:
1. Quality
2. Automation
3. Simple UX
4. Maintainability
5. Reproducibility
6. Extensibility
7. Speed

Interpretation:
- Never sacrifice final MV quality just to preserve old structure.
- Automation and rerender loops matter more than manual tuning convenience.
- Keep the surface area tiny even if internal orchestration is sophisticated.
- Speed matters, but only after quality and correctness are protected.

---

## 4. User and Usage Model

Primary user:
- the repository owner only

Implications:
- no need to preserve broad backwards compatibility for external users
- old flows should be removed aggressively when they conflict with the new product direction
- UX should be optimized for fast personal iteration, not for enterprise configurability

---

## 5. Input and UX Contract

### External input contract

The canonical user-facing input is:
- `concept_text`

The desired UX is:
- one command
- one primary text input
- minimal optional knobs exposed to the user

### What `concept_text` should imply internally

The system may derive from `concept_text`:
- music direction
- lyrical seed
- genre/style intent
- visual world rules
- shot plan
- review expectations

### Explicit UX rules

User-facing CLI/API should prefer:
- `ai-mv start --concept-text "..."`

Avoid exposing by default:
- separate `audio_brief`
- separate `audio_hook_brief`
- profile files
- legacy `--brief`
- style-specific plumbing details
- low-level workflow node controls

If advanced configuration is needed later, it should be layered behind the primary simple UX, not replace it.

---

## 6. Style Strategy

### Final direction

The platform supports multiple styles from the beginning.

### Architectural implication

Style-specific rules must not live inside `core` as hard-coded product truth.

Instead:
- `core` should be style-neutral orchestration
- style packs/presets should contain aesthetic defaults, prompt seeds, visual motifs, and routing hints
- citypop may remain as the first or best-developed style pack, but not as the identity of the whole product

### Immediate consequence

Any hard-coded `citypop_bible` logic embedded as universal truth is technical debt unless moved into a style layer.

---

## 7. Music Generation Policy

Music generation is mandatory.

This means the platform is not merely a visualizer for external tracks.
The core promise is end-to-end MV creation where music and visuals are generated as parts of one system.

Implications:
- music generation is a first-class stage, not an optional adapter
- downstream planning should assume music timing/structure exists
- quality review must include music-video alignment, not just visual quality

---

## 8. Workflow and ComfyUI Policy

ComfyUI/workflow dependence stays strong.

This means:
- workflow orchestration is core product infrastructure, not a temporary implementation detail
- abstraction is allowed, but not at the cost of hiding critical workflow reality from the codebase
- design should optimize for reliable workflow composition and reviewable routing

Implications:
- `engines/` remains strategically important
- mapper/runner boundaries should stay explicit
- workflow contracts should be tested and versioned carefully

---

## 9. LLM/Codex Policy

LLMs are allowed to participate through:
- prompt draft/polish
- planning support
- review judgment
- rerender decision support

This means LLMs are not just cosmetic assistants.
They are part of the production logic where subjective judgment is valuable.

Design constraints:
- LLM outputs must be bounded by explicit schemas/contracts
- review/rerender logic should record reasons, not only verdicts
- deterministic guardrails and validation remain necessary around subjective model outputs

---

## 10. Review Philosophy

Review is a first-class product feature.

The target review level is close to human aesthetic judgment, not just file existence checks.

### Review should evaluate
- style fit to requested concept
- identity/subject consistency
- motion quality
- composition quality
- transition coherence
- music-visual synchronization
- publishability of the final MV

### Review should produce
- pass/fail
- per-shot weaknesses
- rerender target list
- rerender reasons
- confidence or score signals
- final output quality summary

### Anti-goal

Review must not remain a shallow stage that only verifies files exist and durations roughly match.

---

## 11. Legacy Deletion Policy

Legacy systems should be removed aggressively.

Delete or retire:
- `profile`-driven inputs
- `legacy_brief`
- public `--brief` compatibility path
- dead citypop-only assumptions in shared layers
- old stage naming that no longer reflects the real pipeline
- code paths kept only for historical comfort

Rule:
- if a legacy path weakens product clarity, remove it
- do not keep obsolete interfaces just because they existed before

Temporary compatibility should only be kept if it directly reduces refactor risk during a short transition window.
Default posture is deletion, not preservation.

---

## 12. Testing Policy

Testing should be strict and regression-oriented.

### Minimum required coverage areas
- CLI input contract
- pipeline stage ordering and payload contracts
- style routing logic
- workflow binding contracts
- review/rerender decision contracts
- artifact/state outputs
- key prompt/planning schema validation

### Test philosophy
- protect product-defining behavior first
- prefer contract tests and regression tests for major pipeline behavior
- ensure refactors cannot silently degrade final-output-oriented logic

### What is not enough
- smoke tests alone
- tests that only prove files were created
- tests that do not guard aesthetic or routing assumptions where measurable signals exist

---

## 13. Architectural Principles

### Principle 1: Final-output-first
The architecture exists to improve final MV quality, not to preserve pretty abstraction boundaries.

### Principle 2: Style-neutral core
`core` should orchestrate, not embed one permanent aesthetic worldview.

### Principle 3: Single-input UX
The system may be internally complex, but externally it should feel simple.

### Principle 4: Strong workflow realism
ComfyUI/workflow details are real constraints and should be modeled honestly.

### Principle 5: Review-driven iteration
Generation quality comes from generate → review → rerender loops, not one-pass optimism.

### Principle 6: Delete confusion
When a structure or name no longer matches the product, remove it.

### Principle 7: Strict contracts everywhere subjective logic touches automation
The more LLM judgment is used, the more explicit the schemas and verification must be.

---

## 14. Target High-Level Architecture

Recommended target layering:

```text
src/ai_mv/
  cli/                 # minimal user-facing commands
  entrypoints/         # start/preflight/status/doctor orchestration entry
  core/
    orchestration/     # stage sequencing, retries, rerender loop
    contracts/         # schemas, typed payload contracts, validators
    review/            # scoring, judgment aggregation, rerender decisions
    artifacts/         # manifests, summaries, outputs
    state/             # run state and snapshots
  styles/              # multi-style packs/presets (citypop, etc.)
  engines/             # workflow-specific mappers/runners
  infra/               # ComfyUI, LLM, locking, transport, env checks
  utils/               # pure helpers only
```

### Boundary rules

`core` owns:
- pipeline logic
- payload/state contracts
- rerender loop policy
- quality gates

`styles` owns:
- style presets
- aesthetic defaults
- motif/palette/negative guidance
- style-specific planning hints

`engines` owns:
- workflow mapping
- workflow execution
- engine-specific IO transformation

`infra` owns:
- external process and API integration
- runtime environment checks
- transport details

---

## 15. Recommended Pipeline Direction

Suggested canonical stage sequence:
1. input normalization
2. music generation
3. style/intent interpretation
4. visual planning
5. still generation
6. clip generation
7. assembly
8. aesthetic review
9. rerender loop
10. final artifact publish

Notes:
- stage names should match actual responsibilities
- review and rerender are not optional sidecars; they are part of the main value loop
- if current code uses citypop-specific naming in shared stages, that should be generalized

---

## 16. Current Repository Drift Against This Charter

### Drift A: The docs disagree with each other
- some docs define a citypop-only product
- current user direction defines a multi-style platform

### Drift B: README/CLI still expose legacy inputs
- `--brief`
- profile-based language
- old pipeline terminology

### Drift C: Core contains style-specific assumptions
- `plan_citypop_mv.py`
- embedded `citypop_bible` style worldview

### Drift D: Review is too weak for the desired quality bar
- current structure appears closer to asset verification than publishability evaluation

### Drift E: Some large files indicate over-concentrated domain logic
- `engines/acestep_1_5_aio/planner.py`
- `core/stages/plan_citypop_mv.py`
- `core/contracts/prompt_normalize.py`

---

## 17. Immediate Decisions Now Locked

These are now the canonical decisions:
- The project is multi-style, not citypop-only.
- The primary user-facing input is `concept_text`.
- Music generation is mandatory.
- Final MV is the main product, not intermediate artifacts.
- ComfyUI/workflow dependence remains strong.
- LLMs are allowed in review and rerender judgment.
- Legacy inputs and old profile flows should be deleted aggressively.
- Testing should be strict and regression-focused.
- Product quality matters more than speed.

---

## 18. Practical Deletion / Keep / Move Rules

### Delete
- profile-centric docs and code paths
- `legacy_brief`
- public support for `--brief`
- citypop-as-universal-truth assumptions in shared layers
- obsolete stage names and payload keys from previous pipeline generations

### Keep
- ComfyUI engine wrappers
- mapper/runner pattern
- state/artifact infrastructure
- WSL runtime support
- pipeline orchestration skeleton

### Move or Refactor
- citypop-specific prompt/planning logic -> `styles/citypop/...`
- aesthetic review logic -> `core/review/...`
- giant planning files -> smaller contract-driven modules
- input normalization -> one canonical `concept_text` path

---

## 19. Next Refactor Plan Themes

### Theme 1: Canonical product rewrite
Update docs so the repo has one truthful product definition.

### Theme 2: Input simplification
Collapse all public input paths into `concept_text`.

### Theme 3: Style extraction
Extract citypop-specific logic from `core` into a style layer.

### Theme 4: Review upgrade
Turn review into a true aesthetic quality gate with rerender reasoning.

### Theme 5: Contract hardening
Protect key behaviors with strict regression tests before large deletions.

---

## 20. Open Questions Deferred for Later

These are secondary and should not block the above charter:
- how styles are selected internally from `concept_text`
- whether style packs will later become explicit plugins
- how far publish/export tooling should go
- whether multiple music generation backends will be supported

These matter later, but they do not change the product identity locked above.

---

## 21. Final Summary

This repository should stop thinking of itself as a citypop rebuild and start thinking of itself as a final-MV production system.

The shortest truthful definition is:

`ai-mv` is a quality-first, concept-text-driven, multi-style AI music video generation platform that uses ComfyUI workflows and LLM-assisted review/rerender loops to produce publishable final music videos.
