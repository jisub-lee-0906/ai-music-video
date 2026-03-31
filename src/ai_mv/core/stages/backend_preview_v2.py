from __future__ import annotations

from ai_mv.core.contracts.stage_io import StageInput, StageOutput
from ai_mv.core.director_brief import build_director_brief_intent
from ai_mv.core.stages.flux2_ref_chain_v2 import (
    _literal_scene_description,
)
from ai_mv.core.stages.payload_views import merge_planner_prompt
from ai_mv.core.stages.wan_interpolation_v2 import _wan_negative_prompt, _wan_positive_prompt


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
                "positive_prompt_preview": _wan_positive_prompt(brief, row),
                "negative_prompt_preview": _wan_negative_prompt(brief),
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


def _join_sentences(*parts: object) -> str:
    out: list[str] = []
    for part in parts:
        sentence = _sentence(part)
        if sentence:
            out.append(sentence)
    return " ".join(out)


def _performance_action(shot: dict) -> str:
    action = str(shot.get("performance_intent", "")).strip()
    if action:
        lowered = action[:1].lower() + action[1:] if action else action
        return lowered.rstrip(".")
    return "holds one readable action while the space reacts around her"


def _ref_start_preview(brief: dict, shot: dict) -> str:
    return _join_sentences(
        f"In {_literal_scene_description(shot)}",
        f"{brief['ref_subject_intro']}",
        str(shot.get("ref_start_action_line", "")).strip() or str(shot.get("subject_action", "")).strip() or str(shot.get("visible_action", "")).strip(),
        str(shot.get("ref_lighting_line", "")).strip() or str(shot.get("lighting_intent", "")).strip(),
    )


def _ref_end_preview(brief: dict, shot: dict) -> str:
    return _join_sentences(
        f"In {_literal_scene_description(shot)}",
        f"{brief['ref_subject_intro']}",
        str(shot.get("ref_end_action_line", "")).strip() or str(shot.get("subject_action", "")).strip() or str(shot.get("visible_action", "")).strip(),
        str(shot.get("ref_lighting_line", "")).strip() or str(shot.get("lighting_intent", "")).strip(),
    )
