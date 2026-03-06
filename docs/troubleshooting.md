# Troubleshooting

- `ModuleNotFoundError`: install editable package `pip install -e .`
- `ai-mv doctor` fails on ComfyUI: confirm `integrations.comfyui_base_url` points to localhost and `comfyui_input_dir`/`comfyui_output_dir` exist.
- `ai-mv doctor` fails on Ollama: confirm `integrations.ollama_model` exists in `ollama list`.
- Missing workflow template: confirm the four exported ComfyUI API JSON files exist under `integrations.workflows_dir`.
- `ffmpeg` or `ffprobe` missing: install them and make sure both commands resolve on `PATH`.
- Comfy timeout: raise `limits.timeout_seconds` or inspect Comfy logs.
- Ollama JSON/schema failure: inspect the failing planner output; the pipeline now stops immediately on invalid structured output.
