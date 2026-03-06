# Operations

- Start: `ai-mv start --config configs/default.yaml`
- Health check: `ai-mv doctor --config configs/default.yaml`
- Status: `ai-mv status --run-id <run_id>`
- Outputs: `artifacts/runs_state/<run_id>`
- Doctor requires local ComfyUI paths, configured Ollama model, workflow templates, `ffmpeg`, and `ffprobe`.
