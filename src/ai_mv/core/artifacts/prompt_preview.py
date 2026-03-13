from __future__ import annotations

from ai_mv.core.artifacts.paths import latest_file, run_file
from ai_mv.utils.json_utils import write_json


def write_prompt_preview(state: dict, payload: dict) -> None:
    scope = str(state.get("scope", "run"))
    data = {
        "run_id": state["run_id"],
        "prompts": dict(payload.get("planner_prompts", {})),
    }
    write_json(run_file(state["run_id"], "prompt_preview.json", scope), data)
    write_json(latest_file("prompt_preview.json", scope), data)
