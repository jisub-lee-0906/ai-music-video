from __future__ import annotations

from ai_mv.core.artifacts.paths import latest_file, latest_success_file, run_file
from ai_mv.utils.json_utils import write_json


def write_director_cards_preview(state: dict, payload: dict) -> None:
    cards = list(payload.get("director_cards_preview", []))
    if not cards:
        return
    scope = str(state.get("scope", "run"))
    data = {"run_id": state["run_id"], "director_cards": cards}
    write_json(run_file(state["run_id"], "director_cards_preview.json", scope), data)
    write_json(latest_file("director_cards_preview.json", scope), data)
    if str(state.get("status", "")) == "done":
        write_json(latest_success_file("director_cards_preview.json", scope), data)
