from __future__ import annotations

def visual_pipeline_settings(config: dict) -> dict:
    node = config.get("visual_pipeline", {}) if isinstance(config, dict) else {}
    node = node if isinstance(node, dict) else {}
    policy = node.get("visual_policy", {}) if isinstance(node.get("visual_policy", {}), dict) else {}
    mode = str(node.get("visual_pipeline_mode", "tti_selective_ref")).strip().lower()
    if mode not in {"tti_only", "tti_selective_ref", "tti_ref_all"}:
        mode = "tti_selective_ref"
    consistency = str(node.get("consistency_mode", "")).strip().lower()
    if consistency not in {"off", "selective", "always"}:
        consistency = "selective"
    kinetic_ref_mode = str(node.get("kinetic_ref_mode", "endpoints")).strip().lower()
    if kinetic_ref_mode not in {"all", "endpoints", "hero_only", "off"}:
        kinetic_ref_mode = "endpoints"
    hero_types = node.get("hero_shot_types", policy.get("hero_shot_types", ["EMOTION_CLOSE"]))
    sections = node.get("reference_priority_sections", policy.get("priority_sections", ["Final Chorus", "Chorus 2", "Chorus 1"]))
    location_budget = node.get("location_budget", {}) if isinstance(node.get("location_budget", {}), dict) else {}
    location_examples = node.get("location_family_examples", ["reflective walkway", "lit passage", "open lane", "sheltered edge"])
    shot_guidance = node.get("shot_type_guidance", {}) if isinstance(node.get("shot_type_guidance", {}), dict) else {}
    grammar = node.get("mv_grammar", {}) if isinstance(node.get("mv_grammar", {}), dict) else {}
    return {
        "visual_pipeline_mode": mode,
        "consistency_mode": consistency,
        "kinetic_ref_mode": kinetic_ref_mode,
        "resolved_visual_policy": dict(policy),
        "hero_shot_types": [str(x).strip().upper() for x in hero_types if str(x).strip()],
        "reference_priority_sections": [str(x).strip().lower() for x in sections if str(x).strip()],
        "allow_face_drift_in_nonhero": bool(node.get("allow_face_drift_in_nonhero", True)),
        "location_budget": {
            "min": max(1, int(location_budget.get("min", 2))),
            "max": max(1, int(location_budget.get("max", 3))),
        },
        "location_family_examples": [str(x).strip() for x in location_examples if str(x).strip()],
        "shot_type_guidance": {
            str(key).strip().lower(): [str(x).strip().upper() for x in value if str(x).strip()]
            for key, value in shot_guidance.items()
            if str(key).strip() and isinstance(value, list)
        },
        "mv_grammar": {
            "verse_coverage_bias": str(grammar.get("verse_coverage_bias", "travel coverage")).strip(),
            "chorus_payoff_bias": str(grammar.get("chorus_payoff_bias", "clear hero payoff")).strip(),
            "bridge_interrupt_bias": str(grammar.get("bridge_interrupt_bias", "interrupted isolation")).strip(),
            "outro_residue_bias": str(grammar.get("outro_residue_bias", "residue image")).strip(),
        },
    }


def shot_type_guidance_digest(config: dict) -> str:
    settings = visual_pipeline_settings(config)
    guidance = settings.get("shot_type_guidance", {})
    order = ["intro", "verse", "pre_chorus", "chorus", "post_chorus", "bridge", "outro"]
    rows: list[str] = []
    for key in order:
        vals = guidance.get(key, [])
        if vals:
            rows.append(f"{key}={','.join(vals)}")
    return "; ".join(rows)


def location_grammar_digest(config: dict) -> str:
    settings = visual_pipeline_settings(config)
    budget = settings.get("location_budget", {"min": 2, "max": 3})
    examples = settings.get("location_family_examples", [])
    return (
        f"budget={budget.get('min', 2)}-{budget.get('max', 3)} recurring families; "
        f"examples={', '.join(examples)}"
    )


def build_mv_directives(config: dict) -> dict:
    mv = config.get("mv", {}) if isinstance(config, dict) else {}
    mv = mv if isinstance(mv, dict) else {}
    return {
        "motif_seed": str(mv.get("story_world", "")).strip(),
        "chorus_payoff_hint": str(mv.get("payoff_style", "")).strip(),
        "bridge_interrupt_hint": str(mv.get("action_vocabulary", "")).strip(),
        "outro_residue_hint": str(mv.get("outro_feel", "")).strip(),
    }
