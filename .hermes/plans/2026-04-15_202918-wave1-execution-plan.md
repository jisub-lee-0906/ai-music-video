# Wave 1 Truth Sync Implementation Plan

> **For Hermes:** Use subagent-driven-development skill to implement this plan task-by-task.

**Goal:** Align public docs and public CLI behavior with the new charter by removing legacy/profile/brief UX and making `concept_text` the single canonical user-facing input.

**Architecture:** Wave 1 intentionally avoids deep pipeline rewrites. It focuses on the product-truth layer: README, CLI parser, command dispatch, start/preflight entrypoints, and the tests that lock those contracts. The purpose is to make the repo truthful first, so later style extraction and review promotion happen on top of a coherent public interface.

**Tech Stack:** Python 3.11+, argparse, pytest, existing ai-mv CLI/entrypoint structure

---

## Current Context

Current drift confirmed from the codebase:
- `README.md` still describes older profile-based usage and old pipeline stages.
- `src/ai_mv/cli/args.py` still exposes `--brief`, `--audio-brief`, and `--audio-hook-brief`.
- `src/ai_mv/cli/commands.py` still resolves `concept_text or legacy_brief`.
- `src/ai_mv/entrypoints/start.py` and `src/ai_mv/entrypoints/preflight.py` still accept audio-specific briefs and write them to artifact/state files.
- Existing tests actively encode the old contract:
  - `tests/unit/test_cli_args.py`
  - `tests/unit/test_start_entrypoint.py`
  - `tests/unit/test_preflight_entrypoint.py`

Wave 1 scope is intentionally narrow:
- no moving files yet
- no style extraction yet
- no review subsystem rewrite yet
- no engine/package rename yet

Wave 1 success means:
- a new user reading the README sees the true product
- CLI only advertises canonical input behavior
- tests lock that contract
- no public legacy input path remains

---

## Acceptance Criteria

1. `README.md` no longer mentions profile-driven execution, `director_brief_example.yaml`, or public `--brief` usage.
2. `ai-mv start` and `ai-mv preflight` publicly accept `--concept-text` as the only primary content input.
3. `src/ai_mv/cli/args.py` no longer exposes `--brief`, `--audio-brief`, or `--audio-hook-brief`.
4. `src/ai_mv/cli/commands.py` no longer references `legacy_brief`.
5. `src/ai_mv/entrypoints/start.py` and `src/ai_mv/entrypoints/preflight.py` no longer accept or persist audio-specific brief files.
6. CLI and entrypoint tests are rewritten to protect the single-input contract.
7. `uv run pytest tests/unit/test_cli_args.py tests/unit/test_start_entrypoint.py tests/unit/test_preflight_entrypoint.py -q` passes.
8. `uv run pytest -q` is run at the end to surface any follow-on breakage.

---

## Files in Scope

### Modify
- `README.md`
- `src/ai_mv/cli/args.py`
- `src/ai_mv/cli/commands.py`
- `src/ai_mv/entrypoints/start.py`
- `src/ai_mv/entrypoints/preflight.py`
- `tests/unit/test_cli_args.py`
- `tests/unit/test_start_entrypoint.py`
- `tests/unit/test_preflight_entrypoint.py`

### Likely untouched in Wave 1
- `src/ai_mv/core/orchestration/pipeline.py`
- `src/ai_mv/core/stages/*`
- `src/ai_mv/engines/*`
- `src/ai_mv/infra/*`

### Explicitly out of scope
- `plan_citypop_mv.py` extraction
- `styles/` package introduction
- review/rerender subsystem promotion
- deleting docs under `docs/` other than README truth sync if needed later

---

## Implementation Strategy

Order matters:
1. Rewrite tests first to express the new contract.
2. Update parser and command dispatch.
3. Simplify entrypoint signatures and file-writing behavior.
4. Rewrite README last so docs match the now-locked implementation.
5. Run focused tests, then full suite.

This order minimizes ambiguity and prevents “docs say one thing, code another” drift while implementing.

---

## Task 1: Rewrite CLI parser tests to define the new contract

**Objective:** Replace tests that currently protect audio-specific/legacy options with tests that assert a single canonical content input.

**Files:**
- Modify: `tests/unit/test_cli_args.py`
- Test: `tests/unit/test_cli_args.py`

**Step 1: Write failing tests for removed options**

Add or rewrite tests so they assert:
- `start --concept-text ...` still parses successfully
- `preflight --concept-text ...` still parses successfully
- `--brief` is rejected
- `--audio-brief` is rejected
- `--audio-hook-brief` is rejected

Suggested test shape:

```python
import pytest
from ai_mv.cli.args import build_parser


def test_start_rejects_legacy_brief_flag():
    parser = build_parser()
    with pytest.raises(SystemExit):
        parser.parse_args(["start", "--brief", "old"])


def test_preflight_rejects_audio_specific_briefs():
    parser = build_parser()
    with pytest.raises(SystemExit):
        parser.parse_args(["preflight", "--audio-brief", "x"])
```

