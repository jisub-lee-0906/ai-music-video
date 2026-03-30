from __future__ import annotations

from ai_mv.core.contracts.stage_io import StageInput, StageOutput
from ai_mv.core.director_brief import build_director_brief_intent
from ai_mv.core.stages.payload_views import merge_planner_prompt


def run_backend_preview_v2(stage_input: StageInput) -> StageOutput:
    preview = build_backend_preview_v2(stage_input.config, stage_input.payload)
    workflow_v2 = dict(stage_input.payload.get("workflow_inputs_v2", {}))
    workflow_v2["backend_preview_v2"] = preview
    return StageOutput(
        "backend_preview_v2",
        "done",
        {
            "backend_preview_v2": preview,
            "workflow_inputs_v2": workflow_v2,
            "planner_prompts": merge_planner_prompt(
                stage_input.payload,
                "backend_preview_v2",
                {"prompt": "Translate the v2 shot packages into TTI, REF, and WAN preview prompts without submitting any workflow."},
            ),
        },
        [],
    )


def build_backend_preview_v2(config: dict, payload: dict) -> dict:
    brief = build_director_brief_intent(config)
    render_plan = payload["render_plan_v2"]
    shots = [row for row in render_plan.get("shot_packages", []) if isinstance(row, dict)]
    tti_preview = {
        "render_strategy": "tti_master",
        "prompt_text": (
            f"{brief['style_contract']}. {brief['identity_core']}. "
            "Neutral presentation pose, pale grey backdrop, soft controlled studio lighting, clean full-body cinematic key reference."
        ),
    }
    ref_preview = []
    for shot in shots:
        ref_preview.append(
            {
                "shot_id": shot["shot_id"],
                "render_strategy": "ref_pair",
                "start_prompt_preview": _ref_start_preview(brief, shot),
                "end_prompt_preview": _ref_end_preview(brief, shot),
            }
        )
    wan_preview = []
    for row in render_plan.get("wan_chain", []):
        if not isinstance(row, dict):
            continue
        wan_preview.append(
            {
                "shot_id": row["shot_id"],
                "render_strategy": "wan_chain",
                "start_source": row["start_source"],
                "previous_chain_key": row.get("previous_chain_key", ""),
                "positive_prompt_preview": (
                    f"Camera {row['camera_intent'].rstrip('.')} in {brief['wan_motion_style'].rstrip('.')} "
                    f"{_wan_carryover_clause(row)} "
                    f"{_wan_anchor_clause(row)} "
                    f"{_wan_change_clause(row)} "
                    f"She {_performance_action(row)}. "
                    f"Background {row['environment_anchor'].rstrip('.')}"
                ),
                "negative_prompt_preview": brief["wan_negative"],
            }
        )
    return {
        "tti_adapter_v2": tti_preview,
        "ref_adapter_v2": ref_preview,
        "wan_adapter_v2": wan_preview,
    }


def _sentence(text: str) -> str:
    cleaned = " ".join(str(text).strip().rstrip(". ").split())
    return f"{cleaned}." if cleaned else ""


def _performance_action(shot: dict) -> str:
    action = str(shot.get("performance_intent", "")).strip()
    if action:
        lowered = action[:1].lower() + action[1:] if action else action
        return lowered.rstrip(".")
    return "holds one readable action while the space reacts around her"


def _ref_start_preview(brief: dict, shot: dict) -> str:
    return (
        f"{brief['ref_subject_intro']} at the start of the shot, {_ref_start_action(shot)} inside {shot['environment_anchor']}. "
        f"{_sentence(_ref_carryover_clause(shot))} "
        f"{_sentence(_ref_anchor_clause(shot))} "
        f"{_sentence(_ref_change_clause(shot, 'start'))} "
        f"{_sentence(shot['camera_intent'])} "
        f"{_sentence(shot.get('lighting_intent', ''))} "
        f"{_sentence(brief.get('ref_frame_style', ''))}"
    )


def _ref_end_preview(brief: dict, shot: dict) -> str:
    return (
        f"{brief['ref_subject_intro']} at the end of the shot, {_performance_action(shot)} inside {shot['environment_anchor']}. "
        f"{_sentence(_ref_carryover_clause(shot))} "
        f"{_sentence(_ref_anchor_clause(shot))} "
        f"{_sentence(_ref_change_clause(shot, 'end'))} "
        f"{_sentence(shot['camera_intent'])} "
        f"{_sentence(shot.get('lighting_intent', ''))} "
        f"{_sentence(shot.get('transition_intent', ''))} "
        f"{_sentence(brief.get('ref_frame_style', ''))}"
    )


def _ref_start_action(shot: dict) -> str:
    zone = str(shot.get("zone", "")).strip().lower()
    if zone in {"threshold", "edge"}:
        return "holds a poised starting stance before the movement commits"
    if zone == "compression":
        return "keeps the body contained and the pose tightly controlled"
    return "holds a clear readable starting pose"


def _wan_carryover_clause(shot: dict) -> str:
    state = str(shot.get("carryover_state", "")).strip().rstrip(".")
    if not state:
        return ""
    if state.startswith("a clean "):
        return f"Begin from {state}."
    return f"Carry forward {state}."


def _wan_anchor_clause(shot: dict) -> str:
    anchor = str(shot.get("continuity_anchor", "")).strip().rstrip(".")
    return f"Keep continuity through {anchor}." if anchor else ""


def _wan_change_clause(shot: dict) -> str:
    change = str(shot.get("new_change", "")).strip().rstrip(".")
    return f"Introduce {change}." if change else ""


def _ref_carryover_clause(shot: dict) -> str:
    state = str(shot.get("carryover_state", "")).strip().rstrip(".")
    if not state:
        return ""
    if state.startswith("a clean "):
        return f"Begin from {state}"
    return f"Carry forward {state}"


def _ref_anchor_clause(shot: dict) -> str:
    anchor = str(shot.get("continuity_anchor", "")).strip()
    return f"Keep continuity through {anchor}" if anchor else ""


def _ref_change_clause(shot: dict, frame: str) -> str:
    change = str(shot.get("new_change", "")).strip()
    if not change:
        return ""
    if frame == "start":
        return f"Introduce only {change}"
    return f"Complete {change}"
