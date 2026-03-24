from __future__ import annotations

from ai_mv.core.quality_review_metrics import beat_to_section_label, canonical_section_label, lyric_metrics


def review_story_alignment(config: dict, payload: dict) -> dict:
    timeline = payload.get("lyrics_timeline", {})
    story_bible = payload.get("visual_story_bible", {})
    shot_timeline = payload.get("shot_timeline", {})
    workflow_inputs = payload.get("workflow_inputs_preview", {})
    if not isinstance(timeline, dict) or not isinstance(story_bible, dict) or not isinstance(shot_timeline, dict):
        return {}
    metrics = lyric_metrics(payload)
    repetition = render_prompt_repetition(workflow_inputs)
    progression = story_progression(payload)
    return {
        "lyric_alignment": {
            "reasoning": "Lyric lines were checked against lyric beats and shot assignments.",
            "strengths": [f"shot coverage maps {metrics['covered_beat_count']} lyric beats"],
            "risks": [f"{metrics['unmapped_lyric_lines']} lyric lines are unmapped"] if metrics["unmapped_lyric_lines"] else [],
        },
        "repeat_variation": {
            "reasoning": "Repeated hook and chorus line reuse was checked for changed visual treatment.",
            "strengths": ["repeated hooks have some visual variation"] if metrics["repeated_hook_variation"] >= 0.5 else [],
            "risks": ["repeated hooks collapse into near-identical visual beats"] if metrics["repeated_hook_variation"] < 0.5 else [],
        },
        "story_progression": progression,
        "section_visual_separation": section_visual_separation(payload),
        "render_prompt_repetition": repetition,
        "profile_continuity": profile_continuity(payload),
        "same_heroine_protection": same_heroine_protection(config, payload),
        "style_alignment": style_alignment(payload),
    }


