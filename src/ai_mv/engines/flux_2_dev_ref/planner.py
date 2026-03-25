from __future__ import annotations

from ai_mv.core.contracts.prompt_normalize import normalize_flux2_ref_items
from ai_mv.core.contracts.prompt_schema import flux2_ref_schema
from ai_mv.engines.flux_2_dev_ref.prompting import (
    _anchor_summary,
    _anchor_summary_row,
    _chain_key,
    _clip_phase,
    _flux2_ref_planner_batch_size,
    _planner_prompt,
    _sentence,
)
from ai_mv.infra.codex_cli_client import generate_structured


def build_flux2_ref_plan(config: dict, payload: dict) -> dict:
    routes = [dict(row) for row in payload.get("clip_routes", []) if isinstance(row, dict) and bool(row.get("use_ref", False))]
    if not routes:
        return {"items": []}
    spec = _generate_ref_spec(config, payload, routes)
    keyed = normalize_flux2_ref_items(spec.get("items", []), routes)
    items = [_build_item(route, keyed[str(route["shot_id"])], idx) for idx, route in enumerate(routes, start=1)]
    return {"items": items}


def _generate_ref_spec(config: dict, payload: dict, anchors: list[dict], attempts: int = 3) -> dict:
    prompt = _planner_prompt(config, payload, anchors, "")
    expected_ids = [str(anchor["shot_id"]) for anchor in anchors]
    current_prompt = prompt
    last_exc: Exception | None = None
    for attempt in range(1, max(1, int(attempts)) + 1):
        spec = generate_structured(config, current_prompt, flux2_ref_schema(), attempts=1)
        try:
            keyed = normalize_flux2_ref_items(spec.get("items", []), anchors)
            for shot_id in expected_ids:
                row = keyed[shot_id]
                if "+" in str(row["prompt_text"]) or "+" in str(row["action_clause"]) or "+" in str(row["camera_clause"]):
                    raise RuntimeError(f"plus-sign formatting mismatch: {shot_id}")
                if str(row["prompt_text"]).strip() != _compose_prompt_text(
                    row["subject_clause"],
                    row["action_clause"],
                    row["camera_clause"],
                    row["continuity_clause"],
                ):
                    raise RuntimeError(f"prompt_text formula mismatch: {shot_id}")
            return spec
        except RuntimeError as exc:
            last_exc = exc
            if attempt >= attempts:
                raise
            actual_ids = [
                str(row.get("shot_id", "")).strip()
                for row in spec.get("items", [])
                if isinstance(row, dict) and str(row.get("shot_id", "")).strip()
            ]
            current_prompt = (
                f"{prompt}\n\n"
                "Previous output failed validation. "
                f"Failure={exc}. "
                f"Expected shot_id order={', '.join(expected_ids)}. "
                f"Previous shot_id order={', '.join(actual_ids)}. "
                "Rewrite the JSON only and follow the exact prompt_text formula."
            )
    if last_exc is not None:
        raise last_exc
    raise RuntimeError("flux2_ref planner failed without validation error")


def _build_item(anchor: dict, row: dict, timeline_index: int) -> dict:
    ref = str(anchor.get("identity_anchor", anchor["anchor"]))
    return {
        "shot_id": anchor["shot_id"],
        "chain_key": _chain_key(anchor),
        "timeline_index": int(timeline_index),
        "anchor": anchor["anchor"],
        "ref": ref,
        "style_ref": "",
        "prompt_text": str(row["prompt_text"]),
        "style_clause": "",
        "subject_clause": str(row["subject_clause"]),
        "action_clause": str(row["action_clause"]),
        "camera_clause": str(row["camera_clause"]),
        "environment_clause": "",
        "continuity_clause": str(row["continuity_clause"]),
        "duration_sec": float(anchor["duration_sec"]),
        "clip_index": int(anchor.get("clip_index", 1)),
        "clip_count": int(anchor.get("clip_count", 1)),
        "clip_phase": _clip_phase(anchor),
        "shot_type": str(anchor["shot_type"]),
        "section_name": str(anchor.get("section_name", "section")),
        "section_label": str(anchor.get("section_label", anchor.get("section_name", "section"))),
        "is_chorus": bool(anchor.get("is_chorus", False)),
        "camera_language": str(anchor.get("camera_language", "")),
        "pose_delta": str(anchor.get("pose_delta", "")),
        "emotion": str(anchor.get("emotion", "")),
        "scene_detail": str(anchor.get("scene_detail", "")),
        "motion_hint": str(anchor.get("motion_hint", "")),
        "space_relation": str(anchor.get("space_relation", "")),
        "kinetic_transition": str(anchor.get("kinetic_transition", "")),
        "lighting_fx": str(anchor.get("lighting_fx", "")),
        "kinetic_intensity": str(anchor.get("kinetic_intensity", "")),
        "route_reason": str(anchor.get("route_reason", "")),
        "scene_change_level": str(anchor.get("scene_change_level", "evolve")),
        "anchor_strategy": str(anchor.get("anchor_strategy", "refine_anchor")),
        "continuity_basis": str(anchor.get("continuity_basis", "world")),
    }


def _compose_prompt_text(subject_clause: str, action_clause: str, camera_clause: str, continuity_clause: str) -> str:
    subject = " ".join(str(subject_clause).strip().split())
    action = " ".join(str(action_clause).strip().split())
    if action and not action.lower().startswith(("now ", "while ", "as ")):
        action = f"now {action}"
    if subject and action:
        lead = f"{subject}, {action}"
    else:
        lead = subject or action
    parts = [lead, camera_clause.strip(), continuity_clause.strip()]
    return " ".join(_sentence(part) for part in parts if part).strip()
