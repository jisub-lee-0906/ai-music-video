from __future__ import annotations


def build_quality_review(config: dict, payload: dict) -> dict:
    review: dict = {}
    story = _review_story_alignment(config, payload)
    if story:
        review["lyric_alignment"] = story["lyric_alignment"]
        review["repeat_variation"] = story["repeat_variation"]
        review["story_progression"] = story["story_progression"]
        review["section_visual_separation"] = story["section_visual_separation"]
        review["render_prompt_repetition"] = story["render_prompt_repetition"]
        review["profile_continuity"] = story["profile_continuity"]
        review["same_heroine_protection"] = story["same_heroine_protection"]
        review["visual"] = {
            "reasoning": "Deterministic review inspected lyric alignment, repeat variation, section progression, section separation, render prompt reuse, and same-heroine continuity coverage.",
            "strengths": _collect_strengths(story),
            "risks": _collect_risks(story),
        }
    return review


def build_run_summary(state: dict, payload: dict, quality_review: dict) -> dict:
    audio_map = payload.get("audio_map", {}) if isinstance(payload, dict) else {}
    sections = audio_map.get("sections", []) if isinstance(audio_map, dict) else []
    labels = [str(x.get("label", x.get("name", ""))).strip() for x in sections if isinstance(x, dict)]
    songform = [str(x.get("name", "")).strip() for x in sections if isinstance(x, dict)]
    route_stats = _route_stats(payload.get("clip_routes", []), payload)
    lyric_metrics = _lyric_metrics(payload)
    return {
        "run_id": state["run_id"],
        "profile_name": str(payload.get("selected_profile", "")).strip(),
        "language": str(audio_map.get("language", "")).strip(),
        "selected_songform": songform,
        "selected_labels": labels,
        "tti_only_count": int(route_stats["tti_only_count"]),
        "ref_assisted_count": int(route_stats["ref_assisted_count"]),
        "ref_ratio_by_section": dict(route_stats["ref_ratio_by_section"]),
        "lyric_beat_count": int(lyric_metrics["lyric_beat_count"]),
        "shot_to_lyric_coverage": float(lyric_metrics["shot_to_lyric_coverage"]),
        "repeated_hook_variation": float(lyric_metrics["repeated_hook_variation"]),
        "unmapped_lyric_lines": int(lyric_metrics["unmapped_lyric_lines"]),
        "failure_reason": str(state.get("failure_reason", "")).strip(),
        "completed_stages": list(state.get("completed_stages", [])),
        "current_stage": str(state.get("current_stage", "")).strip(),
    }


def _review_story_alignment(config: dict, payload: dict) -> dict:
    timeline = payload.get("lyrics_timeline", {})
    story_bible = payload.get("visual_story_bible", {})
    shot_timeline = payload.get("shot_timeline", {})
    workflow_inputs = payload.get("workflow_inputs_preview", {})
    if not isinstance(timeline, dict) or not isinstance(story_bible, dict) or not isinstance(shot_timeline, dict):
        return {}
    lyric_metrics = _lyric_metrics(payload)
    repetition = _render_prompt_repetition(workflow_inputs)
    progression = _story_progression(payload)
    return {
        "lyric_alignment": {
            "reasoning": "Lyric lines were checked against lyric beats and shot assignments.",
            "strengths": [f"shot coverage maps {lyric_metrics['covered_beat_count']} lyric beats"],
            "risks": [f"{lyric_metrics['unmapped_lyric_lines']} lyric lines are unmapped"] if lyric_metrics["unmapped_lyric_lines"] else [],
        },
        "repeat_variation": {
            "reasoning": "Repeated hook and chorus line reuse was checked for changed visual treatment.",
            "strengths": ["repeated hooks have some visual variation"] if lyric_metrics["repeated_hook_variation"] >= 0.5 else [],
            "risks": ["repeated hooks collapse into near-identical visual beats"] if lyric_metrics["repeated_hook_variation"] < 0.5 else [],
        },
        "story_progression": progression,
        "section_visual_separation": _section_visual_separation(payload),
        "render_prompt_repetition": repetition,
        "profile_continuity": _profile_continuity(payload),
        "same_heroine_protection": _same_heroine_protection(config, payload),
    }


def _story_progression(payload: dict) -> dict:
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


def _render_prompt_repetition(workflow_inputs: dict) -> dict:
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


def _section_visual_separation(payload: dict) -> dict:
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


def _profile_continuity(payload: dict) -> dict:
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


def _same_heroine_protection(config: dict, payload: dict) -> dict:
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
    direct_face = [
        row for row in routes if str(row.get("face_exposure_level", "")).strip().lower() == "direct"
    ]
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


def _collect_strengths(story: dict) -> list[str]:
    out: list[str] = []
    for key in ("lyric_alignment", "repeat_variation", "story_progression", "section_visual_separation", "render_prompt_repetition", "profile_continuity", "same_heroine_protection"):
        node = story.get(key, {})
        out.extend(str(x) for x in node.get("strengths", []) if str(x).strip())
    return out[:8] or ["lyric-first contracts are structurally present"]


