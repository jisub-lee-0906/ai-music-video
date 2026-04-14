# ai-mv WSL Realistic Goals and Optimization Plan

> For Hermes: Use subagent-driven-development skill to implement this plan task-by-task.

Goal: Make ai-mv reliably runnable from WSL against a Windows-hosted ComfyUI setup, with a realistic first-success target that favors short stylized outputs over full automation.

Architecture: Keep the existing Python orchestration and ComfyUI workflow structure, but reduce failure surface in three places: configuration injection, preflight/start ergonomics, and realistic runtime defaults. Preserve the current Windows-capable path while making WSL operation explicit and repeatable. Favor small, test-backed changes over a deep rewrite.

Tech Stack: Python 3.11, ComfyUI, Codex CLI, ffmpeg/ffprobe, pytest, WSL, Windows-mounted ComfyUI directories.

---

## Realistic success targets

### Tier 1: Environment success

A run is considered environment-ready when all of the following are true:
- `./scripts/doctor-wsl.sh` exits 0
- `./scripts/preflight-wsl.sh --concept-text 'smoke test'` exits 0
- ComfyUI responds at the WSL gateway host
- Codex CLI is installed and logged in
- ComfyUI input/output directories are visible under `/mnt/c/...`

### Tier 2: First practical generation success

The first real generation target should be deliberately small:
- one short concept-text only run
- target music duration: 15–20 seconds
- `planning.enable_ia2v = false`
- `planning.enable_flf2v = false`
- still generation plus basic i2v only
- success means:
  - a run_id is created
  - pipeline completes without failed status
  - still outputs exist
  - clip outputs exist
  - final MV exists
  - review report does not mark the whole run failed

### Tier 3: Quality success

Do not use these as initial pass/fail blockers:
- perfect identity consistency across all shots
- perfect beat sync
- perfect lip sync
- long-form coherent narrative video
- fully automated production-quality song generation

Treat these as stretch goals after Tier 2 is stable.

---

## Why these goals are realistic

Current local/open tooling is strongest at:
- LLM-based planning
- still image generation
- short image-to-video clips
- ffmpeg assembly

Current local/open tooling is weakest at:
- polished local music generation
- exact audio-conditioned motion generation
- robust first/last-frame control across many shots
- long fully automated coherent MV generation

Therefore the project should optimize first for:
- short stylized MV outputs
- strong still anchors
- short clips
- human-in-the-loop rerendering

---

## Task 1: Lock in the practical first-run profile

Objective: Define the repo's official first-success target so debugging stays grounded.

Files:
- Modify: `README.md`
- Modify: `docs/first-run-checklist.md`
- Modify: `docs/sample-config.yaml`

Step 1: Document the first-success envelope
- Add a short "First successful WSL run" section.
- Specify:
  - 15–20 second target
  - `enable_ia2v=false`
  - `enable_flf2v=false`
  - concept-text driven run
  - WSL wrapper commands only

Step 2: Update sample config to reflect the intended first-success defaults
- Keep the sample config conservative.
- Do not enable advanced routing by default.

Step 3: Verify docs consistency
Run:
- `search_files(pattern='enable_ia2v|enable_flf2v|15~20초|15-20', path='docs', file_glob='*.md')`
Expected:
- docs consistently point to the same minimal first-run target

---

## Task 2: Remove duplicated WSL wrapper config logic

Objective: Reduce maintenance risk by centralizing WSL wrapper config injection.

Files:
- Create: `scripts/lib/wsl-env.sh`
- Modify: `scripts/doctor-wsl.sh`
- Modify: `scripts/preflight-wsl.sh`
- Modify: `scripts/start-wsl.sh`
- Test: `tests/unit/test_cli_args.py` or a new focused wrapper-adjacent test file if Python-side helper extraction occurs

Step 1: Extract common shell discovery logic
Move these into a shared shell helper:
- WSL detection
- gateway detection
- Comfy input/output path checks
- Codex path detection
- required binary checks

Step 2: Keep wrapper responsibilities small
- doctor wrapper should only set env and call doctor
- preflight wrapper should only set env and call preflight
- start wrapper should only set env and call start

Step 3: Verify wrappers still behave
Run:
- `./scripts/doctor-wsl.sh`
- `./scripts/preflight-wsl.sh --run-id wsl-wrapper-refactor-smoke --concept-text 'wrapper refactor smoke'`
Expected:
- both exit 0

---

## Task 3: Add a Python-side WSL config override helper

Objective: Stop monkeypatch-style wrapper logic from being the only path to safe WSL configuration.

