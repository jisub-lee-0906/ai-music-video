def resolve_timeout(config: dict) -> int:
    return int(config["limits"]["timeout_seconds"])
