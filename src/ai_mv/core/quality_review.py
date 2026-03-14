from __future__ import annotations

from ai_mv.core.contracts.prompt_schema import coverage_review_schema
from ai_mv.infra.codex_cli_client import generate_structured


def build_quality_review(config: dict, payload: dict) -> dict:
    review: dict = {}
    coverage = _maybe_review_coverage(config, payload)
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


def _maybe_review_coverage(config: dict, payload: dict) -> dict:
    visual = payload.get("visual_brief")
    workflow_inputs = payload.get("workflow_inputs_preview", {})
    if not isinstance(visual, dict) or not isinstance(workflow_inputs, dict):
        return {}
    tti = workflow_inputs.get("tti_anchor", {})
    shot_router = workflow_inputs.get("shot_router", {})
    flux2_ref = workflow_inputs.get("flux2_ref_chain", {})
    wan = workflow_inputs.get("wan_interpolation", {})
    if not tti or not wan:
        return {}
    prompt = _coverage_prompt(payload, visual, tti, shot_router, flux2_ref, wan)
    raw = generate_structured(config, prompt, coverage_review_schema())
    return {
        "reasoning": str(raw["reasoning"]).strip(),
        "strengths": [str(x).strip() for x in raw["strengths"] if str(x).strip()],
        "risks": [str(x).strip() for x in raw["risks"] if str(x).strip()],
        "prompt": prompt,
    }


def _coverage_prompt(payload: dict, visual: dict, tti: dict, shot_router: dict, flux2_ref: dict, wan: dict) -> str:
    profile = str(payload.get("audio_map", {}).get("profile_summary", "")).strip()
    sections = _section_summary(visual)
    tti_text = str(tti.get("master_anchor", {}).get("text", tti.get("master_anchor", {}).get("prompt_text", ""))).strip()
    route_text = _route_summary(shot_router)
    route_stats = _route_stats_text(payload.get("clip_routes", []))
    flux2_ref_text = _flux2_ref_summary(flux2_ref)
    wan_text = _wan_summary(wan)
    return (
        "You are a music-video coverage reviewer checking whether the planned visual payload would edit into a compelling MV. "
        "Return JSON only. "
        "Review the single provided plan; do not rank or compare alternatives. "
        "Evaluate same-world continuity, section progression, repeated-return escalation, editability, character consistency, and routing discipline. "
        "Penalize portrait repetition, weak visual payoff in Chorus 2 or Final Chorus, overuse of ref-assisted routing in coverage sections, weak bridge interruption, and outro residue that does not leave a final image. "
        f"Profile={profile}. "
        f"Section dramaturgy={sections}. "
        f"TTI master anchor={tti_text}. "
        f"Shot routing={route_text}. "
        f"Routing stats={route_stats}. "
        f"Flux2 reference workflow inputs={flux2_ref_text}. "
        f"WAN workflow inputs={wan_text}."
    )


def _section_summary(visual: dict) -> str:
    rows = []
    for row in visual.get("section_briefs", []):
        if not isinstance(row, dict):
            continue
        rows.append(
            f"{row.get('section_name','')}: beat={row.get('story_beat','')}; location={row.get('location_anchor','')}; arc={row.get('emotional_arc','')}"
        )
    return " | ".join(rows)


def _flux2_ref_summary(flux2_ref: dict) -> str:
    items = flux2_ref.get("items", []) if isinstance(flux2_ref, dict) else []
    rows = []
    for item in items[:12]:
        if not isinstance(item, dict):
            continue
        rows.append(
            f"{item.get('shot_id','')}: phase={item.get('clip_phase','')}; relation={item.get('space_relation','')}; start={item.get('start_text','')}; end={item.get('end_text','')}"
        )
    return " | ".join(rows)


def _route_summary(shot_router: dict) -> str:
    rows = shot_router.get("decisions", []) if isinstance(shot_router, dict) else []
    out = []
    for row in rows[:12]:
        if not isinstance(row, dict):
            continue
        out.append(
            f"{row.get('shot_id','')}: ref={row.get('use_ref', False)}; "
            f"reason={row.get('reason','')}; mv={row.get('mv_function','')}; "
            f"phase={row.get('clip_phase','')}; priority={row.get('shot_priority','')}"
        )
    return " | ".join(out)


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


def _route_stats_text(routes: list[dict]) -> str:
    stats = _route_stats(routes)
    ratios = ", ".join(f"{k}={v}" for k, v in stats["ref_ratio_by_section"].items())
    return (
        f"total={stats['total_count']}; "
        f"tti_only={stats['tti_only_count']}; "
        f"ref_assisted={stats['ref_assisted_count']}; "
        f"section_ratios={ratios}"
    )


def _wan_summary(wan: dict) -> str:
    clips = wan.get("clips", []) if isinstance(wan, dict) else []
    rows = []
    for clip in clips[:12]:
        if not isinstance(clip, dict):
            continue
        rows.append(
            f"{clip.get('shot_id','')}: energy={clip.get('energy','')}; relation={clip.get('space_relation','')}; pos={clip.get('positive_prompt','')}"
        )
    return " | ".join(rows)