def _collect_risks(story: dict) -> list[str]:
    out: list[str] = []
    for key in ("lyric_alignment", "repeat_variation", "story_progression", "section_visual_separation", "render_prompt_repetition", "profile_continuity", "same_heroine_protection"):
        node = story.get(key, {})
        out.extend(str(x) for x in node.get("risks", []) if str(x).strip())
    return out[:8] or ["no major lyric-story structural risk detected"]


def _lyric_metrics(payload: dict) -> dict:
    timeline = payload.get("lyrics_timeline", {})
    shot_timeline = payload.get("shot_timeline", {})
    sections = [row for row in timeline.get("sections", []) if isinstance(row, dict)]
    shot_rows = [row for row in shot_timeline.get("shots", []) if isinstance(row, dict)]
    shot_beat_ids = {str(row.get("lyric_beat_id", "")).strip() for row in shot_rows if str(row.get("lyric_beat_id", "")).strip()}
    all_beat_ids: set[str] = set()
    total_lines = 0
    mapped_lines: set[tuple[str, int]] = set()
    repeated_groups: dict[tuple[int, ...], list[dict]] = {}
    for section_idx, section in enumerate(sections, start=1):
        lines = [row for row in section.get("lines", []) if isinstance(row, dict)]
        total_lines += len(lines)
        for beat in section.get("lyric_beats", []):
            if not isinstance(beat, dict):
                continue
            beat_id = str(beat.get("beat_id", "")).strip()
            if beat_id:
                all_beat_ids.add(beat_id)
            refs = tuple(_positive_int_refs(beat.get("line_refs", [])))
            repeated_groups.setdefault(refs, []).append(beat)
            if beat_id in shot_beat_ids:
                for ref in refs:
                    mapped_lines.add((section_idx, ref))
    variation_scores = []
    for refs, beats in repeated_groups.items():
        if len(refs) == 0 or len(beats) <= 1:
            continue
        signatures = {
            (
                str(beat.get("visible_action", "")).strip().lower(),
                str(beat.get("payoff_role", "")).strip().lower(),
            )
            for beat in beats
        }
        variation_scores.append(len(signatures) / float(len(beats)))
    repeated_variation = sum(variation_scores) / len(variation_scores) if variation_scores else 1.0
    return {
        "lyric_beat_count": len(all_beat_ids),
        "covered_beat_count": len(all_beat_ids & shot_beat_ids),
        "shot_to_lyric_coverage": round((len(all_beat_ids & shot_beat_ids) / len(all_beat_ids)) if all_beat_ids else 1.0, 3),
        "repeated_hook_variation": round(repeated_variation, 3),
        "unmapped_lyric_lines": max(0, total_lines - len(mapped_lines)),
    }


def _positive_int_refs(raw_values: object) -> list[int]:
    if not isinstance(raw_values, list):
        return []
    out: list[int] = []
    for item in raw_values:
        try:
            value = int(item)
        except (TypeError, ValueError):
            continue
        if value > 0:
            out.append(value)
    return out


def _route_stats(routes: list[dict], payload: dict) -> dict:
    beat_to_section = _beat_to_section_label(payload)
    total = 0
    ref_assisted = 0
    per_section: dict[str, dict[str, int]] = {}
    for row in routes:
        if not isinstance(row, dict):
            continue
        total += 1
        use_ref = bool(row.get("use_ref", False))
        if use_ref:
            ref_assisted += 1
        label = _route_section_label(row, beat_to_section)
        bucket = per_section.setdefault(label, {"total": 0, "ref": 0})
        bucket["total"] += 1
        if use_ref:
            bucket["ref"] += 1
    ratios = {
        label: round((vals["ref"] / vals["total"]) if vals["total"] else 0.0, 3)
        for label, vals in per_section.items()
    }
    return {
        "total_count": total,
        "tti_only_count": max(0, total - ref_assisted),
        "ref_assisted_count": ref_assisted,
        "ref_ratio_by_section": ratios,
    }


def _beat_to_section_label(payload: dict) -> dict[str, str]:
    timeline = payload.get("lyrics_timeline", {}) if isinstance(payload, dict) else {}
    out: dict[str, str] = {}
    for section in timeline.get("sections", []):
        if not isinstance(section, dict):
            continue
        label = str(section.get("section_label", section.get("section_name", "section"))).strip() or "section"
        for beat in section.get("lyric_beats", []):
            if not isinstance(beat, dict):
                continue
            beat_id = str(beat.get("beat_id", "")).strip()
            if beat_id:
                out[beat_id] = label
    return out


def _route_section_label(row: dict, beat_to_section: dict[str, str]) -> str:
    beat_id = str(row.get("lyric_beat_id", "")).strip()
    mapped = beat_to_section.get(beat_id, "").strip()
    if mapped:
        return mapped
    label = str(row.get("section_label", row.get("section_name", "section"))).strip()
    if "[" in label and "]" in label:
        return str(row.get("section_name", "section")).strip() or "section"
    return label or "section"
