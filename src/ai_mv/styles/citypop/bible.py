from __future__ import annotations


def get_citypop_bible() -> dict:
    return {
        "style": "japanese_citypop_80s_90s",
        "style_aliases": ["city pop", "citypop", "summer boulevard", "cassette romance", "ocean-blue dusk"],
        "palette": ["sunset amber", "ocean blue", "neon cyan", "sodium-vapor night"],
        "motifs": [
            "city lights",
            "glass reflections",
            "summer air",
            "film grain",
            "late train",
            "cassette glow",
            "quiet boulevard",
            "rooftop dusk",
        ],
        "wardrobe_rules": ["light summer jacket", "retro blouse", "silver accessories", "soft silhouette"],
        "camera_rules": ["restrained dolly", "soft lateral drift", "no aggressive handheld", "no hyper-cutting"],
        "negative_rules": [
            "k-pop look",
            "hard cyberpunk",
            "crowded multi-character shot",
            "club performance stage",
            "modern influencer aesthetic",
        ],
    }
