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
        action = _performance_action(shot)
        ref_preview.append(
            {
                "shot_id": shot["shot_id"],
                "render_strategy": "ref_pair",
                "start_prompt_preview": (
                    f"The same Korean female idol, now grounded inside {shot['environment_anchor']}. "
                    f"{_sentence(shot['camera_intent'])} "
                    "Cinematic live-action still frame, natural skin response, grounded environmental realism."
                ),
                "end_prompt_preview": (
                    f"The same Korean female idol, now {action.rstrip('.')} inside {shot['environment_anchor']}. "
                    f"{_sentence(shot['camera_intent'])} "
                    "Cinematic live-action still frame, natural skin response, grounded environmental realism."
                ),
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
                    f"Camera {row['camera_intent'].rstrip('.')} in stable cinematic motion. "
                    f"She {_performance_action(row)}. "
                    f"Background {row['environment_anchor'].rstrip('.')}"
                ),
                "negative_prompt_preview": "morphing, melting, static, anatomy collapse, warped hands, extra limbs, identity drift, toy-like cgi",
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