Files:
- Create: `src/ai_mv/core/orchestration/wsl_overrides.py`
- Modify: `src/ai_mv/entrypoints/doctor.py`
- Modify: `src/ai_mv/entrypoints/preflight.py`
- Modify: `src/ai_mv/entrypoints/start.py`
- Test: `tests/unit/test_doctor_entrypoint.py`
- Test: new tests for the WSL override helper

Step 1: Write failing tests first
Add tests covering:
- WSL override leaves non-WSL config unchanged
- WSL override replaces Windows-style Comfy paths with `/mnt/c/...` paths when explicit environment overrides are provided
- WSL override preserves explicit user-provided values when already Linux-safe

Step 2: Implement a small helper
The helper should:
- detect WSL
- optionally read explicit env vars for gateway/input/output/codex path
- rewrite only the integration values needed for runtime safety
- avoid changing unrelated config

Step 3: Use helper inside entrypoints
- apply it just before doctor/preflight/start validation and execution
- keep the core orchestration unchanged

Step 4: Verify tests
Run:
- `pytest tests/unit/test_doctor_entrypoint.py -v`
- `pytest tests/unit -q`
Expected:
- pass without regressions

---

## Task 4: Add explicit config override CLI support

Objective: Make the project runnable from WSL without relying only on shell wrappers.

Files:
- Modify: `src/ai_mv/cli/args.py`
- Modify: `src/ai_mv/cli/commands.py`
- Modify: relevant entrypoint(s)
- Test: `tests/unit/test_cli_args.py`
- Test: `tests/unit/test_cli_app.py`

Step 1: Write failing parser tests
Add tests for new arguments such as:
- `--config`
- `--concept-text`
- optional explicit overrides for `comfyui-base-url`, `comfyui-input-dir`, `comfyui-output-dir`, `codex-cli-path`

Step 2: Implement minimal CLI wiring
- parser accepts the flags
- commands pass the values through
- entrypoints merge them into config before validation

Step 3: Keep wrappers even after this change
Wrappers remain the easiest path for the user, but the core CLI becomes less Windows-fixed.

Step 4: Verify parser and command tests
Run:
- `pytest tests/unit/test_cli_args.py tests/unit/test_cli_app.py -v`
Expected:
- pass

---

## Task 5: Add a safe smoke mode for start verification

Objective: Make full-run verification possible without immediately committing to the heaviest production path.

Files:
- Modify: planning/config defaults if needed
- Modify: start/preflight docs
- Possibly create: `scripts/start-wsl-smoke.sh`
- Test: one small integration or smoke test if practical

Step 1: Define smoke mode constraints
Smoke mode should enforce:
- 15–20 second audio target
- no ia2v
- no flf2v
- one simple concept text
- current workflow set only

Step 2: Expose a simple invocation path
Possible options:
- `./scripts/start-wsl.sh --concept-text '...'`
- or a dedicated `start-wsl-smoke.sh`

Step 3: Verification checklist for a real smoke run
A successful smoke run should produce:
- run_id
- still files
- clip files
- final MV
- review artifact

---

## Task 6: Run the verification ladder

Objective: Prove the project works at increasing confidence levels.

Files:
- No code changes required
- Capture findings in docs if issues are found

Step 1: Environment verification
Run:
- `./scripts/doctor-wsl.sh`
Expected:
- `comfyui=True codex=True`

Step 2: Preflight verification
Run:
- `./scripts/preflight-wsl.sh --run-id wsl-preflight-final --concept-text 'Japanese 80s city pop night drive, neon coast, bittersweet summer romance'`
Expected:
- `status=done`

Step 3: Full smoke run verification
Run:
- `./scripts/start-wsl.sh --run-id wsl-start-smoke --concept-text 'Japanese 80s city pop night drive, neon coast, bittersweet summer romance'`
Expected:
- final status is not failed
- output artifacts exist

Step 4: Artifact verification
Check:
- `artifacts/runs/<run_id>/...`
- final MV path
- review report contents
- any failure_reason in snapshot/status output

---

## Verification stance for future full runs

Yes: Hermes can verify a real full run after optimization.

Verification can include:
- environment readiness
- preflight success
- start command exit status
- produced file existence
- manifest / run summary / review report inspection
- snapshot failure_reason inspection
- ComfyUI queue/HTTP health during the run

Limits:
- generation quality is only partially automatable
- Hermes can verify whether outputs were produced and whether obvious failure states occurred
- Hermes can also do a first-pass artifact review, but cinematic quality remains partly subjective

---

## Immediate execution recommendation

Start with Tasks 1–3 only.

Why:
- they have the highest reliability payoff
- they reduce wrapper fragility
- they keep the project grounded in a realistic first-success target
- they make later full-run verification much safer
