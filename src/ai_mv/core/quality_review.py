from __future__ import annotations

from ai_mv.core.quality_review_metrics import duration_metrics, lyric_metrics, plan_metrics, prompt_metrics, route_stats


def build_quality_review(config: dict, payload: dict) -> dict:
    metrics = plan_metrics(payload)
    lyric = lyric_metrics(payload)
    prompts = prompt_metrics(payload)
    durations = duration_metrics(payload)
    route = route_stats(payload.get("clip_routes", []), payload)
    strengths: list[str] = []
    risks: list[str] = []
    if int(metrics.get("shot_package_count", 0)) > 0:
        strengths.append("storyboard generated at least one shot")
    else:
        risks.append("storyboard is empty")
    if lyric["unmapped_lyric_lines"] == 0:
        strengths.append("all lyric lines map to at least one shot")
    else:
        risks.append(f"{lyric['unmapped_lyric_lines']} lyric lines are unmapped")
    if int(route.get("total_count", 0)) > 0:
        strengths.append("clip routes are populated")
    elif payload.get("prompt_plan"):
        risks.append("render routes are missing")
    if bool(lyric.get("beat_timing_monotonic", False)):
        strengths.append("lyric beat timing stays monotonic across the song")
    else:
        risks.append("lyric beat timing is not monotonic")
    if int(prompts.get("ref_adjacent_duplicate_count", 0)) == 0:
        strengths.append("adjacent REF prompts are not duplicated")
    else:
        risks.append(f"{int(prompts['ref_adjacent_duplicate_count'])} adjacent REF prompts repeat too closely")
    if int(prompts.get("wan_adjacent_duplicate_count", 0)) == 0:
        strengths.append("adjacent WAN prompts are not duplicated")
    else:
        risks.append(f"{int(prompts['wan_adjacent_duplicate_count'])} adjacent WAN prompts repeat too closely")
    if int(prompts.get("subject_drift_count", 0)) == 0:
        strengths.append("REF prompts keep subject identity wording stable")
    else:
        risks.append(f"{int(prompts['subject_drift_count'])} REF prompts show subject drift")
    if float(durations.get("audio_duration_sec", 0.0)) > 0.0 and float(durations.get("video_duration_sec", 0.0)) > 0.0:
        drift = float(durations.get("duration_drift_sec", 0.0))
        if drift <= 0.2:
            strengths.append("final video length stays closely aligned to the audio")
        else:
            risks.append(f"audio/video length drift is {drift:.3f}s")
    return {
        "reasoning": "Technical safety review only. This report is a lightweight runtime signal, not the main creative evaluation. Use llm_review.json as the primary qualitative review.",
        "strengths": strengths,
        "risks": risks,
        "metrics": {
            "shot_package_count": int(metrics.get("shot_package_count", 0)),
            "lyric_beat_count": int(lyric.get("lyric_beat_count", 0)),
            "unmapped_lyric_lines": int(lyric.get("unmapped_lyric_lines", 0)),
            "route_count": int(route.get("total_count", 0)),
            "beat_timing_monotonic": bool(lyric.get("beat_timing_monotonic", False)),
            "ref_adjacent_duplicate_count": int(prompts.get("ref_adjacent_duplicate_count", 0)),
            "wan_adjacent_duplicate_count": int(prompts.get("wan_adjacent_duplicate_count", 0)),
            "subject_drift_count": int(prompts.get("subject_drift_count", 0)),
            "ref_duration_summary": dict(prompts.get("ref_duration_summary", {})),
            "wan_duration_summary": dict(prompts.get("wan_duration_summary", {})),
            "audio_duration_sec": float(durations.get("audio_duration_sec", 0.0)),
            "video_duration_sec": float(durations.get("video_duration_sec", 0.0)),
            "duration_drift_sec": float(durations.get("duration_drift_sec", 0.0)),
        },
    }


def _prompt_rule_trace(payload: dict) -> dict:
    prompt_plan = payload.get("prompt_plan", {}) if isinstance(payload, dict) else {}
    ref_items = [row for row in prompt_plan.get("ref_items", []) if isinstance(row, dict)]
    wan_items = [row for row in prompt_plan.get("wan_items", []) if isinstance(row, dict)]
    master = dict(prompt_plan.get("master_anchor", {})) if isinstance(prompt_plan, dict) else {}
    ref_with_golden = sum(1 for row in ref_items if str(row.get("applied_golden_structure", "")).strip())
    wan_with_golden = sum(1 for row in wan_items if str(row.get("applied_golden_structure", "")).strip())
    global_refs = sum(1 for row in ref_items if row.get("applied_global_prompt_rules"))
    global_wan = sum(1 for row in wan_items if row.get("applied_global_prompt_rules"))
    return {
        "master_anchor_precedence": str(master.get("rule_precedence_summary", "")).strip(),
        "ref_items_with_global_rules": global_refs,
        "ref_items_with_golden_structure": ref_with_golden,
        "wan_items_with_global_rules": global_wan,
        "wan_items_with_golden_structure": wan_with_golden,
    }


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
    prompt_summary = prompt_metrics(payload)
    duration_summary = duration_metrics(payload)
    return {
        "run_id": state["run_id"],
        "selected_brief": str(payload.get("selected_brief", "")).strip(),
        "pipeline_version": "music_profile_centered_v1",
        "review_mode": "technical_signals_plus_llm_review",
        "language": str(audio_map.get("language", "")).strip(),
        "selected_songform": songform,
        "selected_labels": labels,
        "tti_only_count": int(route_summary["tti_only_count"]),
        "ref_assisted_count": int(route_summary["ref_assisted_count"]),
        "ref_ratio_by_section": dict(route_summary["ref_ratio_by_section"]),
        "lyric_beat_count": int(lyric_summary["lyric_beat_count"]),
        "shot_to_lyric_coverage": float(lyric_summary["shot_to_lyric_coverage"]),
        "unmapped_lyric_lines": int(lyric_summary["unmapped_lyric_lines"]),
        "beat_timing_monotonic": bool(lyric_summary.get("beat_timing_monotonic", False)),
        "shot_package_count": int(summary_metrics.get("shot_package_count", 0)),
        "payoff_role_count": int(summary_metrics.get("payoff_role_count", 0)),
        "shot_function_count": int(summary_metrics.get("shot_function_count", 0)),
        "place_count": int(summary_metrics.get("place_count", 0)),
        "ref_item_count": int(prompt_summary.get("ref_item_count", 0)),
        "wan_item_count": int(prompt_summary.get("wan_item_count", 0)),
        "ref_adjacent_duplicate_count": int(prompt_summary.get("ref_adjacent_duplicate_count", 0)),
        "wan_adjacent_duplicate_count": int(prompt_summary.get("wan_adjacent_duplicate_count", 0)),
        "subject_drift_count": int(prompt_summary.get("subject_drift_count", 0)),
        "ref_duration_summary": dict(prompt_summary.get("ref_duration_summary", {})),
        "wan_duration_summary": dict(prompt_summary.get("wan_duration_summary", {})),
        "audio_duration_sec": float(duration_summary.get("audio_duration_sec", 0.0)),
        "video_duration_sec": float(duration_summary.get("video_duration_sec", 0.0)),
        "duration_drift_sec": float(duration_summary.get("duration_drift_sec", 0.0)),
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
