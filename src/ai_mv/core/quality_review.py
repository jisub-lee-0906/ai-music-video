from __future__ import annotations


def build_quality_review(config: dict, payload: dict) -> dict:
    review: dict = {}
    coverage = _review_visual_plan(payload)
    if coverage:
        review["visual"] = coverage
    return review


def build_run_summary(state: dict, payload: dict, quality_review: dict) -> dict:
    audio_map = payload.get("audio_map", {}) if isinstance(payload, dict) else {}
    sections = audio_map.get("sections", []) if isinstance(audio_map, dict) else []
    labels = [str(x.get("label", x.get("name", ""))).strip() for x in sections if isinstance(x, dict)]
    songform = [str(x.get("name", "")).strip() for x in sections if isinstance(x, dict)]
    route_stats = _route_stats(payload.get("clip_routes", []))
    return {
        "run_id": state["run_id"],
        "profile_name": str(payload.get("selected_profile", "")).strip(),
        "language": str(audio_map.get("language", "")).strip(),
        "selected_songform": songform,
        "selected_labels": labels,
        "tti_only_count": int(route_stats["tti_only_count"]),
        "ref_assisted_count": int(route_stats["ref_assisted_count"]),
        "ref_ratio_by_section": dict(route_stats["ref_ratio_by_section"]),
        "failure_reason": str(state.get("failure_reason", "")).strip(),
        "completed_stages": list(state.get("completed_stages", [])),
        "current_stage": str(state.get("current_stage", "")).strip(),
    }


def _review_visual_plan(payload: dict) -> dict:
    visual = payload.get("visual_brief")
    workflow_inputs = payload.get("workflow_inputs_preview", {})
    if not isinstance(visual, dict) or not isinstance(workflow_inputs, dict):
        return {}
    section_briefs = [row for row in visual.get("section_briefs", []) if isinstance(row, dict)]
    if not section_briefs:
        return {}
    strengths: list[str] = []
    risks: list[str] = []
    reasoning: list[str] = []

    _check_location_recurrence(section_briefs, strengths, risks)
    _check_escalation(section_briefs, strengths, risks)
    _check_routes(payload.get("clip_routes", []), strengths, risks)
    _check_wan_output(workflow_inputs.get("wan_interpolation", {}), strengths, risks)

    if not strengths:
        strengths.append("visual contract is structurally complete enough for downstream render stages")
    if not risks:
        risks.append("no major structural repetition signal detected in deterministic review")
    reasoning.append("Deterministic review inspected section beats, escalation, routing balance, and render-facing prompt reuse.")
    return {
        "reasoning": " ".join(reasoning),
        "strengths": strengths[:8],
        "risks": risks[:8],
    }


def _check_location_recurrence(section_briefs: list[dict], strengths: list[str], risks: list[str]) -> None:
    locations = [str(row.get("location_anchor", "")).strip() for row in section_briefs if str(row.get("location_anchor", "")).strip()]
    unique = list(dict.fromkeys(locations))
    if 1 <= len(unique) <= 3:
        strengths.append("location families stay compact enough to preserve a single visual world")
    if len(unique) > max(3, len(section_briefs) // 2):
        risks.append("section locations diversify too aggressively and may fracture world continuity")


def _check_escalation(section_briefs: list[dict], strengths: list[str], risks: list[str]) -> None:
    beats = [str(row.get("story_beat", "")).strip().lower() for row in section_briefs]
    if len(set(beats)) < len([beat for beat in beats if beat]) * 0.75:
        risks.append("section story beats repeat too closely and may flatten progression")
    chorus_rows = [row for row in section_briefs if str(row.get("section_name", "")).strip().lower() == "chorus"]
    chorus_levels = [str(row.get("escalation_level", "")).strip().lower() for row in chorus_rows]
    chorus_axes = [str(row.get("motion_axis", "")).strip().lower() for row in chorus_rows]
    if chorus_rows and len(set(chorus_levels + chorus_axes)) > 1:
        strengths.append("repeated chorus sections preserve escalation signals instead of collapsing into one beat")
    elif len(chorus_rows) > 1:
        risks.append("repeated chorus sections lack distinct escalation markers")
    for row in section_briefs:
        sec = str(row.get("section_name", "")).strip().lower()
        escalation = str(row.get("escalation_level", "")).strip().lower()
        if sec == "bridge" and escalation != "interrupt":
            risks.append("bridge does not declare an interruptive role")
            break
    for row in section_briefs:
        sec = str(row.get("section_name", "")).strip().lower()
        escalation = str(row.get("escalation_level", "")).strip().lower()
        if sec == "outro" and escalation != "residue":
            risks.append("outro does not preserve a residue role")
            break


def _check_routes(routes: list[dict], strengths: list[str], risks: list[str]) -> None:
    stats = _route_stats(routes)
    if stats["ref_assisted_count"] and stats["tti_only_count"]:
        strengths.append("routing balances reference-heavy identity shots against cheaper tti-only coverage")
    if stats["total_count"] and stats["ref_assisted_count"] == stats["total_count"]:
        risks.append("all clips are ref-assisted, which reduces the benefit of the simplified routing policy")


def _check_wan_output(wan: dict, strengths: list[str], risks: list[str]) -> None:
    clips = wan.get("clips", []) if isinstance(wan, dict) else []
    prompts = [str(row.get("positive_prompt", "")).strip().lower() for row in clips if isinstance(row, dict)]
    if prompts and len(set(prompts)) == len(prompts):
        strengths.append("render-facing wan prompts remain distinct clip to clip")
    elif len(prompts) > 1:
        risks.append("render-facing wan prompts repeat verbatim across clips")


def _route_stats(routes: list[dict]) -> dict:
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
        label = str(row.get("section_label", row.get("section_name", "section"))).strip() or "section"
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
