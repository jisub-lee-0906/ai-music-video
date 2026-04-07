from __future__ import annotations

from ai_mv.core.contracts.visual_plan_normalize import normalize_prompt_plan
from ai_mv.core.director_brief import build_director_brief_intent
from ai_mv.core.stages.render_verbalizer import verbalize_ref_prompt_pairs, verbalize_wan_prompts


def build_prompt_plan(config: dict, payload: dict) -> dict:
    brief = build_director_brief_intent(config)
    direction_plan = payload["direction_plan"]
    ref_items: list[dict] = []
    for shot in direction_plan.get("shot_packages", []):
        ref_items.append(
            {
                "shot_id": str(shot.get("shot_id", "")).strip(),
                "section_name": str(shot.get("section_name", "")).strip(),
                "section_label": str(shot.get("section_label", "")).strip(),
                "line_refs": list(shot.get("line_refs", [])),
                "lyric_lines": list(shot.get("lyric_lines", [])),
                "literal_image": str(shot.get("literal_image", "")).strip(),
                "visible_action": str(shot.get("visible_action", "")).strip(),
                "emotional_turn": str(shot.get("emotional_turn", "")).strip(),
                "continuity_anchor": str(shot.get("continuity_anchor", "")).strip(),
                "payoff_role": str(shot.get("payoff_role", "")).strip(),
                "duration_sec": float(shot.get("duration_sec", 2.0) or 2.0),
                "story_function": str(shot.get("story_function", "")).strip(),
                "story_goal": str(shot.get("story_goal", "")).strip(),
                "story_event": str(shot.get("story_event", "")).strip(),
                "world_zone": str(shot.get("world_zone", "")).strip(),
                "shot_function": str(shot.get("shot_function", "")).strip(),
                "place": str(shot.get("place", "")).strip(),
                "action": str(shot.get("action", "")).strip(),
                "carry": str(shot.get("carry", "")).strip(),
                "why": str(shot.get("why", "")).strip(),
                "ref_start_prompt_text": "",
                "ref_end_prompt_text": "",
            }
        )
    _verbalize_ref_items(config, ref_items)

    wan_items: list[dict] = []
    for index, current in enumerate(ref_items[1:], start=2):
        previous = ref_items[index - 2]
        wan_items.append(
            {
                "shot_id": str(current.get("shot_id", "")).strip(),
                "section_name": str(current.get("section_name", "")).strip(),
                "section_label": str(current.get("section_label", "")).strip(),
                "start_ref_shot_id": str(previous.get("shot_id", "")).strip(),
                "end_ref_shot_id": str(current.get("shot_id", "")).strip(),
                "duration_sec": float(current.get("duration_sec", 2.0) or 2.0),
                "story_function": str(current.get("story_function", "")).strip(),
                "story_event": str(current.get("story_event", "")).strip(),
                "place": str(current.get("place", "")).strip() or str(previous.get("place", "")).strip(),
                "bridge_action": _bridge_action(previous, current),
                "carry": str(current.get("carry", "")).strip() or str(previous.get("carry", "")).strip(),
                "why": f"Bridge {previous.get('shot_id', '')} to {current.get('shot_id', '')} in the same visual thread.",
                "wan_positive_prompt_text": "",
            }
        )
    _verbalize_wan_items(config, wan_items)

    return normalize_prompt_plan(
        {
            "master_anchor": {
                "render_strategy": "tti_master",
                "identity_core": str(brief.get("identity_core", "")).strip(),
                "style_contract": str(brief.get("style_contract", "")).strip(),
                "environment_anchor": "plain neutral studio background",
            },
            "ref_items": ref_items,
            "wan_items": wan_items,
        }
    )


def build_render_plan(config: dict, payload: dict) -> dict:
    return build_prompt_plan(config, payload)


def build_prompt_plan_preview_prompt(config: dict, payload: dict) -> str:
    return (
        "Turn each direction beat into a compact REF prompt and each adjacent pair into a compact WAN bridge prompt. "
        "Keep only place, action, carry-over detail, and final prompt text."
    )


def build_render_plan_preview_prompt(config: dict, payload: dict) -> str:
    return build_prompt_plan_preview_prompt(config, payload)


def _verbalize_ref_items(config: dict, ref_items: list[dict]) -> None:
    prompts = verbalize_ref_prompt_pairs(config, ref_items)
    for row in ref_items:
        prompt = prompts.get(row["shot_id"], {})
        row["ref_start_prompt_text"] = str(prompt.get("start_prompt_text", "")).strip()
        row["ref_end_prompt_text"] = str(prompt.get("end_prompt_text", "")).strip()


def _verbalize_wan_items(config: dict, wan_items: list[dict]) -> None:
    prompts = verbalize_wan_prompts(config, wan_items)
    for row in wan_items:
        row["wan_positive_prompt_text"] = str(prompts.get(row["shot_id"], "")).strip()


def _bridge_action(previous: dict, current: dict) -> str:
    current_action = str(current.get("action", "")).strip()
    if current_action:
        return current_action
    previous_action = str(previous.get("action", "")).strip()
    if previous_action:
        return previous_action
    return "continuing through the same place with one readable movement"
