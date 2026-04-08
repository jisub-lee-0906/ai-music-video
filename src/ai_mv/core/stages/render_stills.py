from __future__ import annotations

from ai_mv.core.contracts.stage_io import StageInput, StageOutput
from ai_mv.core.output_paths import qwen_still_prefix
from ai_mv.engines.qwen_image.runner import run_qwen_still


def run_render_stills(stage_input: StageInput) -> StageOutput:
    shot_plan = [row for row in stage_input.payload.get("shot_plan", []) if isinstance(row, dict)]
    render_plan = [row for row in stage_input.payload.get("render_plan", []) if isinstance(row, dict)]
    render_map = {str(row.get("shot_id", "")).strip(): row for row in render_plan}
    still_results = []
    for shot in shot_plan:
        shot_id = str(shot.get("shot_id", "")).strip()
        render_item = render_map.get(shot_id, {})
        prompt_text = _still_prompt_text(render_item)
        image_path = run_qwen_still(
            stage_input.config,
            {
                "shot_id": shot_id,
                "positive_prompt": prompt_text,
                "negative_prompt": str(stage_input.config.get("render", {}).get("qwen_negative", "")).strip(),
                "filename_prefix": qwen_still_prefix(shot_id),
                "seed": int(render_item.get("seed", 0) or 0),
                "qwen_size": str(stage_input.config.get("render", {}).get("qwen_size", "")).strip(),
            },
        )
        still_results.append(
            {
                "shot_id": shot_id,
                "image": image_path,
                "prompt_seed": str(render_item.get("prompt_seed", "")).strip(),
                "prompt_text": prompt_text,
                "status": "done",
            }
        )
    return StageOutput(
        "render_stills",
        "done",
        {
            "still_results": still_results,
            "workflow_inputs": {
                **dict(stage_input.payload.get("workflow_inputs", {})),
                "stills": {"count": len(still_results)},
            },
        },
        [],
    )


def _still_prompt_text(render_item: dict) -> str:
    for key in ("prompt_polish", "prompt_draft", "prompt_seed"):
        value = str(render_item.get(key, "")).strip()
        if value:
            return value
    return "japanese 80s city pop illustration, neon coast, bittersweet summer night"
