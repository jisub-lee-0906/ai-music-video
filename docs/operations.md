# Operations

- Start: `ai-mv start --profile <profile>`
- Health check: `ai-mv doctor`
- Status: `ai-mv status --run-id <run_id>`
- Outputs: `artifacts/runs_state/<run_id>`
- Doctor requires local ComfyUI paths, configured Ollama model, workflow templates, `ffmpeg`, and `ffprobe`.
- Creative control should come from `configs/profiles/<name>.yaml`.
- Preferred profile fields are `audio.tags` and `style.guidance`.
- Manual lyrics/title/description inputs are not part of the normal runtime contract.
- Runtime flow is `acestep_music -> visual_bridge -> tti_anchor -> uso_chain -> wan_interpolation -> merge_mux`.
