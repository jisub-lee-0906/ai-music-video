from __future__ import annotations


def latest_success_eligible(state: dict, payload: dict) -> bool:
    status = str(state.get("status", "")).strip()
    if status != "done":
        return False
    scope = str(state.get("scope", "run")).strip().lower()
    if scope == "preflight":
        return True
    final_video = str(payload.get("final_video", "")).strip()
    music_file = str(payload.get("music_file", "")).strip()
    return bool(final_video and music_file)
