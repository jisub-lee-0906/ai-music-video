def resolve_timeout(config: dict) -> int | None:
    try:
        value = int(config["limits"]["timeout_seconds"])
    except Exception:
        return None
    return None if value <= 0 else value
