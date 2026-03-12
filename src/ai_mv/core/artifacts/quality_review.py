from __future__ import annotations

from ai_mv.core.artifacts.paths import latest_file, run_file
from ai_mv.utils.json_utils import write_json


def write_quality_review(state: dict, review: dict) -> None:
    write_json(run_file(state["run_id"], "quality_review.json"), review)
    write_json(latest_file("quality_review.json"), review)
