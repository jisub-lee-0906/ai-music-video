from __future__ import annotations

from .bible import get_j_rock_bible


def lane_match_signals() -> dict:
    bible = get_j_rock_bible()
    return {
        "style_lane": "j_rock",
        "style": str(bible.get("style", "")).strip(),
        "style_aliases": list(bible.get("style_aliases", [])),
        "motifs": list(bible.get("motifs", [])),
        "camera_rules": list(bible.get("camera_rules", [])),
        "negative_rules": list(bible.get("negative_rules", [])),
    }
