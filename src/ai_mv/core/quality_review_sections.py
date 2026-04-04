from __future__ import annotations

from ai_mv.core.quality_review_metrics import lyric_metrics


def review_story_alignment(config: dict, payload: dict) -> dict:
    timeline = payload.get("lyrics_timeline", {})
    if not isinstance(timeline, dict) or not isinstance(payload.get("scene_outline"), dict):
        return {}
    metrics = lyric_metrics(payload)
    return {
        "lyric_alignment": {
            "reasoning": "Lyric lines were checked against beat coverage in the scene outline.",
            "strengths": [f"shot coverage maps {metrics['covered_beat_count']} lyric beats"],
            "risks": [f"{metrics['unmapped_lyric_lines']} lyric lines are unmapped"] if metrics["unmapped_lyric_lines"] else [],
        },
        "repeat_variation": {
            "reasoning": "Repeated hooks are evaluated later through prompt execution and image review.",
            "strengths": [],
            "risks": [],
        },
        "story_progression": story_progression(payload),
        "section_visual_separation": section_visual_separation(payload),
        "render_prompt_repetition": render_prompt_repetition(payload.get("workflow_inputs_preview", {})),
        "profile_continuity": profile_continuity(payload),
        "same_heroine_protection": same_heroine_protection(config, payload),
        "style_alignment": style_alignment(payload),
    }


def story_progression(payload: dict) -> dict:
    progression = [row for row in payload["scene_outline"].get("section_progression", []) if isinstance(row, dict)]
    roles = {str(row.get("story_goal", "")).strip() for row in progression if str(row.get("story_goal", "")).strip()}
    zones = {str(row.get("world_zone", "")).strip() for row in progression if str(row.get("world_zone", "")).strip()}
    strengths = []
    risks = []
    if len(roles) >= 3:
        strengths.append("section progression differentiates story goals across the song")
    else:
        risks.append("section story goals are still too repetitive")
    if len(zones) >= 3:
        strengths.append("world zones change meaningfully across sections")
    else:
        risks.append("world zones are too shallow across sections")
    return {"reasoning": "Section progression was checked for distinct story goals and world zones.", "strengths": strengths, "risks": risks}


def render_prompt_repetition(workflow_inputs: dict) -> dict:
    backend_preview = workflow_inputs.get("backend_preview", {}) if isinstance(workflow_inputs, dict) else {}
    rows = [str(row.get("positive_prompt_preview", "")).strip().lower() for row in backend_preview.get("wan_adapter", []) if isinstance(row, dict)]
    ratio = (len(set(rows)) / len(rows)) if rows else 1.0
    strengths = ["WAN prompt previews preserve clip-to-clip differences"] if ratio >= 0.7 else []
    risks = ["WAN prompt previews repeat too aggressively across clips"] if rows and ratio < 0.7 else []
    return {"reasoning": "WAN prompt previews were checked for repeated text.", "strengths": strengths, "risks": risks, "distinct_ratio": round(ratio, 3)}


def section_visual_separation(payload: dict) -> dict:
    sections = {}
    for row in payload["scene_outline"].get("shot_packages", []):
        if not isinstance(row, dict):
            continue
        label = str(row.get("section_label", "")).strip()
        bucket = sections.setdefault(label, {"zones": set(), "functions": set()})
        if str(row.get("world_zone", "")).strip():
            bucket["zones"].add(str(row.get("world_zone", "")).strip())
        if str(row.get("story_function", "")).strip():
            bucket["functions"].add(str(row.get("story_function", "")).strip())
    ordered = list(sections.items())
    comparisons = 0
    distinct_pairs = 0
    for (_pl, prev), (_cl, cur) in zip(ordered, ordered[1:]):
        comparisons += 1
        if prev != cur:
            distinct_pairs += 1
    ratio = (distinct_pairs / comparisons) if comparisons else 1.0
    strengths = ["adjacent sections carry distinct story-function or world-zone setups"] if ratio >= 0.6 else []
    risks = ["adjacent sections still read too similarly in structure"] if comparisons and ratio < 0.6 else []
    return {"reasoning": "Section transitions were checked for world-zone and story-function change.", "strengths": strengths, "risks": risks, "separation_ratio": round(ratio, 3)}


def profile_continuity(payload: dict) -> dict:
    outline = payload["scene_outline"]
    strengths = []
    risks = []
    if str(outline.get("story_premise", "")).strip():
        strengths.append("story premise is present in the scene outline")
    else:
        risks.append("story premise is missing from the scene outline")
    if str(outline.get("world_rules", "")).strip():
        strengths.append("world rules are preserved in the scene outline")
    else:
        risks.append("world rules are missing from the scene outline")
    return {"reasoning": "Writer-layer story premises and world rules were checked in the outline output.", "strengths": strengths, "risks": risks}


def same_heroine_protection(config: dict, payload: dict) -> dict:
    ref_items = [row for row in payload.get("prompt_plan", {}).get("ref_items", []) if isinstance(row, dict)]
    ratio = (
        sum(1 for row in ref_items if "same" in str(row.get("ref_start_prompt_text", "")).lower()) / float(len(ref_items))
        if ref_items
        else 1.0
    )
    strengths = ["prompt plan keeps same-heroine language across REF items"] if ratio >= 0.9 else []
    risks = ["prompt plan loses same-heroine continuity in too many REF items"] if ratio < 0.9 else []
    return {"reasoning": "REF prompt text was checked for same-heroine continuity wording.", "strengths": strengths, "risks": risks, "protected_ratio": round(ratio, 3), "direct_face_ratio": 0.0}


