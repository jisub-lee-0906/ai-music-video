# Architecture

- CLI entrypoint dispatches run/doctor/status.
- Core pipeline runs stage registry in deterministic order.
- Engines map stage inputs to ComfyUI workflow node patches.
- Infra wraps ComfyUI/Ollama + retry/timeout policies.
- Artifacts persist run state, summary, manifest, and dashboard.