**Step 2: Run test to verify failure**

Run:
`uv run pytest tests/unit/test_cli_args.py -q`

Expected:
- FAIL because old flags are still accepted.

**Step 3: Update existing tests to remove old expectations**

Delete or rewrite tests that currently assert acceptance of:
- `--audio-brief`
- `--audio-hook-brief`

**Step 4: Run test again after parser changes later**

Run:
`uv run pytest tests/unit/test_cli_args.py -q`

Expected:
- PASS after Tasks 2 and 3 are completed.

---

## Task 2: Remove legacy/public flags from the CLI parser

**Objective:** Make the parser itself truthful and minimal.

**Files:**
- Modify: `src/ai_mv/cli/args.py`
- Test: `tests/unit/test_cli_args.py`

**Step 1: Change parser definitions**

Update `build_parser()` so:
- `start` keeps `--run-id` and `--concept-text`
- `preflight` keeps `--run-id` and `--concept-text`
- remove these arguments entirely:
  - `--brief`
  - `--audio-brief`
  - `--audio-hook-brief`

The target intent is roughly:

```python
start_cmd = sub.add_parser("start")
start_cmd.add_argument("--run-id", default=None)
start_cmd.add_argument("--concept-text", dest="concept_text", default=None)

preflight = sub.add_parser("preflight")
preflight.add_argument("--run-id", default=None)
preflight.add_argument("--concept-text", dest="concept_text", default=None)
```

**Step 2: Run parser tests**

Run:
`uv run pytest tests/unit/test_cli_args.py -q`

Expected:
- parser contract tests pass or now fail only in dispatch/entrypoint areas still expecting removed fields.

---

## Task 3: Remove legacy argument fallback in command dispatch

**Objective:** Ensure command dispatch does not silently preserve deleted public UX.

**Files:**
- Modify: `src/ai_mv/cli/commands.py`
- Test: `tests/unit/test_cli_app.py` (if needed), `tests/unit/test_cli_args.py`

**Step 1: Rewrite dispatch calls**

Current pattern:

```python
kwargs.get("concept_text") or kwargs.get("legacy_brief")
```

Target pattern:

```python
kwargs.get("concept_text")
```

For both `start` and `preflight`.

Also remove references to now-deleted kwargs.

**Step 2: Run focused tests**

Run:
`uv run pytest tests/unit/test_cli_args.py tests/unit/test_cli_app.py -q`

Expected:
- PASS, or only failures in entrypoint tests if signatures are still old.

---

## Task 4: Simplify `start` entrypoint to canonical input only

**Objective:** Remove audio-specific brief handling from public start flow.

**Files:**
- Modify: `src/ai_mv/entrypoints/start.py`
- Test: `tests/unit/test_start_entrypoint.py`

**Step 1: Narrow function signatures**

Update:
- `run_start(...)`
- `_load_prepared_config(...)`

from accepting:
- `concept_text`
- `audio_brief`
- `audio_hook_brief`

to accepting only:
- `concept_text`

Suggested target shape:

```python
def run_start(run_id: str | None = None, concept_text: str | None = None) -> int:
    ...


def _load_prepared_config(concept_text: str | None) -> dict:
    ...
```

**Step 2: Remove audio brief config writes**

Delete logic that:
- copies `audio.brief`
- copies `audio.hook_brief`
- writes `audio_brief.txt`
- writes `audio_hook_brief.txt`

Keep only `concept_text.txt` persistence.

**Step 3: Rewrite tests**

Update `tests/unit/test_start_entrypoint.py` so it verifies:
- `run_start(concept_text=...)` still works
- `_prepare_run_brief()` writes only `concept_text.txt`
- no tests expect audio brief artifact creation

Suggested replacement assertion direction:

```python
def test_prepare_run_brief_writes_only_concept_text(monkeypatch, tmp_path):
    ...
    rid = entry._prepare_run_brief({"concept_text": "night drive"}, "run-123")
    assert (state_dir / "concept_text.txt").exists()
    assert not (state_dir / "audio_brief.txt").exists()
```

**Step 4: Run focused tests**

Run:
`uv run pytest tests/unit/test_start_entrypoint.py -q`

Expected:
- PASS

---

## Task 5: Simplify `preflight` entrypoint to canonical input only

**Objective:** Mirror the `start` cleanup in preflight so the public UX is consistent.

**Files:**
- Modify: `src/ai_mv/entrypoints/preflight.py`
- Test: `tests/unit/test_preflight_entrypoint.py`

**Step 1: Narrow function signatures**

Update:
- `run_preflight_entry(...)`
- `_load_prepared_config(...)`

to accept only `concept_text` besides `run_id`.

**Step 2: Remove audio brief file persistence**

Delete logic that writes:
- `audio_brief.txt`
- `audio_hook_brief.txt`