def style_alignment(payload: dict) -> dict:
    direction = [row for row in payload.get("direction_plan", {}).get("shot_packages", []) if isinstance(row, dict)]
    if not direction:
        return {
            "reasoning": "Direction-plan world zones and story-visual intents were checked for cinematic staging variety.",
            "strengths": [],
            "risks": [],
            "graphic_event_ratio": 0.0,
            "non_heroine_focus_ratio": 0.0,
            "payoff_graphic_ratio": 0.0,
            "route_non_heroine_focus_ratio": 0.0,
        }
    visual_intent_ratio = sum(1 for row in direction if str(row.get("story_visual_intent", "")).strip()) / float(len(direction))
    section_signatures: dict[str, dict[str, set[str]]] = {}
    payoff_release_hits = 0
    for row in direction:
        label = str(row.get("section_label", "")).strip() or "section"
        bucket = section_signatures.setdefault(
            label,
            {
                "zones": set(),
                "archetypes": set(),
                "surfaces": set(),
                "functions": set(),
            },
        )
        zone = str(row.get("world_zone", "")).strip()
        archetype = str(row.get("ref_archetype", "")).strip()
        surface = _surface_family(str(row.get("primary_surface", "")).strip())
        story_function = str(row.get("story_function", "")).strip()
        if zone:
            bucket["zones"].add(zone)
        if archetype:
            bucket["archetypes"].add(archetype)
        if surface:
            bucket["surfaces"].add(surface)
        if story_function:
            bucket["functions"].add(story_function)
        if story_function == "payoff" and (
            zone == "open_peak" or surface in {"crosswalk", "platform_edge", "curb", "street_release"}
        ):
            payoff_release_hits += 1

    ordered = list(section_signatures.items())
    comparisons = 0
    distinct_pairs = 0
    for (_, prev), (_, cur) in zip(ordered, ordered[1:]):
        comparisons += 1
        if prev != cur:
            distinct_pairs += 1
    section_signature_ratio = (distinct_pairs / float(comparisons)) if comparisons else 1.0
    surface_family_count = len({surface for bucket in section_signatures.values() for surface in bucket["surfaces"] if surface})
    surface_contrast_ratio = min(1.0, surface_family_count / 4.0)
    payoff_graphic_ratio = 1.0 if payoff_release_hits > 0 else 0.0
    graphic_event_ratio = round(
        (
            (visual_intent_ratio * 0.30)
            + (section_signature_ratio * 0.30)
            + (surface_contrast_ratio * 0.20)
            + (payoff_graphic_ratio * 0.20)
        ),
        3,
    )
    strengths = ["direction plan includes staged world-zone variety and explicit story-visual intent for a cinematic music-video flow"] if graphic_event_ratio >= 0.6 else []
    risks = ["direction plan still lacks enough world-zone contrast or explicit story-visual intent"] if graphic_event_ratio < 0.6 else []
    return {
        "reasoning": "Direction-plan world zones and story-visual intents were checked for cinematic staging variety.",
        "strengths": strengths,
        "risks": risks,
        "graphic_event_ratio": graphic_event_ratio,
        "non_heroine_focus_ratio": 0.0,
        "payoff_graphic_ratio": payoff_graphic_ratio,
        "route_non_heroine_focus_ratio": 0.0,
    }


def _surface_family(surface: str) -> str:
    lowered = surface.strip().lower()
    if not lowered:
        return ""
    if "crosswalk" in lowered:
        return "crosswalk"
    if "platform edge" in lowered or "platform" in lowered:
        return "platform_edge"
    if "threshold" in lowered or "gate" in lowered or "turnstile" in lowered:
        return "threshold_gate"
    if "sidewalk" in lowered or "pavement" in lowered or "curb" in lowered:
        return "street_release"
    if "stairs" in lowered or "stair" in lowered:
        return "stairs"
    if "passage" in lowered or "corridor" in lowered:
        return "passage"
    if "window" in lowered or "glass" in lowered:
        return "window_contact"
    return lowered


def collect_strengths(story: dict) -> list[str]:
    out: list[str] = []
    for key in (
        "lyric_alignment",
        "repeat_variation",
        "story_progression",
        "section_visual_separation",
        "render_prompt_repetition",
        "profile_continuity",
        "same_heroine_protection",
        "style_alignment",
        "prompt_review",
        "visual_generation_review",
    ):
        node = story.get(key, {})
        out.extend(str(x) for x in node.get("strengths", []) if str(x).strip())
    return out[:8] or ["writer, director, and prompt-plan structure is present"]


def collect_risks(story: dict) -> list[str]:
    out: list[str] = []
    for key in (
        "lyric_alignment",
        "repeat_variation",
        "story_progression",
        "section_visual_separation",
        "render_prompt_repetition",
        "profile_continuity",
        "same_heroine_protection",
        "style_alignment",
        "prompt_review",
        "visual_generation_review",
    ):
        node = story.get(key, {})
        out.extend(str(x) for x in node.get("risks", []) if str(x).strip())
    return out[:8] or ["no major structural risk detected"]
