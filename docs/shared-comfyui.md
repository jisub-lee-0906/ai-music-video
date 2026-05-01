# Shared Windows ComfyUI for Krita, Blender, and ai-music-video

This repo is designed to treat Windows ComfyUI as one shared generation backend.
Krita, Blender, and the WSL ai-music-video pipeline should all point at the same backend queue instead of launching separate ComfyUI servers.

## Canonical setup

We use the ComfyUI Desktop app as the canonical owner because it is the most visible and least confusing control surface.

Use exactly one Desktop-owned ComfyUI backend:

- Start ComfyUI from the Windows ComfyUI Desktop app.
- The Desktop app should own the Python backend process.
- Closing the Desktop app should also stop the backend it launched.
- Do not separately launch `python main.py` from WSL/PowerShell for everyday use.

Endpoints:
- Windows local clients:
  - `http://127.0.0.1:8000`
- WSL ai-music-video:
  - `http://<WSL gateway>:8000`
  - usually `http://172.28.224.1:8000`
- ComfyUI backend bind:
  - `--listen 0.0.0.0 --port 8000`

Recommended client mapping:

| Client | Endpoint |
| --- | --- |
| Krita AI Diffusion | `http://127.0.0.1:8000` |
| Blender ComfyUI addon | `http://127.0.0.1:8000` |
| ai-music-video from WSL | `http://<WSL gateway>:8000` |

Do not intentionally use port `8001` or `8002` for one of these clients unless you are deliberately running a separate isolated ComfyUI instance.

## Why duplicate backends happen

A common failure mode is:

1. A ComfyUI backend is started from WSL/PowerShell on `0.0.0.0:8000`.
2. The Windows ComfyUI Desktop app is opened later.
3. The Desktop app tries to start its own backend, sees that `8000` is already taken, and starts a second backend on `8001`.
4. Both backends use the same `Documents/ComfyUI/user/comfyui.db`.
5. The second backend logs a database lock warning such as:

```text
Could not acquire lock on database 'C:/Users/Desktop/Documents/ComfyUI/user/comfyui.db'.
Another ComfyUI process may already be using it.
```

This is not a normal "frontend + backend" split. `ComfyUI.exe` is the Desktop frontend shell, but `python.exe main.py --port 8000` and `python.exe main.py --port 8001` are two separate backend servers.

## Guard added for WSL wrappers

The WSL wrappers now run a duplicate-backend guard before using ComfyUI.

Affected wrappers include anything that sources `scripts/lib/wsl-env.sh`, such as:

```bash
./scripts/doctor-wsl.sh
./scripts/preflight-wsl.sh --concept-text '...'
./scripts/start-wsl.sh --concept-text '...'
```

There is also a standalone diagnostic command:

```bash
./scripts/check-shared-comfy-wsl.sh
```

If more than one Windows ComfyUI backend is listening on common ports (`8000`, `8001`, `8002`, `8188`), the guard fails fast and prints the detected ports/PIDs. This prevents ai-music-video from silently using one backend while the Desktop frontend, Krita, or Blender looks at another.

By default the guard also requires the single canonical backend on port `8000` to be owned by the ComfyUI Desktop app. If port `8000` is held by a manual WSL/PowerShell-launched `python main.py`, the guard fails with exit `44` and asks you to stop that backend before launching Desktop.

Advanced diagnostic override for non-Desktop ownership:

```bash
AI_MV_SHARED_COMFY_OWNER_MODE=any ./scripts/check-shared-comfy-wsl.sh
```

Use `AI_MV_SHARED_COMFY_OWNER_MODE=any` only when intentionally debugging or temporarily running a manual backend.

Temporary diagnostic bypass:

```bash
AI_MV_SKIP_SHARED_COMFY_GUARD=1 ./scripts/doctor-wsl.sh
```

Only use the bypass when deliberately inspecting a broken state. Do not use it for normal generation.

## Safe operating rule

For everyday use:

1. Keep only one ComfyUI backend alive.
2. Prefer canonical port `8000`.
3. Point Krita and Blender to `127.0.0.1:8000`.
4. Point ai-music-video to the WSL gateway on port `8000`.
5. Do not let ai-music-video clear or interrupt the queue by default.
6. Run only one heavy generation job at a time; let the shared ComfyUI queue serialize work.

The ai-music-video runtime defaults are shared-server safe:

- `interrupt_comfy_before_start = false`
- `clear_comfy_queue_before_start = false`

If the queue is already busy, ai-music-video should fail fast rather than killing a Krita or Blender job.

## If the guard reports duplicate backends

Recommended manual cleanup for the Desktop-canonical setup:

1. Finish or cancel any active generation job.
2. Fully exit the ComfyUI Desktop app, including tray/background processes.
3. Stop any remaining manual/WSL/PowerShell `python.exe main.py` backend processes.
4. Start ComfyUI from the Windows ComfyUI Desktop app only.
5. Re-run:

```bash
./scripts/check-shared-comfy-wsl.sh
```

Expected result:

```text
[shared-comfy] OK: exactly one canonical Desktop-owned ComfyUI backend may be used on port 8000.
```

## Current preferred architecture

ComfyUI is the shared backend. The frontend is only a UI/monitoring surface.

```text
Windows ComfyUI Desktop app
  └─ Desktop-owned backend : 0.0.0.0:8000
      ├─ ComfyUI Desktop frontend
      ├─ Krita AI Diffusion
      ├─ Blender ComfyUI addon
      └─ WSL ai-music-video pipeline
```

Generated media should remain grouped under the Windows ComfyUI output tree:

```text
C:\Users\Desktop\Documents\ComfyUI\output\ai_mv\runs\<run_id>\
  audio\
  stills\
  clips\
  final\
```

Pipeline metadata should remain in the repo:

```text
artifacts/runs/<run_id>/
.analysis/latest-validation-<run_id>/
```
