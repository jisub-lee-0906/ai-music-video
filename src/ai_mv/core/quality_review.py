from __future__ import annotations

from ai_mv.core.quality_review_metrics import lyric_metrics, route_stats, v2_plan_metrics
from ai_mv.core.quality_review_sections import collect_risks, collect_strengths, review_story_alignment


def build_quality_review(config: dict, payload: dict) -> dict:
    review: dict = {}
    if payload.get("scene_plan_v2"):
        metrics = v2_plan_metrics(payload)
        review["v2_director_plan"] = {
            "strengths": _v2_strengths(metrics),
            "risks": _v2_risks(metrics),
            "metrics": metrics,
        }
    story = review_story_alignment(config, payload)
    if story:
        review["lyric_alignment"] = story["lyric_alignment"]
        review["repeat_variation"] = story["repeat_variation"]
        review["story_progression"] = story["story_progression"]
        review["section_visual_separation"] = story["section_visual_separation"]
        review["render_prompt_repetition"] = story["render_prompt_repetition"]
        review["profile_continuity"] = story["profile_continuity"]
        review["same_heroine_protection"] = story["same_heroine_protection"]
        review["style_alignment"] = story["style_alignment"]
        review["visual"] = {
            "reasoning": "Deterministic review inspected lyric alignment, repeat variation, section progression, section separation, render prompt reuse, same-heroine continuity coverage, and target-style alignment.",
            "strengths": collect_strengths(story),
            "risks": collect_risks(story),
        }
    return review


def build_run_summary(state: dict, payload: dict, quality_review: dict) -> dict:
    audio_map = payload.get("audio_map", {}) if isinstance(payload, dict) else {}
    sections = audio_map.get("sections", []) if isinstance(audio_map, dict) else []
    labels = [str(x.get("label", x.get("name", ""))).strip() for x in sections if isinstance(x, dict)]
    songform = [str(x.get("name", "")).strip() for x in sections if isinstance(x, dict)]
    route_summary = route_stats(payload.get("clip_routes", []), payload)
    if not payload.get("clip_routes") and isinstance(payload.get("render_plan_v2"), dict):
        shot_packages = [row for row in payload["render_plan_v2"].get("shot_packages", []) if isinstance(row, dict)]
        route_summary = {
            "total_count": len(shot_packages),
            "tti_only_count": 0,
            "ref_assisted_count": len(shot_packages),
            "ref_ratio_by_section": _v2_ref_ratio_by_section(shot_packages),
        }
    lyric_summary = lyric_metrics(payload)
    v2_metrics = v2_plan_metrics(payload) if payload.get("scene_plan_v2") else {}
    return {
        "run_id": state["run_id"],
        "selected_brief": str(payload.get("selected_brief", "")).strip(),
        "pipeline_version": "v2",
        "language": str(audio_map.get("language", "")).strip(),
        "selected_songform": songform,
        "selected_labels": labels,
        "tti_only_count": int(route_summary["tti_only_count"]),
        "ref_assisted_count": int(route_summary["ref_assisted_count"]),
        "ref_ratio_by_section": dict(route_summary["ref_ratio_by_section"]),
        "lyric_beat_count": int(lyric_summary["lyric_beat_count"]),
        "shot_to_lyric_coverage": float(lyric_summary["shot_to_lyric_coverage"]),
        "repeated_hook_variation": float(lyric_summary["repeated_hook_variation"]),
        "unmapped_lyric_lines": int(lyric_summary["unmapped_lyric_lines"]),
        "shot_package_count": int(v2_metrics.get("shot_package_count", 0)),
        "motif_family_count": int(v2_metrics.get("motif_family_count", 0)),
        "zone_count": int(v2_metrics.get("zone_count", 0)),
        "continuity_group_count": int(v2_metrics.get("continuity_group_count", 0)),
        "render_strategy_counts": dict(v2_metrics.get("render_strategy_counts", {})),
        "failure_reason": str(state.get("failure_reason", "")).strip(),
        "completed_stages": list(state.get("completed_stages", [])),
        "current_stage": str(state.get("current_stage", "")).strip(),
    }


def _v2_ref_ratio_by_section(shot_packages: list[dict]) -> dict[str, float]:
    buckets: dict[str, int] = {}
    for shot in shot_packages:
        label = str(shot.get("section_label", "")).strip() or "section"
        buckets[label] = buckets.get(label, 0) + 1
    return {label: 1.0 for label in buckets}


def _v2_strengths(metrics: dict) -> list[str]:
    strengths: list[str] = []
    if int(metrics.get("shot_package_count", 0)) > 0:
        strengths.append("Shot packages are populated for the full v2 planning chain.")
    if int(metrics.get("zone_count", 0)) >= 4:
        strengths.append("Zone progression spans multiple scene states instead of collapsing into a single location mode.")
    if int(metrics.get("motif_family_count", 0)) >= 4:
        strengths.append("Multiple motif families are in rotation, which reduces repetitive world signaling.")
    if int(metrics.get("continuity_group_count", 0)) >= 4:
        strengths.append("Continuity groups are separated across sections, which gives the chain clearer progression targets.")
    return strengths


def _v2_risks(metrics: dict) -> list[str]:
    risks: list[str] = []
    if int(metrics.get("motif_family_count", 0)) <= 2:
        risks.append("Motif family rotation is still narrow, so the world may feel repetitive even with correct shot coverage.")
    if int(metrics.get("zone_count", 0)) <= 2:
        risks.append("Zone progression is too shallow, so sections may not feel meaningfully different in staging.")
    strategies = dict(metrics.get("render_strategy_counts", {}))
    if set(strategies) == {"ref_pair"}:
        risks.append("Render strategy is still single-mode at the shot layer, so backend diversity has not opened up yet.")
    return risks
