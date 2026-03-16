from __future__ import annotations


DEFAULT_CONFIG: dict = {
    "audio": {
        "quality": "V0",
        "language": "en",
        "beats_per_bar": 4,
    },
    "profile": "",
    "video": {"target": "1920x1080@24"},
    "render": {
        "tti_size": "1280x720",
        "ref_size": "1024x576",
        "wan_size": "896x512",
        "wan_max_clip_sec": 5.0,
        "wan_planner_batch_size": 20,
        "flux2_ref_planner_batch_size": 4,
    },
    "visual_pipeline": {
        "visual_pipeline_mode": "tti_selective_ref",
        "consistency_mode": "selective",
        "hero_shot_types": ["EMOTION_CLOSE"],
        "reference_priority_sections": ["Final Chorus", "Chorus 2", "Chorus 1"],
        "allow_face_drift_in_nonhero": True,
        "location_budget": {"min": 2, "max": 3},
        "location_family_examples": [
            "reflective threshold",
            "lit passage",
            "open night lane",
            "sheltered edge",
        ],
        "shot_type_guidance": {
            "intro": ["CHAR_MASTER", "ENV_TRANSITION"],
            "verse": ["PERF_WIDE", "ENV_TRANSITION"],
            "pre_chorus": ["EMOTION_CLOSE", "PERF_WIDE"],
            "chorus": ["PERF_WIDE", "EMOTION_CLOSE"],
            "post_chorus": ["DETAIL_INSERT", "ENV_TRANSITION"],
            "bridge": ["EMOTION_CLOSE", "ENV_TRANSITION"],
            "outro": ["ENV_TRANSITION", "CHAR_MASTER"],
        },
        "mv_grammar": {
            "verse_coverage_bias": "travel coverage",
            "chorus_payoff_bias": "clear hero payoff",
            "bridge_interrupt_bias": "interrupted isolation",
            "outro_residue_bias": "residue image",
        },
    },
    "limits": {
        "timeout_seconds": 900,
    },
    "integrations": {
        "comfyui_base_url": "http://127.0.0.1:8188",
        "comfyui_input_dir": r"C:\Users\Desktop\Documents\ComfyUI\input",
        "comfyui_output_dir": r"C:\Users\Desktop\Documents\ComfyUI\output",
        "codex_cli_path": "",
        "codex_model": "gpt-5.4",
        "codex_timeout_structured_sec": 600,
        "workflows_dir": "workflows",
    },
    "runtime": {
        "template_hash_lock": False,
        "template_hashes": {},
    },
}


def default_config() -> dict:
    return _clone(DEFAULT_CONFIG)


def apply_defaults(config: dict) -> None:
    _deep_fill(config, DEFAULT_CONFIG)


def _deep_fill(target: dict, defaults: dict) -> None:
    for key, val in defaults.items():
        if key not in target:
            target[key] = _clone(val)
            continue
        if isinstance(val, dict) and isinstance(target.get(key), dict):
            _deep_fill(target[key], val)


def _clone(value):
    if isinstance(value, dict):
        return {k: _clone(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_clone(v) for v in value]
    return value
