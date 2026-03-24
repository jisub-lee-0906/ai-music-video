from __future__ import annotations

from ai_mv.core.quality_review_metrics import lyric_metrics, route_stats
from ai_mv.core.quality_review_sections import collect_risks, collect_strengths, review_story_alignment


def build_quality_review(config: dict, payload: dict) -> dict:
    review: dict = {}
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
    lyric_summary = lyric_metrics(payload)
    return {
        "run_id": state["run_id"],
        "profile_name": str(payload.get("selected_profile", "")).strip(),
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
        "failure_reason": str(state.get("failure_reason", "")).strip(),
        "completed_stages": list(state.get("completed_stages", [])),
        "current_stage": str(state.get("current_stage", "")).strip(),
    }
