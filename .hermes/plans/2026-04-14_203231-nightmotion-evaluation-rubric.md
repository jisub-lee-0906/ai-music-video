# Nightmotion Evaluation Rubric and Investigation Plan

> For Hermes: use this rubric before making further workflow or prompting changes.

Goal: Evaluate whether the current ai-music-video pipeline can produce a musically and visually coherent MV, not just good isolated stills.

Architecture: Audit the pipeline in layers from A→Z: config and routing, prompt generation, workflow-specific suitability, official-doc grounding, still continuity, video suitability, and final MV readiness. Do not treat preflight success or strong single images as proof of MV quality.

Tech stack: ai-mv Python pipeline, Qwen still generation, LTX i2v / ia2v / flf2v workflows, WSL wrappers, ComfyUI workflows.

---

## Evaluation gates

### Gate 1: Structural correctness and A→Z flow
Questions:
- Does the pipeline move cleanly from concept_text/audio brief → audio plan → shot plan → render plan → stills → clips → final assemble?
- Are there hidden assumptions where smoke mode forces a weak default route?
- Is the chosen video workflow actually being selected intentionally, or just inherited from defaults?
- Are artifacts written at each stage so failures can be inspected without guessing?

Evidence to collect:
- active config values for planning.enable_ia2v / enable_flf2v
- actual shot_plan and render_plan for a real run
- render_mode distribution across shots
- snapshot transitions across stages
- final output existence and stage failure location if incomplete

Pass condition:
- Routing is explainable shot-by-shot and consistent with intended MV behavior.

### Gate 2: Prompt quality itself
Questions:
- Are prompts strong as prompts, not just as general aesthetic text?
- Do they encode subject, location, motion implication, framing, and continuity anchors clearly?
- Are they overly generic, overly decorative, or too still-image-centric?
- Do they introduce conflicting objectives between still beauty and video usability?

Evidence to collect:
- prompt_seed / prompt_draft / prompt_polish per shot
- repeated motifs/anchors across neighboring shots
- negative prompt alignment with target workflow
- whether prompts are section-aware and transition-aware

Pass condition:
- Prompt text is specific, internally coherent, and optimized for the intended render mode.

### Gate 3: Workflow-specific prompt suitability
Questions:
- Is the same prompt style being reused blindly for qwen stills, i2v, ia2v, and flf2v?
- Does each workflow receive the kind of prompt it actually benefits from?
- Are flf2v bridge shots given prompts/images that support start→end transformation?
- Are i2v keyframes motion-safe, or only pretty as standalone illustrations?

Evidence to collect:
- exact mapper inputs per workflow
- prompt field mapping differences between workflows
- image-to-video source assets used for each shot
- shot roles that should prefer i2v vs ia2v vs flf2v

Pass condition:
- Each workflow gets prompts/assets tailored to what that workflow does best.

### Gate 4: Official-document validation
Questions:
- Are workflow prompting assumptions grounded in official docs / workflow docs / model docs, not imagination?
- Do current assumptions about i2v, ia2v, and flf2v prompting match documented behavior?
- Are negative prompt and input-asset recommendations documented by the actual tools/models?

Evidence to collect:
- official documentation links and excerpts for each workflow/model
- prompt guidance, input constraints, asset requirements, and failure patterns from docs
- mismatches between docs and current implementation

Pass condition:
- Every major workflow/prompting rule can be justified from official documentation or first-party examples.

### Gate 5: Image continuity
Questions:
- Do neighboring stills share character identity, palette logic, camera logic, and environment continuity?
- Does the sequence feel like consecutive moments of one MV rather than unrelated illustrations?
- Do section changes feel intentional rather than random?

Evidence to collect:
- still sequence ordered by shot_id
- continuity problems: face drift, costume drift, background drift, framing jumps, lighting mismatch
- whether prompt text preserves continuity anchors across adjacent shots

Pass condition:
- Adjacent stills feel like a sequence, not a gallery.

### Gate 6: Video usability of stills
Questions:
- If a still is used as i2v or flf2v source, will it animate cleanly?
- Does it have stable composition, readable subject separation, and enough motion affordance?
- Is the frame too busy, too collage-like, too symmetric, or too fragile for animation?
- For flf2v, are start and end frames compatible enough to bridge smoothly?

Evidence to collect:
- still composition review by render_mode
- which images are being used as first/last keyframes for flf2v
- whether chorus/bridge/transition shots have the right source imagery

Pass condition:
- Still assets are not only attractive, but usable as video keyframes.

### Gate 7: MV suitability
Questions:
- Does the shot sequence follow musical energy and section changes?
- Are transitions emotionally and rhythmically aligned with the song?
- Does the chorus visually escalate?
- Does the bridge actually pivot the visual language?
- Does the whole sequence feel like a music video rather than a slideshow of nice images?

Evidence to collect:
- shot_plan vs song sections
- visual energy curve across sections
- transition logic between shots
- final clip timing and assembly outputs

Pass condition:
- The resulting sequence reads as an MV with flow, progression, and payoff.

---

## Immediate investigation order

1. Confirm final status of the current run and save all artifacts.
2. Extract shot_plan/render_plan and tabulate render_mode per shot.
3. Compare planned workflow routing against actual MV needs.
4. Review still sequence in shot order for continuity and video usability.
5. Audit prompt text per shot for continuity anchors and workflow fitness.
6. Gather official docs for Qwen still workflow, LTX i2v, LTX ia2v, and LTX flf2v.
7. Produce a gap report:
   - structural issues
   - prompt issues
   - workflow-selection issues
   - continuity issues
   - MV-direction issues
8. Only after that, propose targeted fixes with rollback paths.

---

## Current working hypothesis

The current pipeline is likely strong at generating attractive single stills and acceptable audio/planning outputs, but weak in three areas:
- intentional workflow routing for motion/video needs
- continuity constraints across shots
- MV-level transition design

This hypothesis must be tested against the collected artifacts and official docs before any implementation changes.
