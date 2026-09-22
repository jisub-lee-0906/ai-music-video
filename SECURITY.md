# Security

## Source publication is not service deployment

This project is a trusted local CLI/orchestrator. Publishing its source does not turn it into a multi-user internet service.

- Explicit CLI configuration of the Codex executable, ComfyUI host, workflows, and local media paths is intentional. The user who supplies that configuration is inside the local trust boundary.
- Do not accept those trusted configuration values unchanged from anonymous web requests or untrusted queue jobs.
- ComfyUI HTTP redirects are rejected. The configured initial host is still checked by the local Comfy configuration validator.
- Failure diagnostics retain useful traceback and path context, but recognized credential patterns are redacted before state artifacts are written.
- Generated artifacts and reports may contain prompts, media metadata, and local paths. Review them before publication.

A future hosted service needs a separate threat model, tenant isolation, authenticated job submission, and server-owned configuration.
