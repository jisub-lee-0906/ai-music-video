from __future__ import annotations

from ai_mv.core.quality_review_metrics import lyric_metrics, plan_metrics, route_stats
from ai_mv.core.quality_review_sections import collect_risks, collect_strengths, review_story_alignment
from ai_mv.core.visual_prompt_evaluator import build_visual_prompt_evaluation


def build_quality_review(config: dict, payload: dict) -> dict:
    review: dict = {}
    if payload.get("scene_outline") or payload.get("direction_plan") or payload.get("prompt_plan"):
        metrics = plan_metrics(payload)
        review["direction_review"] = {
            "reasoning": "Deterministic review inspected scene outline coverage, story-function variety, world-zone spread, and direction-plan archetype coverage.",
            "strengths": _plan_strengths(metrics),
            "risks": _plan_risks(metrics),
            "metrics": metrics,
        }
    visual_eval = build_visual_prompt_evaluation(payload)
    if visual_eval:
        review.update(visual_eval)
    story = review_story_alignment(config, payload)
    if story:
        review["story_review"] = {
            "reasoning": "Writer-layer review inspected lyric alignment, story progression, section separation, and story-profile continuity.",
            "strengths": collect_strengths(
                {
                    "lyric_alignment": story.get("lyric_alignment", {}),
                    "story_progression": story.get("story_progression", {}),
                    "section_visual_separation": story.get("section_visual_separation", {}),
                    "profile_continuity": story.get("profile_continuity", {}),
                }
            ),
            "risks": collect_risks(
                {
                    "lyric_alignment": story.get("lyric_alignment", {}),
                    "story_progression": story.get("story_progression", {}),
                    "section_visual_separation": story.get("section_visual_separation", {}),
                    "profile_continuity": story.get("profile_continuity", {}),
                }
            ),
        }
        review["prompt_review"] = {
            "reasoning": "Prompt-plan review inspected repeated prompt shapes, same-heroine continuity wording, and style alignment.",
            "strengths": collect_strengths(
                {
                    "render_prompt_repetition": story.get("render_prompt_repetition", {}),
                    "same_heroine_protection": story.get("same_heroine_protection", {}),
                    "style_alignment": story.get("style_alignment", {}),
                }
            ),
            "risks": collect_risks(
                {
                    "render_prompt_repetition": story.get("render_prompt_repetition", {}),
                    "same_heroine_protection": story.get("same_heroine_protection", {}),
                    "style_alignment": story.get("style_alignment", {}),
                }
            ),
            "metrics": {
                "prompt_distinct_ratio": story.get("render_prompt_repetition", {}).get("distinct_ratio", 1.0),
                "same_heroine_protected_ratio": story.get("same_heroine_protection", {}).get("protected_ratio", 1.0),
                "style_alignment_ratio": story.get("style_alignment", {}).get("graphic_event_ratio", 0.0),
            },
        }
        review["visual_generation_review"] = {
            "reasoning": "Visual generation review combines prompt-contract checks with stage-level story and direction findings.",
            "strengths": collect_strengths({**story, **visual_eval}),
            "risks": collect_risks({**story, **visual_eval}),
        }
        review["lyric_alignment"] = story["lyric_alignment"]
        review["repeat_variation"] = story["repeat_variation"]
        review["story_progression"] = story["story_progression"]
        review["section_visual_separation"] = story["section_visual_separation"]
        review["render_prompt_repetition"] = story["render_prompt_repetition"]
        review["profile_continuity"] = story["profile_continuity"]
        review["same_heroine_protection"] = story["same_heroine_protection"]
        review["style_alignment"] = story["style_alignment"]
    return review


def build_run_summary(state: dict, payload: dict, quality_review: dict) -> dict:
    audio_map = payload.get("audio_map", {}) if isinstance(payload, dict) else {}
    sections = audio_map.get("sections", []) if isinstance(audio_map, dict) else []
    labels = [str(x.get("label", x.get("name", ""))).strip() for x in sections if isinstance(x, dict)]
    songform = [str(x.get("name", "")).strip() for x in sections if isinstance(x, dict)]
    route_summary = route_stats(payload.get("clip_routes", []), payload)
    if not payload.get("clip_routes") and isinstance(payload.get("prompt_plan"), dict):
        ref_items = [row for row in payload["prompt_plan"].get("ref_items", []) if isinstance(row, dict)]
        route_summary = {
            "total_count": len(ref_items),
            "tti_only_count": 0,
            "ref_assisted_count": len(ref_items),
            "ref_ratio_by_section": _ref_ratio_by_section(ref_items),
        }
    lyric_summary = lyric_metrics(payload)
    summary_metrics = plan_metrics(payload) if payload.get("scene_outline") else {}
    return {
        "run_id": state["run_id"],
        "selected_brief": str(payload.get("selected_brief", "")).strip(),
        "pipeline_version": "visual",
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
        "shot_package_count": int(summary_metrics.get("shot_package_count", 0)),
        "world_zone_count": int(summary_metrics.get("world_zone_count", 0)),
        "story_function_count": int(summary_metrics.get("story_function_count", 0)),
        "archetype_count": int(summary_metrics.get("archetype_count", 0)),
        "failure_reason": str(state.get("failure_reason", "")).strip(),
        "completed_stages": list(state.get("completed_stages", [])),
        "current_stage": str(state.get("current_stage", "")).strip(),
    }


def _ref_ratio_by_section(rows: list[dict]) -> dict[str, float]:
    buckets: dict[str, int] = {}
    for shot in rows:
        label = str(shot.get("section_label", "")).strip() or "section"
        buckets[label] = buckets.get(label, 0) + 1
    return {label: 1.0 for label in buckets}


def _plan_strengths(metrics: dict) -> list[str]:
    strengths: list[str] = []
    if int(metrics.get("shot_package_count", 0)) > 0:
        strengths.append("Scene, direction, and prompt plans are populated for the full planning chain.")
    if int(metrics.get("world_zone_count", 0)) >= 3:
        strengths.append("World-zone progression spans multiple scene states instead of collapsing into one place mode.")
    if int(metrics.get("story_function_count", 0)) >= 3:
        strengths.append("Story functions vary across shots instead of repeating a single dramatic beat.")
    if int(metrics.get("archetype_count", 0)) >= 4:
        strengths.append("Direction plan rotates across multiple archetypes instead of collapsing into one prompt family.")
    return strengths


def _plan_risks(metrics: dict) -> list[str]:
    risks: list[str] = []
    if int(metrics.get("story_function_count", 0)) <= 2:
        risks.append("Story-function rotation is still narrow, so the visual chain may feel repetitive.")
    if int(metrics.get("world_zone_count", 0)) <= 2:
        risks.append("World-zone progression is too shallow, so sections may not feel meaningfully different.")
    if int(metrics.get("archetype_count", 0)) <= 2:
        risks.append("Archetype variety is too narrow, so prompt execution may flatten into a single family.")
    return risks
