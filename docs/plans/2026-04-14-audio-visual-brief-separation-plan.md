# Audio / Visual Brief Separation Implementation Plan

> **For Hermes:** Use subagent-driven-development skill to implement this plan task-by-task.

**Goal:** Improve audio lyric quality and audio/visual consistency at the same time by separating music-facing intent from still-image-facing intent, without breaking the current WSL wrappers or the existing concept-driven workflow.

**Architecture:** Keep `concept_text` as the shared story/world anchor, but stop treating it as the only source of truth for every downstream module. Add a small, rollbackable config layer where audio planning can prefer `audio.brief` and `audio.hook_brief`, while visual generation can continue using shared concept plus render-specific constraints. This preserves compatibility, reduces cross-contamination from image-only wording, and keeps rollback to a few files.

**Tech Stack:** Python, pytest, existing `ai_mv` CLI/entrypoints, config defaults, AceStep audio planner, Qwen still generation pipeline.

---

## Root Cause Summary

Observed facts from the current codebase:
- `src/ai_mv/entrypoints/preflight.py` and `src/ai_mv/entrypoints/start.py` only accept `concept_text` from the CLI and inject it into config.
- `src/ai_mv/engines/acestep_1_5_aio/planner.py:143-148` copies `concept_text` into `audio.brief` / `hook_brief` when no separate prompt is provided.
- `src/ai_mv/core/contracts/prompt_normalize.py:487-497` rejects chorus-family lyrics when there is no short memorable hook line.
- The audio path is intentionally strict about singability, hook clarity, and section-role contrast.
- The visual path benefits from explicit anti-panel wording, but that wording is not musically useful.

Current failure mode:
- A single mixed-purpose `concept_text` can contain image-specific constraints such as `single cinematic keyframe stills` or `no comic panels`.
- That same text is currently eligible to become the audio brief.
- The audio planner therefore receives a less music-focused intent packet, increasing the chance of generic or explanatory chorus lines that fail the hook-quality gate.

Design principle for the fix:
- Share emotional arc and world anchor.
- Separate expression-specific constraints.
- Do not weaken the audio quality gate; improve the inputs instead.

---

## Safety / Rollback

This plan is intentionally minimal-risk.

Primary rollback targets:
- `src/ai_mv/core/orchestration/config_defaults.py`
- `src/ai_mv/cli/args.py`
- `src/ai_mv/entrypoints/preflight.py`
- `src/ai_mv/entrypoints/start.py`
- `src/ai_mv/engines/acestep_1_5_aio/planner.py`
- `docs/sample-config.yaml`
- related tests only

Rollback strategy:
1. Revert CLI additions for audio-specific arguments.
2. Revert config defaults for `audio.brief` / `audio.hook_brief` / any visual-only field added in this plan.
3. Revert planner preference logic so audio falls back to `concept_text` exactly as before.
4. Revert tests.

Do not change workflow templates, WSL networking, or render engine internals in the same change.

---

## Proposed Behavior

### Shared anchor stays
Keep `concept_text` as the canonical shared project/story anchor, for example:
- setting
- emotional arc
- world mood
- a few shared symbolic images

### Audio-specific inputs get their own lane
Add optional config keys under `audio`:
- `audio.brief`
- `audio.hook_brief`
- optional later: `audio.avoid`

Audio planner precedence after the change:
1. explicit `audio.brief`
2. legacy `prompt` / `--brief` if still present
3. fallback `concept_text`

Hook candidate precedence after the change:
1. explicit `audio.hook_brief`
2. fallback `audio.brief`
3. fallback `concept_text`

### Visual-specific constraints stay out of audio
Do not feed these into audio brief generation:
- `single cinematic keyframe`
- `no comic panels`
- `no split screen`
- camera/composition wording
- still-generation anti-collage constraints

### What should remain shared
Use `concept_text` for shared semantic alignment only:
- late-night drive
- bittersweet summer romance
- unresolved longing turning into quiet resolve
- neon reflections / station light / sea wind

---

## Task 1: Lock current and desired behavior with tests

**Objective:** Create precise tests before code changes so we can separate audio and visual intent without breaking compatibility.

**Files:**
- Modify: `tests/unit/test_cli_args.py`
- Modify: `tests/unit/test_audio_contract.py` or create a planner-focused test file if a cleaner location exists
- Modify: `tests/unit/test_doctor_entrypoint.py` only if CLI wiring indirectly affects existing expectations

