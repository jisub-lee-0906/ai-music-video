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

4. prompt-lab.md
How to test prompt syntax outside the main ai-mv pipeline before encoding findings into repo-side prompt contracts.

5. frame-validation.md
How to validate stills, clips, and final MV outputs through representative frame extraction.

6. workflow-usage.md
Current workflow usage and mapper/binding expectations.

7. workflow-binding-notes.md
Workflow node binding notes and ComfyUI integration assumptions.

8. m2-ia2v-spec.md
Current ia2v routing and audio-reactive clip constraints.

9. m3-flf2v-spec.md
Current flf2v transition routing constraints.

10. first-run-checklist.md
Operational checklist for real runs.

Reference / support material:
- repo-restructure.md
  Current-state architecture status and remaining legacy seams.
- implementation-change-map.md
  Current-state legacy ledger and cleanup map.

Operating rule for this folder:
- Treat the product-direction charter and structure-migration mapping as canonical.
- Keep this folder limited to docs that still describe the current architecture or support active workflow/prompt/review work.
- Remove drifted historical docs instead of leaving them around as quasi-canonical references.
