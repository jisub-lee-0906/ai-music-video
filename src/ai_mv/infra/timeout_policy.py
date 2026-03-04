def resolve_timeout(config: dict) -> int:
    limits = config.get("limits", {})
    return int(limits.get("timeout_seconds", 180))

