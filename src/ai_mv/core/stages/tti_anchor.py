from __future__ import annotations

from ai_mv.core.contracts.stage_io import StageInput, StageOutput
from ai_mv.core.stages.payload_views import merge_planner_prompt
from ai_mv.engines.flux_2_dev_tti.runner import run_tti


def run_tti_anchor(stage_input: StageInput) -> StageOutput:
    plan = build_tti_anchor_plan(stage_input.config, stage_input.payload)
    anchors = run_tti(stage_input.config, plan)
    master_anchor = str(anchors[0]["identity_anchor"]) if anchors else ""
    workflow_inputs = dict(stage_input.payload.get("workflow_inputs", {}))
    workflow_inputs["tti_anchor"] = {
        "master_prompt": str(plan["master_anchor"]["prompt_text"]),
        "shot_count": len(plan["shots"]),
        "master_anchor": master_anchor,
    }
    return StageOutput(
        "tti_anchor",
        "done",
        {
            "anchors": anchors,
            "master_anchor": master_anchor,
            "workflow_inputs": workflow_inputs,
            "planner_prompts": merge_planner_prompt(
                stage_input.payload,
                "tti_anchor",
                {"prompt": str(plan["master_anchor"]["prompt_text"])},
            ),
        },
        [],
    )


def build_tti_anchor_plan(config: dict, payload: dict) -> dict:
    shots = [row for row in payload.get("prompt_plan", {}).get("ref_items", []) if isinstance(row, dict)]
    tti_shots = []
    for idx, shot in enumerate(shots, start=1):
        section_label = str(shot.get("section_label", "")).strip()
        tti_shots.append(
            {
                "shot_id": str(shot.get("shot_id", "")).strip(),
                "shot_type": "DETAIL_INSERT",
                "section_name": str(shot.get("section_name", "")).strip(),
                "section_label": section_label,
                "duration_sec": float(shot.get("duration_sec", 2.0) or 2.0),
                "is_chorus": "chorus" in section_label.lower(),
                "seed": idx,
            }
        )
    return {
        "master_anchor": {
            "prompt_text": build_tti_anchor_master_prompt(config),
            "seed": 1,
        },
        "shots": tti_shots,
    }


def build_tti_anchor_master_prompt(config: dict) -> str:
    voice = str(config.get("voice", "")).strip() if isinstance(config, dict) else ""
    anchor_parts = [
        _anchor_subject(config, voice),
        str(config.get("anchor_hair", "")).strip() if isinstance(config, dict) else "",
    ]
    wardrobe_parts = [
        str(config.get("anchor_top", "")).strip() if isinstance(config, dict) else "",
        str(config.get("anchor_bottom", "")).strip() if isinstance(config, dict) else "",
        str(config.get("anchor_shoes", "")).strip() if isinstance(config, dict) else "",
    ]
    anchor_description = ", ".join(part for part in anchor_parts if part)
    wardrobe_description = ", ".join(part for part in wardrobe_parts if part)
    pose = str(config.get("anchor_pose", "")).strip() if isinstance(config, dict) else ""
    background = str(config.get("anchor_background", "")).strip() if isinstance(config, dict) else ""
    clauses = [
        anchor_description,
        f"wearing {wardrobe_description}" if wardrobe_description else "",
        pose or "full-body standing pose, slight side angle, both hands visible, shoes fully visible",
        background or "plain neutral studio background, no props, no environmental elements",
        "soft controlled lighting",
        "clean silhouette",
        "clear face readability",
        "readable outfit and footwear",
        "for later reference images",
    ]
    return ", ".join(part for part in clauses if str(part).strip()) + "."


def _anchor_subject(config: dict, voice: str) -> str:
    if isinstance(config, dict) and str(config.get("anchor_subject", "")).strip():
        return str(config.get("anchor_subject", "")).strip()
    low = voice.lower()
    if "duo" in low:
        return "young adult vocal duo"
    if "group" in low or "mixed" in low:
        return "young adult vocal group"
    if "solo female" in low:
        return "young adult female vocalist"
    if "solo male" in low:
        return "young adult male vocalist"
    if "female" in low:
        return "young adult female vocalist"
    if "male" in low:
        return "young adult male vocalist"
    if "duo" in low or "group" in low or "mixed" in low:
        return "vocal group"
    return "young adult vocalist"