Keep only concept text persistence.

**Step 3: Rewrite tests**

Update `tests/unit/test_preflight_entrypoint.py` so it verifies only the single canonical input path.

Suggested replacement direction:

```python
def test_prepare_run_brief_writes_only_concept_text(monkeypatch, tmp_path):
    ...
    rid = entry._prepare_run_brief({"concept_text": "night drive"}, "run-123")
    assert (state_dir / "concept_text.txt").exists()
    assert not (state_dir / "audio_brief.txt").exists()
```

**Step 4: Run focused tests**

Run:
`uv run pytest tests/unit/test_preflight_entrypoint.py -q`

Expected:
- PASS

---

## Task 6: Rewrite README to match the real product

**Objective:** Make the repo’s first impression truthful.

**Files:**
- Modify: `README.md`

**Step 1: Remove outdated concepts**

Delete or replace mentions of:
- old stage list (`storyboard`, `keyframes`, `wan_interpolation`, etc.)
- `profiles/`
- `profiles/director_brief_example.yaml`
- `ai-mv start --brief ...`
- `ai-mv preflight --brief ...`

**Step 2: Replace with canonical description**

README should now describe:
- multi-style MV platform
- `concept_text`-first UX
- music generation + visual generation + review flow
- WSL wrapper usage still allowed
- final MV as the main target

Suggested high-level sections:
1. What ai-mv is
2. Current pipeline
3. Core requirements
4. Quickstart
5. WSL usage
6. Tests

**Step 3: Add truthful commands**

Recommended command examples:

```bash
ai-mv doctor
ai-mv preflight --concept-text "dreamy synthwave night drive with lonely neon romance"
ai-mv start --concept-text "dreamy synthwave night drive with lonely neon romance"
ai-mv status --run-id 20260406-215500
```

**Step 4: Optional note on internal complexity**

It is okay to say the external UX is simple even if internal planning uses deeper workflow/LLM logic.

---

## Task 7: Run focused regression checks for Wave 1

**Objective:** Verify the contract you intentionally changed.

**Files:**
- Test only

**Step 1: Run focused Wave 1 tests**

Run:
`uv run pytest tests/unit/test_cli_args.py tests/unit/test_start_entrypoint.py tests/unit/test_preflight_entrypoint.py -q`

Expected:
- all pass

**Step 2: Run nearby command-path tests**

Run:
`uv run pytest tests/unit/test_cli_app.py tests/unit/test_pipeline.py -q`

Expected:
- pass, unless there are unrelated pre-existing failures

**Step 3: Run full suite**

Run:
`uv run pytest -q`

Expected:
- discover any follow-on failures caused by removed legacy paths
- if unrelated historical failures remain, record them clearly rather than hiding them

---

## Task 8: Cleanup and commit

**Objective:** Finish Wave 1 as a coherent, reviewable change set.

**Files:**
- All modified files from this plan

**Step 1: Review changed files for charter alignment**

Checklist:
- [ ] no public `--brief`
- [ ] no public `audio_brief` flags
- [ ] no `legacy_brief` fallback
- [ ] README no longer lies about profiles
- [ ] tests protect the new contract

**Step 2: Commit**

Suggested commit:

```bash
git add README.md \
  src/ai_mv/cli/args.py \
  src/ai_mv/cli/commands.py \
  src/ai_mv/entrypoints/start.py \
  src/ai_mv/entrypoints/preflight.py \
  tests/unit/test_cli_args.py \
  tests/unit/test_start_entrypoint.py \
  tests/unit/test_preflight_entrypoint.py

git commit -m "refactor: make concept_text the only public input contract"
```

---

## Risks and Notes

### Risk 1: Internal code still references audio brief values
Even if public entrypoints stop exposing them, lower layers may still contain dormant assumptions.

Mitigation:
- keep Wave 1 focused on the public contract
- let full-suite tests reveal downstream coupling
- handle deeper cleanup in later waves

### Risk 2: README may overpromise multi-style support immediately
Mitigation:
- describe the target honestly without claiming every style is already production-ready
- phrase it as a multi-style platform under active refactor, not a fully finished universal generator

### Risk 3: removing flags may feel abrupt
Mitigation:
- acceptable here because the project is for personal use and the charter explicitly prefers deletion over compatibility preservation

---

## What Wave 1 Does Not Solve

Wave 1 does not:
- extract citypop-specific logic from `core`
- introduce `styles/`
- improve review quality
- refactor giant planning files
- fix all architecture problems

Wave 1 only makes the product truthful at the top level.
That is the necessary first move before deeper structural work.

---

## Next Recommended Wave

After Wave 1 is merged, proceed immediately to Wave 2:
- create `styles/citypop/`
- split `plan_citypop_mv.py`
- move embedded citypop worldview/constants out of shared layers
- start generic planning interfaces in `core/planning/`

This sequence preserves momentum: first fix the product contract, then fix the architecture behind it.
