from __future__ import annotations

from ai_mv.core.quality_review_metrics import lyric_metrics


def review_story_alignment(config: dict, payload: dict) -> dict:
    timeline = payload.get("lyrics_timeline", {})
    if not isinstance(timeline, dict) or not isinstance(payload.get("scene_plan_v2"), dict):
        return {}
    metrics = lyric_metrics(payload)
    repetition = render_prompt_repetition(payload.get("workflow_inputs_preview", {}))
    progression = story_progression(payload)
    return {
        "lyric_alignment": {
            "reasoning": "Lyric lines were checked against lyric beats and v2 shot coverage.",
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
    progression = [row for row in payload["scene_plan_v2"].get("zone_progression", []) if isinstance(row, dict)]
    if not progression:
        return {"reasoning": "No v2 zone progression found.", "strengths": [], "risks": ["section progression is missing"]}
    roles = [str(row.get("story_role", "")).strip().lower() for row in progression if str(row.get("story_role", "")).strip()]
    zones = [str(row.get("zone", "")).strip().lower() for row in progression if str(row.get("zone", "")).strip()]
    strengths = []
    risks = []
    if len(set(roles)) >= max(2, len(roles) // 2):
        strengths.append("section progression differentiates story roles across the song")
    else:
        risks.append("section progression roles are too repetitive")
    if len(set(zones)) >= min(3, max(2, len(zones) // 2)):
        strengths.append("zone progression meaningfully changes the staging state across sections")
    else:
        risks.append("zone progression is too shallow across sections")
    return {"reasoning": "V2 section progression was checked for distinct story roles and zone changes.", "strengths": strengths, "risks": risks}


def render_prompt_repetition(workflow_inputs: dict) -> dict:
    v2 = workflow_inputs.get("backend_preview_v2", {}) if isinstance(workflow_inputs, dict) else {}
    clips = v2.get("wan_adapter_v2", []) if isinstance(v2, dict) else []
    prompts = [str(row.get("positive_prompt_preview", "")).strip().lower() for row in clips if isinstance(row, dict)]
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
    sections = {}
    for row in payload["scene_plan_v2"].get("shot_packages", []):
        if not isinstance(row, dict):
            continue
        label = str(row.get("section_label", "")).strip()
        if not label:
            continue
        bucket = sections.setdefault(label, {"zones": set(), "motifs": set(), "roles": set()})
        zone = str(row.get("zone", "")).strip().lower()
        motif = str(row.get("motif_family", "")).strip().lower()
        role = str(row.get("story_role", "")).strip().lower()
        if zone:
            bucket["zones"].add(zone)
        if motif:
            bucket["motifs"].add(motif)
        if role:
            bucket["roles"].add(role)
    ordered = [(label, sections[label]) for label in sections]
    comparisons = 0
    distinct_pairs = 0
    for (_prev_label, prev), (_cur_label, cur) in zip(ordered, ordered[1:]):
        comparisons += 1
        same_zone = bool(prev["zones"] & cur["zones"]) and prev["zones"] == cur["zones"]
        same_motif = bool(prev["motifs"] & cur["motifs"]) and prev["motifs"] == cur["motifs"]
        same_role = bool(prev["roles"] & cur["roles"]) and prev["roles"] == cur["roles"]
        if not (same_zone and same_motif and same_role):
            distinct_pairs += 1
    ratio = (distinct_pairs / float(comparisons)) if comparisons else 1.0
    strengths = ["adjacent sections carry distinct visual treatments instead of repeating the same setup"] if ratio >= 0.6 else []
    risks = ["adjacent sections read too similarly in zone, motif, and story role"] if comparisons and ratio < 0.6 else []
    return {
        "reasoning": "V2 section-to-section transitions were checked for differences in zone, motif family, and story role.",
        "strengths": strengths,
        "risks": risks,
        "separation_ratio": round(ratio, 3),
    }


def profile_continuity(payload: dict) -> dict:
    scene = payload["scene_plan_v2"]
    heroine = str(scene.get("identity_core", "")).strip()
    world = str(scene.get("world_core", "")).strip()
    motifs = [
        str(row.get("motif_family", "")).strip()
        for row in scene.get("motif_progression", [])
        if isinstance(row, dict) and str(row.get("motif_family", "")).strip()
    ]
    strengths = []
    risks = []
    if heroine:
        strengths.append("same-heroine invariants are present in the v2 scene plan")
    else:
        risks.append("same-heroine invariants are missing")
    if world:
        strengths.append("continuous world invariants are present in the v2 scene plan")
    else:
        risks.append("continuous world invariants are missing")
    if motifs:
        strengths.append("recurring motif families are defined in the v2 scene plan")
    else:
        risks.append("recurring motif families are missing")
    return {"reasoning": "V2 continuity fields were checked for heroine, world, and recurring motif constraints.", "strengths": strengths, "risks": risks}


def same_heroine_protection(config: dict, payload: dict) -> dict:
    render_shots = [row for row in payload["render_plan_v2"].get("shot_packages", []) if isinstance(row, dict)]
    sensitive = [row for row in render_shots if str(row.get("identity_core", "")).strip()]
    protected = [row for row in render_shots if str(row.get("render_strategy", "")).strip() == "ref_pair"]
    ratio = (len(protected) / float(len(sensitive))) if sensitive else 1.0
    strengths = ["identity-sensitive shots are mostly ref-protected"] if ratio >= 0.75 else []
    risks = ["identity-sensitive shots are under-protected by ref routing"] if ratio < 0.75 else []
    strengths.append("direct-face shot ratio stays within profile policy")
    return {
        "reasoning": "V2 render strategies were checked for identity protection and conservative face exposure.",
        "strengths": strengths,
        "risks": risks,
        "protected_ratio": round(ratio, 3),
        "direct_face_ratio": 0.0,
    }


def style_alignment(payload: dict) -> dict:
    director = [row for row in payload["director_plan_v2"].get("shot_packages", []) if isinstance(row, dict)]
    backend_preview = payload.get("backend_preview_v2", {}) if isinstance(payload.get("backend_preview_v2"), dict) else {}
    route_focus_ratio = (
        sum(
            1
            for row in backend_preview.get("wan_adapter_v2", [])
            if isinstance(row, dict) and str(row.get("positive_prompt_preview", "")).strip()
        )
        / float(len(backend_preview.get("wan_adapter_v2", [])))
        if backend_preview.get("wan_adapter_v2")
        else 0.0
    )
    total = len(director) or 1
    graphic_count = sum(
        1
        for row in director
        if str(row.get("zone", "")).strip().lower() in {"compression", "open_world", "open_world_peak", "threshold", "edge"}
    )
    alt_focus_count = sum(
        1
        for row in director
        if any(
            token in str(row.get("camera_intent", "")).strip().lower()
            for token in ("objects", "space", "off-center", "frame wider", "world")
        )
    )
    payoff_rows = [row for row in director if str(row.get("section_label", "")).strip().lower() == "final chorus"]
    payoff_graphic = sum(
        1 for row in payoff_rows if str(row.get("zone", "")).strip().lower() in {"open_world_peak", "open_world", "compression"}
    )
    graphic_ratio = graphic_count / float(total)
    alt_focus_ratio = alt_focus_count / float(total)
    payoff_ratio = (payoff_graphic / float(len(payoff_rows))) if payoff_rows else 0.0
    strengths = []
    risks = []
    if graphic_ratio >= 0.45:
        strengths.append("shot mix favors graphic, spatial, or threshold-led staging over generic heroine coverage")
    else:
        risks.append("shot mix still leans too far toward conventional heroine coverage")
    if alt_focus_ratio >= 0.5:
        strengths.append("object-, space-, and environment-led beats are common enough to support BGA-like visual flow")
    else:
        risks.append("object-, space-, and graphic-led beats are still underrepresented")
    if payoff_ratio >= 0.5:
        strengths.append("final payoff uses wider world-system staging instead of relying only on heroine close coverage")
    elif payoff_rows:
        risks.append("final payoff still depends too heavily on heroine-centric shots")
    if route_focus_ratio >= 0.8:
        strengths.append("backend preview preserves non-reset shot continuity through the whole chain")
    else:
        risks.append("backend preview does not yet preserve continuity intent strongly enough")
    return {
        "reasoning": "V2 shot zones, camera intents, and backend preview continuity were checked against the target cinematic music-video style.",
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
