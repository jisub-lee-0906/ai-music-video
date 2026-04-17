# ai-mv Docs Index

This docs directory now supports the current ai-mv product direction:
- concept_text-first UX
- multi-style MV generation
- mandatory music generation
- final-MV quality as the main success metric
- strong ComfyUI/workflow orchestration
- review and rerender loops that improve weak outputs

Read these first:

1. ../README.md
Top-level product overview and current command surface.

2. ../.hermes/plans/2026-04-15_202152-product-direction-charter.md
Canonical product direction and non-negotiable architecture rules.

3. ../.hermes/plans/2026-04-15_202537-structure-migration-mapping.md
Target architecture, keep/move/delete expectations, and migration priorities.

4. workflow-usage.md
Current workflow usage and mapper/binding expectations.

5. workflow-binding-notes.md
Workflow node binding notes and ComfyUI integration assumptions.

6. m2-ia2v-spec.md
Current ia2v routing and audio-reactive clip constraints.

7. m3-flf2v-spec.md
Current flf2v transition routing constraints.

8. first-run-checklist.md
Operational checklist for real runs.

Historical / style-pack-specific material:
- archived/citypop-mv-master-plan.md
  Historical citypop-first plan. Useful as style-pack reference, not as repo-wide product truth.
- repo-restructure.md
  Older restructuring notes that still contain citypop-era assumptions and should be read as transitional context only.
- implementation-change-map.md
  Transitional implementation map with historical assumptions mixed in.
- legacy-deletion-plan.md
  Useful deletion notes, but some entries reflect an older citypop-first reset and should be reconciled against the current charter.

Operating rule for this folder:
- Treat the product-direction charter and structure-migration mapping as canonical.
- Treat citypop-specific docs as style-pack history unless they are explicitly rewritten for the current architecture.
- Treat older files under `docs/plans/` as historical implementation notes when they reference removed stage names, old tests, or citypop-first assumptions.