**Step 1: Add parser coverage**
Add tests asserting we can parse new optional arguments cleanly, for example:
- `ai-mv preflight --audio-brief "..."`
- `ai-mv preflight --audio-hook-brief "..."`
- `ai-mv start --audio-brief "..."`
- `ai-mv start --audio-hook-brief "..."`

**Step 2: Add planner precedence tests**
Add tests for planner source selection:
- when `audio.brief` exists, audio planner uses it instead of `concept_text`
- when `audio.hook_brief` exists, hook generation uses it instead of broad concept text
- when those fields are absent, current fallback behavior still works

**Step 3: Add compatibility test**
Add one test proving a plain `concept_text`-only invocation still behaves like today.

**Step 4: Run tests to verify RED if needed**
Run:
`pytest tests/unit/test_cli_args.py tests/unit/test_audio_contract.py -v`

Expected:
- some failures because new CLI/config/planner behavior is not implemented yet

**Step 5: Commit checkpoint after green later**
Use a commit like:
`git commit -m "test: lock audio brief separation behavior"`

---

## Task 2: Add minimal config fields for audio-specific intent

**Objective:** Introduce small, explicit config hooks for music-facing prompts without changing existing behavior for users who do nothing.

**Files:**
- Modify: `src/ai_mv/core/orchestration/config_defaults.py`
- Modify: `docs/sample-config.yaml`

**Step 1: Add safe optional defaults**
Under `DEFAULT_CONFIG["audio"]`, add empty-string fields:
- `brief: ""`
- `hook_brief: ""`
- optional but recommended if already used elsewhere: `negative_direction: ""`

Do not remove `concept_text`.
Do not force users to populate the new fields.

**Step 2: Mirror in docs**
In `docs/sample-config.yaml`, document:
- `concept_text` = shared story/world anchor
- `audio.brief` = music-only brief
- `audio.hook_brief` = short-hook guidance for chorus generation

**Step 3: Verification**
Run:
`pytest tests/unit/test_cli_args.py tests/unit/test_bootstrap.py -v`

Expected:
- defaults still load
- current bootstrap behavior remains intact

**Step 4: Commit**
`git commit -m "feat: add audio-specific brief config defaults"`

---

## Task 3: Extend CLI/entrypoints without breaking old usage

**Objective:** Let users pass audio-specific brief fields from CLI while preserving current `--concept-text` and legacy `--brief` compatibility.

**Files:**
- Modify: `src/ai_mv/cli/args.py`
- Modify: `src/ai_mv/cli/commands.py` if needed for argument forwarding
- Modify: `src/ai_mv/entrypoints/preflight.py`
- Modify: `src/ai_mv/entrypoints/start.py`

**Step 1: Add new optional args**
Add parser args:
- `--audio-brief`
- `--audio-hook-brief`

Keep existing:
- `--concept-text`
- `--brief` (legacy)

**Step 2: Wire into prepared config**
In `_load_prepared_config(...)` for both preflight and start:
- set `cfg["audio"]["brief"]` when provided
- set `cfg["audio"]["hook_brief"]` when provided
- preserve current fallback to `concept_text` when not provided

**Step 3: Preserve run artifact writing**
Continue writing `concept_text.txt` as before.
Optionally add new artifact files later, but do not require that in this first pass.

**Step 4: Verification**
Run:
`pytest tests/unit/test_cli_args.py tests/unit/test_doctor_entrypoint.py -v`

Expected:
- parser accepts new args
- existing entrypoint tests still pass or need only minimal updates

**Step 5: Commit**
`git commit -m "feat: accept audio-specific brief CLI overrides"`

---

## Task 4: Change audio planner precedence only, not its quality gates

**Objective:** Improve lyric quality by changing which text the audio planner prefers, while leaving validation rules intact.

**Files:**
- Modify: `src/ai_mv/engines/acestep_1_5_aio/planner.py`

**Step 1: Refactor source selection into a tiny helper**
Create a small helper, e.g. `_resolve_audio_brief_inputs(config)`, that returns:
- chosen audio brief
- chosen hook brief
- concept fallback metadata

Recommended precedence:
- audio brief: `audio.brief` > `prompt` / legacy brief > `concept_text`
- hook brief: `audio.hook_brief` > `audio.brief` > legacy brief > `concept_text`

**Step 2: Keep current defaults safe**
If user provides none of the new fields, behavior should remain compatible with the current code.

**Step 3: Do not modify these in the same change**
- `validate_audio_lyrics_quality(...)`
- bar-fit constraints
- section-role minimums
- hook-length thresholds

The purpose of this task is better input quality, not weaker validation.

