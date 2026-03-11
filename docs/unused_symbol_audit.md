# Unused Symbol Audit

This audit was performed to remove clear dead code before the next planner pass and to avoid deleting dynamic entrypoints by mistake.

## Removed

- `ai_mv.infra.http_retry.with_retry`
  - No remaining references in `src` or `tests`
  - No registry, runner, or CLI entrypoint role

## Keep / not dead by design

- Runner `required_inputs()` helpers
  - Used by workflow patching and runtime preflight
- CLI entrypoints and command dispatch
  - Reached through command-line invocation
- Stage registry and scheduler helpers
  - Reached through orchestration, not only direct imports
- Private planner formatting helpers
  - Narrow call sites but part of stable prompt construction

## Audit rule

Only symbols with both conditions are removed:

1. No references in `src` or `tests`
2. No dynamic entrypoint, registry, mapper, runner, or contract role