def story_progression(payload: dict) -> dict:
    progression = payload.get("visual_story_bible", {}).get("section_progression", [])
    if not progression:
        return {"reasoning": "No section progression found.", "strengths": [], "risks": ["section progression is missing"]}
    functions = [str(row.get("story_function", "")).strip().lower() for row in progression if isinstance(row, dict)]
    strengths = []
    risks = []
    if len(set(functions)) >= max(2, len(functions) // 2):
        strengths.append("section progression differentiates story functions across the song")
    else:
        risks.append("section progression functions are too repetitive")
    return {"reasoning": "Section progression was checked for distinct narrative roles.", "strengths": strengths, "risks": risks}


def render_prompt_repetition(workflow_inputs: dict) -> dict:
    wan = workflow_inputs.get("wan_interpolation", {}) if isinstance(workflow_inputs, dict) else {}
    clips = wan.get("clips", []) if isinstance(wan, dict) else []
    prompts = [str(row.get("positive_prompt", "")).strip().lower() for row in clips if isinstance(row, dict)]
    unique = len(set(prompts))
    ratio = (unique / len(prompts)) if prompts else 1.0
    strengths = ["render-facing prompts preserve clip-to-clip differences"] if ratio >= 0.7 else []
    risks = ["render-facing wan prompts repeat too aggressively across clips"] if prompts and ratio < 0.7 else []
    return {
        "reasoning": "WAN positive prompts were compared for repeated text.",
        "strengths": strengths,
        "risks": risks,
        "distinct_ratio": round(ratio, 3),
    }


def section_visual_separation(payload: dict) -> dict:
    story = payload.get("visual_story_bible", {}) if isinstance(payload, dict) else {}
    timeline = payload.get("lyrics_timeline", {}) if isinstance(payload, dict) else {}
    beat_map = {
        str(beat.get("beat_id", "")).strip(): beat
        for beat in story.get("lyric_beats", [])
        if isinstance(beat, dict)
    }
    sections = [row for row in timeline.get("sections", []) if isinstance(row, dict)]
    signatures: list[tuple[set[str], set[str], set[str]]] = []
    for section in sections:
        beats = []
        for beat in section.get("lyric_beats", []):
            if not isinstance(beat, dict):
                continue
            story_beat = beat_map.get(str(beat.get("beat_id", "")).strip())
            if isinstance(story_beat, dict):
                beats.append(story_beat)
        if not beats:
            continue
        signatures.append(
            (
                {str(row.get("location_family", "")).strip().lower() for row in beats if str(row.get("location_family", "")).strip()},
                {str(row.get("palette_hint", "")).strip().lower() for row in beats if str(row.get("palette_hint", "")).strip()},
                {str(row.get("visible_action", "")).strip().lower() for row in beats if str(row.get("visible_action", "")).strip()},
            )
        )
    comparisons = 0
    distinct_pairs = 0
    for prev, cur in zip(signatures, signatures[1:]):
        comparisons += 1
        same_location = bool(prev[0] & cur[0]) and prev[0] == cur[0]
        same_palette = bool(prev[1] & cur[1]) and prev[1] == cur[1]
        same_action = bool(prev[2] & cur[2]) and prev[2] == cur[2]
        if not (same_location and same_palette and same_action):
            distinct_pairs += 1
    ratio = (distinct_pairs / float(comparisons)) if comparisons else 1.0
    strengths = ["adjacent sections carry distinct visual treatments instead of repeating the same setup"] if ratio >= 0.6 else []
    risks = ["adjacent sections read too similarly in location, palette, and action treatment"] if comparisons and ratio < 0.6 else []
    return {
        "reasoning": "Section-to-section transitions were checked for differences in location, palette, and action treatment.",
        "strengths": strengths,
        "risks": risks,
        "separation_ratio": round(ratio, 3),
    }


def profile_continuity(payload: dict) -> dict:
    story = payload.get("visual_story_bible", {}) if isinstance(payload, dict) else {}
    heroine = str(story.get("heroine_invariants", story.get("hero_identity_lock", ""))).strip()
    world = str(story.get("world_invariants", story.get("world_rules", ""))).strip()
    locations = [str(x).strip() for x in story.get("location_family_rules", story.get("recurring_location_families", [])) if str(x).strip()]
    strengths = []
    risks = []
    if heroine:
        strengths.append("same-heroine invariants are present in the story bible")
    else:
        risks.append("same-heroine invariants are missing")
    if world:
        strengths.append("continuous world invariants are present")
    else:
        risks.append("continuous world invariants are missing")
    if locations:
        strengths.append("recurring location families are defined")
    else:
        risks.append("recurring location families are missing")
    return {"reasoning": "Profile continuity fields were checked for heroine, world, and recurring location constraints.", "strengths": strengths, "risks": risks}


def same_heroine_protection(config: dict, payload: dict) -> dict:
    routes = [row for row in payload.get("clip_routes", []) if isinstance(row, dict)]
    policy = {}
    profile_intent = payload.get("profile_intent", {})
    if isinstance(profile_intent, dict):
        policy = profile_intent.get("resolved_profile_policy", {})
    max_direct_face_ratio = 0.2
    if isinstance(policy, dict):
        try:
            max_direct_face_ratio = float(policy.get("max_direct_face_ratio", 0.2))
        except Exception:
            max_direct_face_ratio = 0.2
    sensitive = [
        row
        for row in routes
        if str(row.get("face_exposure_level", "")).strip().lower() in {"direct", "soft"}
        or str(row.get("continuity_priority", "")).strip().lower() == "high"
    ]
    protected = [row for row in sensitive if bool(row.get("use_ref", False))]
    ratio = (len(protected) / float(len(sensitive))) if sensitive else 1.0
    direct_face = [row for row in routes if str(row.get("face_exposure_level", "")).strip().lower() == "direct"]
    direct_face_ratio = (len(direct_face) / float(len(routes))) if routes else 0.0
    strengths = ["identity-sensitive shots are mostly ref-protected"] if ratio >= 0.75 else []
    risks = ["identity-sensitive shots are under-protected by ref routing"] if ratio < 0.75 else []
    if direct_face_ratio <= max_direct_face_ratio:
        strengths.append("direct-face shot ratio stays within profile policy")
    else:
        risks.append("direct-face shot ratio exceeds profile policy")
    return {
        "reasoning": "Face-sensitive and high-continuity shots were checked for ref protection.",
        "strengths": strengths,
        "risks": risks,
        "protected_ratio": round(ratio, 3),
        "direct_face_ratio": round(direct_face_ratio, 3),
    }


def style_alignment(payload: dict) -> dict:
    shots = [row for row in payload.get("shot_timeline", {}).get("shots", []) if isinstance(row, dict)]
    routes = [row for row in payload.get("clip_routes", []) if isinstance(row, dict)]
    beat_map = beat_to_section_label(payload)
    total_shots = len(shots) or 1
    graphic_types = {"GRAPHIC_EVENT", "SYMBOLIC_INSERT", "WORLD_EVENT", "TRANSITIONAL_ABSTRACT", "RHYTHM_DETAIL"}
    graphic_count = sum(1 for row in shots if str(row.get("shot_type", "")).strip().upper() in graphic_types)
    alt_focus_count = sum(1 for row in shots if str(row.get("prompt_focus", "")).strip().lower() in {"object", "space", "graphic"})
    payoff_rows = [
        row
        for row in shots
        if canonical_section_label(
            str(row.get("section_label", row.get("section_name", ""))).strip(),
            str(row.get("lyric_beat_id", "")).strip(),
            beat_map,
        ).lower()
        == "final chorus"
    ]
    payoff_graphic = sum(1 for row in payoff_rows if str(row.get("shot_type", "")).strip().upper() in graphic_types)
    route_focus_ratio = (
        sum(1 for row in routes if str(row.get("prompt_focus", "")).strip().lower() in {"object", "space", "graphic"}) / float(len(routes))
        if routes
        else 0.0
    )
    graphic_ratio = graphic_count / float(total_shots)
    alt_focus_ratio = alt_focus_count / float(total_shots)
    payoff_ratio = (payoff_graphic / float(len(payoff_rows))) if payoff_rows else 0.0
    strengths = []
    risks = []
    if graphic_ratio >= 0.45:
        strengths.append("shot mix favors graphic and symbolic event types over generic heroine coverage")
    else:
        risks.append("shot mix still leans too far toward conventional heroine coverage")
    if alt_focus_ratio >= 0.5:
        strengths.append("object-, space-, and graphic-led beats are common enough to support BGA-like visual flow")
    else:
        risks.append("object-, space-, and graphic-led beats are still underrepresented")
    if payoff_ratio >= 0.5:
        strengths.append("final payoff uses graphic or world-system shots instead of relying only on face payoff")
    elif payoff_rows:
        risks.append("final payoff still depends too heavily on heroine-centric shots")
    if route_focus_ratio >= 0.5:
        strengths.append("route payload preserves non-heroine focus deep into render planning")
    else:
        risks.append("route payload collapses back toward heroine-first planning too often")
    return {
        "reasoning": "Shot types, prompt focus, and payoff composition were checked against the target 2D graphic MV style.",
        "strengths": strengths,
        "risks": risks,
        "graphic_event_ratio": round(graphic_ratio, 3),
        "non_heroine_focus_ratio": round(alt_focus_ratio, 3),
        "payoff_graphic_ratio": round(payoff_ratio, 3),
        "route_non_heroine_focus_ratio": round(route_focus_ratio, 3),
    }


def collect_strengths(story: dict) -> list[str]:
    out: list[str] = []
    for key in ("lyric_alignment", "repeat_variation", "story_progression", "section_visual_separation", "render_prompt_repetition", "profile_continuity", "same_heroine_protection", "style_alignment"):
        node = story.get(key, {})
        out.extend(str(x) for x in node.get("strengths", []) if str(x).strip())
    return out[:8] or ["lyric-first contracts are structurally present"]


def collect_risks(story: dict) -> list[str]:
    out: list[str] = []
    for key in ("lyric_alignment", "repeat_variation", "story_progression", "section_visual_separation", "render_prompt_repetition", "profile_continuity", "same_heroine_protection", "style_alignment"):
        node = story.get(key, {})
        out.extend(str(x) for x in node.get("risks", []) if str(x).strip())
    return out[:8] or ["no major lyric-story structural risk detected"]