**Step 4: Verification**
Run:
`pytest tests/unit/test_audio_contract.py tests/unit/test_cli_args.py -v`

Expected:
- hook-quality tests still pass
- new precedence tests pass

**Step 5: Commit**
`git commit -m "feat: prefer audio-specific brief sources in planner"`

---

## Task 5: Add observability for debugging, but keep it low risk

**Objective:** Make it easier to debug future audio failures without changing render semantics.

**Files:**
- Modify: `src/ai_mv/entrypoints/preflight.py`
- Modify: `src/ai_mv/entrypoints/start.py`
- Optional modify: artifact-writing helpers if there is already a clean pattern

**Step 1: Save input artifacts**
When present, write these alongside existing run inputs:
- `inputs/concept_text.txt`
- `inputs/audio_brief.txt`
- `inputs/audio_hook_brief.txt`

**Step 2: Keep naming explicit**
Do not overwrite `concept_text.txt` with audio-specific text.
The point is to make divergence visible.

**Step 3: Verification**
Manual check after one preflight:
- confirm all provided inputs are saved to artifacts
- confirm old runs still work when only `concept_text` exists

**Step 4: Commit**
`git commit -m "feat: persist audio-specific brief artifacts for debugging"`

---

## Task 6: Real validation path before any broader refactor

**Objective:** Confirm the design actually improves audio quality and preserves alignment before touching deeper prompting logic.

**Files:**
- No mandatory new code files

**Step 1: Prepare two controlled smoke runs**
Run A: concept-only
- `concept_text` contains both shared mood and some visual-only constraints

Run B: separated briefs
- `concept_text` contains only shared world/emotion
- `audio.brief` contains music-facing narrative and section expectations
- `audio.hook_brief` contains explicit short-hook guidance

**Step 2: Compare outcomes**
For each run, record:
- whether preflight passes audio stage
- failure reason if not
- whether chorus-family lines include short memorable hooks
- whether resulting plan still matches the same world/emotional arc as the visual system

**Step 3: Success criteria**
The separation design is good enough if:
- audio pass rate improves or failure reasons become more musically meaningful
- chorus hooks become shorter/clearer
- shared concept alignment is still obvious in the plan and later render prompts

---

## Recommended Example Input Shape

Use this kind of split in docs and manual tests:

Shared `concept_text`:
`Japanese 80s city pop night drive, bittersweet summer romance, late-night movement, unresolved longing turning into quiet resolve, neon reflections, station light, sea wind`

`audio.brief`:
`Short-form Japanese city pop song with concrete late-night urban detail. Verse should feel lived-in and cinematic, Pre-Chorus should tighten, Chorus should land a short title-grade hook immediately, Bridge should turn inward, Final Chorus should feel more open and resolved without becoming generic.`

`audio.hook_brief`:
`Give the chorus family at least one short memorable Japanese hook line under the quality gate limit. Prefer a title-worthy phrase tied to neon reflections, late-night motion, sea wind, station light, or the emotional turn of unresolved longing becoming quiet resolve. Avoid explanatory full-sentence hooks.`

---

## Not In Scope for A안

Do not include these in the first implementation pass:
- weakening audio quality validation thresholds
- redesigning the entire AceStep prompt architecture
- changing still-generation prompt shaping again
- adding automatic seed sweeps for audio
- introducing a new cross-modal planning service
- changing workflow JSON templates

---

## Acceptance Criteria

- Users can provide `audio.brief` and `audio.hook_brief` without losing existing `concept_text` support.
- `concept_text` remains the shared story/world anchor.
- Audio planner prefers audio-specific fields when present.
- Audio quality gates remain unchanged.
- Input artifacts make debugging easier.
- Existing concept-only workflows remain compatible.
- Change is easy to revert file-by-file.

---

## Suggested Execution Order

1. Add tests for parser + planner precedence.
2. Add config defaults and sample config docs.
3. Add CLI/entrypoint wiring.
4. Change planner precedence.
5. Add artifact persistence.
6. Run controlled smoke comparison.

---

## Verification Commands

Parser / config:
`pytest tests/unit/test_cli_args.py tests/unit/test_bootstrap.py -v`

Audio planner / contracts:
`pytest tests/unit/test_audio_contract.py -v`

Entrypoints:
`pytest tests/unit/test_doctor_entrypoint.py -v`

Suggested regression bundle after implementation:
`pytest tests/unit/test_cli_args.py tests/unit/test_bootstrap.py tests/unit/test_audio_contract.py tests/unit/test_doctor_entrypoint.py tests/unit/test_citypop_stages.py -v`
