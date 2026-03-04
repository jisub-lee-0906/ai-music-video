# Troubleshooting

- `ModuleNotFoundError`: install editable package `pip install -e .`
- Missing refs: ensure `consistency.reference_images` files exist.
- Comfy timeout: raise `limits.timeout_seconds` or inspect Comfy logs.
- JSON invalid from Ollama: pipeline retries with repair prompt.
