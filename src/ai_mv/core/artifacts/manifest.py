from __future__ import annotations

from ai_mv.core.artifacts.paths import latest_file, latest_success_file, run_file
from ai_mv.core.artifacts.provenance import dedupe_preserve_order, normalized_text_list
from ai_mv.core.artifacts.schema import artifact_schema_version
from ai_mv.core.artifacts.success_policy import latest_success_eligible
from ai_mv.core.artifacts.summary_fields import _assembly_revision_summary
from ai_mv.core.planning.sections import normalized_sections
from ai_mv.utils.json_utils import write_json


def write_manifest(state: dict, payload: dict) -> None:
    scope = str(state.get("scope", "run"))
    rerender_escalation = payload.get("rerender_escalation") if isinstance(payload.get("rerender_escalation"), dict) else {}
    escalation_artifacts = rerender_escalation.get("artifacts") if isinstance(rerender_escalation.get("artifacts"), dict) else {}
    audio_map = dict(payload.get("audio_map", {}))
    section_plan = _manifest_section_plan(payload, audio_map)
    out = {
        "run_id": state["run_id"],
        "status": state["status"],
        "failure_reason": state["failure_reason"],
        "schema_version": artifact_schema_version(),
        "input": {
            "concept_text": str(payload.get("concept_text", "")),
        },
        "song": {
            "master_audio": str(payload.get("music_file", "")),
            "section_map": audio_map,
            "audio_plan": dict(payload.get("audio_plan", {})),
        },
        "plan": {
            "style_lane": str(payload.get("style_lane", "")),
            "style_resolution": dict(payload.get("style_resolution", {})) or {
                "style_lane": str(payload.get("style_lane", "")),
            },
            "section_plan": section_plan,
            "material_plan": list(payload.get("material_plan", [])),
            "render_plan": list(payload.get("render_plan", [])),
        },
        "stills": {
            "material_results": list(payload.get("material_results", payload.get("still_results", []))),
        },
        "clips": {
            "clip_results": list(payload.get("clip_results", [])),
        },
        "assembly": {
            "final_video": str(payload.get("final_video", "")),
            "assembly_plan": dict(payload.get("assembly_plan", {})),
            "review_inputs": dict(payload.get("review_inputs", {})),
            "assembly_revision": _manifest_assembly_revision(payload),
        },
        "review": _manifest_review_section(payload, escalation_artifacts, rerender_escalation),
        "artifacts": {
            "scope": scope,
        },
    }
    anchor_results = [row for row in payload.get("anchor_results", []) if isinstance(row, dict)]
    if anchor_results:
        out["stills"]["anchor_results"] = anchor_results
    write_json(run_file(state["run_id"], "manifest.json", scope), out)
    write_json(latest_file("manifest.json", scope), out)
    if latest_success_eligible(state, payload):
        write_json(latest_success_file("manifest.json", scope), out)


def _manifest_assembly_revision(payload: dict) -> dict:
    summary = _assembly_revision_summary(payload)
    if not summary:
        return {}
    revision_result = payload.get("assembly_revision_result") if isinstance(payload.get("assembly_revision_result"), dict) else {}
    out = {
        "present": bool(summary.get("present", False)),
        "action": str(summary.get("action", "")).strip(),
        "status": str(revision_result.get("status", "")).strip(),
        "target": str(summary.get("target", "")).strip(),
        "final_video": str(summary.get("final_video", "")).strip(),
        "target_shots": normalized_text_list(summary.get("target_shots")),
        "target_material_ids": normalized_text_list(summary.get("target_material_ids")),
        "target_section_ids": normalized_text_list(summary.get("target_section_ids")),
    }
    return out if any(value for key, value in out.items() if key != "present") else {}



def _manifest_rerender_escalation(rerender_escalation: dict) -> dict:
    shot_ids = normalized_text_list(rerender_escalation.get("shot_ids"))
    material_ids = normalized_text_list(rerender_escalation.get("material_ids"))
    section_ids = normalized_text_list(rerender_escalation.get("section_ids"))
    out = {
        "status": str(rerender_escalation.get("status", "")).strip(),
        "shot_ids": shot_ids,
        "material_ids": material_ids,
        "section_ids": section_ids,
        "unique_material_ids": dedupe_preserve_order(material_ids),
        "unique_section_ids": dedupe_preserve_order(section_ids),
    }
    return out if any(out.values()) else {}



def _manifest_review_section(payload: dict, escalation_artifacts: dict, rerender_escalation: dict) -> dict:
    review_report = dict(payload.get("review_report", {}))
    out = {
        "review_report": review_report,
        "review_packet_manifest": str(escalation_artifacts.get("review_packet_manifest", "")).strip(),
        "rerender_escalation": _manifest_rerender_escalation(rerender_escalation),
    }
    audio_review_summary = review_report.get("audio_review_summary") if isinstance(review_report.get("audio_review_summary"), dict) else {}
    if audio_review_summary:
        out["audio_review_summary"] = dict(audio_review_summary)
    return out



def _manifest_section_plan(payload: dict, audio_map: dict) -> list[dict]:
    explicit = payload.get("section_plan") if isinstance(payload.get("section_plan"), list) else None
    if explicit is not None:
        return list(explicit)
    raw_sections = audio_map.get("sections") if isinstance(audio_map, dict) else None
    if isinstance(raw_sections, list) and any(_is_real_section_row(row) for row in raw_sections):
        duration_sec = float(audio_map.get("duration_sec", 16.0) or 16.0)
        return normalized_sections(audio_map, duration_sec)
    return []


def _is_real_section_row(row: object) -> bool:
    if not isinstance(row, dict):
        return False
    try:
        start_sec = float(row.get("start_sec"))
        end_sec = float(row.get("end_sec"))
    except Exception:
        return False
    return end_sec > start_sec
