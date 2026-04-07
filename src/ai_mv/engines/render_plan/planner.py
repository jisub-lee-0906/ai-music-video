from __future__ import annotations

from ai_mv.core.contracts.visual_plan_normalize import normalize_prompt_plan
from ai_mv.core.director_brief import build_director_brief_intent
from ai_mv.core.stages.render_verbalizer import verbalize_ref_prompts, verbalize_wan_prompts
from ai_mv.infra.codex_cli_client import generate_structured


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
                "shot_function": str(shot.get("shot_function", "")).strip(),
                "place": str(shot.get("place", "")).strip(),
                "action": str(shot.get("action", "")).strip(),
                "carry": str(shot.get("carry", "")).strip(),
                "framing": str(shot.get("framing", "")).strip(),
                "ref_prompt_text": "",
            }
        )
    _verbalize_ref_items(config, ref_items)
    _naturalize_ref_items(config, ref_items)

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
                "place": str(current.get("place", "")).strip() or str(previous.get("place", "")).strip(),
                "bridge_action": _bridge_action(previous, current),
                "carry": str(current.get("carry", "")).strip() or str(previous.get("carry", "")).strip(),
                "wan_positive_prompt_text": "",
            }
        )
    _verbalize_wan_items(config, wan_items)
    ref_by_id = {
        str(row.get("shot_id", "")).strip(): row
        for row in ref_items
        if str(row.get("shot_id", "")).strip()
    }
    _naturalize_wan_items(config, wan_items, ref_by_id)

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
    prompts = verbalize_ref_prompts(config, ref_items)
    for row in ref_items:
        row["ref_prompt_text"] = str(prompts.get(row["shot_id"], "")).strip()


def _naturalize_ref_items(config: dict, ref_items: list[dict]) -> None:
    render = config.get("render", {}) if isinstance(config, dict) else {}
    if not isinstance(render, dict) or not bool(render.get("ref_naturalize", False)):
        return
    rows = [row for row in ref_items if str(row.get("shot_id", "")).strip() and str(row.get("ref_prompt_text", "")).strip()]
    if not rows:
        return
    for row in rows:
        try:
            rewritten = generate_structured(config, _ref_naturalize_prompt(row), _ref_naturalize_schema(row), attempts=1)
        except Exception:
            continue
        text = _normalize_ref_naturalize_result(rewritten, row)
        if text:
            row["ref_prompt_text"] = text


def _verbalize_wan_items(config: dict, wan_items: list[dict]) -> None:
    prompts = verbalize_wan_prompts(config, wan_items)
    for row in wan_items:
        row["wan_positive_prompt_text"] = str(prompts.get(row["shot_id"], "")).strip()


def _naturalize_wan_items(config: dict, wan_items: list[dict], ref_by_id: dict[str, dict]) -> None:
    render = config.get("render", {}) if isinstance(config, dict) else {}
    if not isinstance(render, dict) or not bool(render.get("wan_naturalize", False)):
        return
    rows = [row for row in wan_items if str(row.get("shot_id", "")).strip() and str(row.get("wan_positive_prompt_text", "")).strip()]
    if not rows:
        return
    for row in rows:
        try:
            rewritten = generate_structured(
                config,
                _wan_naturalize_prompt(row, ref_by_id),
                _wan_naturalize_schema(row),
                attempts=1,
            )
        except Exception:
            continue
        text = _normalize_wan_naturalize_result(rewritten, row)
        if text:
            row["wan_positive_prompt_text"] = text


def _bridge_action(previous: dict, current: dict) -> str:
    current_action = str(current.get("action", "")).strip()
    if current_action:
        return current_action
    previous_action = str(previous.get("action", "")).strip()
    if previous_action:
        return previous_action
    return "continuing through the same place with one readable movement"


def _ref_naturalize_prompt(row: dict) -> str:
    shot_id = str(row.get("shot_id", "")).strip()
    section_label = str(row.get("section_label", "")).strip()
    place = str(row.get("place", "")).strip()
    action = str(row.get("action", "")).strip()
    carry = str(row.get("carry", "")).strip()
    framing = str(row.get("framing", "")).strip()
    literal_image = str(row.get("literal_image", "")).strip()
    base = str(row.get("ref_prompt_text", "")).strip()
    return (
        "Rewrite this REF prompt into more natural cinematic English while preserving the same exact shot meaning. "
        "Do not invent new people, props, places, actions, camera setups, or story beats. "
        "Do not change the subject identity or introduce gendered terms that are not already present in the base prompt. "
        "Make each prompt read like a fluent image-generation prompt instead of a mechanical summary. "
        "Do not restate the same object twice in consecutive sentences unless the carry is truly necessary for continuity. "
        "Let the detail sentence and the carry sentence do different jobs: one should deepen the image, and the other should preserve continuity. "
        "Prefer one clear action and one clear physical image per shot over stacking multiple similar phrases. "
        "Keep the tone grounded and cinematic, not explanatory or analytical. "
        "Preserve the final face-lock sentence exactly as it already appears in the base prompt. "
        "Return strict JSON only. "
        f"Shot: shot_id={shot_id} | section={section_label} | place={place} | action={action} | carry={carry} | framing={framing} | detail={literal_image} | base_prompt={base}"
    )


def _ref_naturalize_schema(row: dict) -> dict:
    shot_id = str(row.get("shot_id", "")).strip()
    return {
        "type": "object",
        "required": ["shot_id", "prompt_text"],
        "properties": {
            "shot_id": {"type": "string", "enum": [shot_id]},
            "prompt_text": {"type": "string"},
        },
    }


def _normalize_ref_naturalize_result(raw: dict, row: dict) -> str:
    if not isinstance(raw, dict):
        return ""
    shot_id = str(raw.get("shot_id", "")).strip()
    expected = str(row.get("shot_id", "")).strip()
    prompt_text = str(raw.get("prompt_text", "")).strip()
    if not shot_id or shot_id != expected or not prompt_text:
        return ""
    face_lock = _face_lock_suffix(str(row.get("ref_prompt_text", "")).strip())
    if face_lock and not prompt_text.endswith(face_lock):
        return ""
    return prompt_text


def _face_lock_suffix(prompt_text: str) -> str:
    text = str(prompt_text).strip()
    if text.endswith("Keep the face."):
        return "Keep the face."
    if text.endswith("Keep the faces consistent."):
        return "Keep the faces consistent."
    return ""


def _wan_naturalize_prompt(row: dict, ref_by_id: dict[str, dict]) -> str:
    shot_id = str(row.get("shot_id", "")).strip()
    section_label = str(row.get("section_label", "")).strip()
    start_ref = str(row.get("start_ref_shot_id", "")).strip()
    end_ref = str(row.get("end_ref_shot_id", "")).strip()
    place = str(row.get("place", "")).strip()
    action = str(row.get("bridge_action", "")).strip()
    carry = str(row.get("carry", "")).strip()
    base = str(row.get("wan_positive_prompt_text", "")).strip()
    start_ref_text = str(ref_by_id.get(start_ref, {}).get("ref_prompt_text", "")).strip()
    end_ref_text = str(ref_by_id.get(end_ref, {}).get("ref_prompt_text", "")).strip()
    return (
        "Rewrite this WAN bridge prompt into more natural cinematic English while preserving the same exact transition meaning. "
        "Do not invent new places, props, actions, camera setups, or story beats. "
        "Do not change the subject identity or introduce gendered terms that are not already present in the base prompt. "
        "Keep the prompt focused on continuity between adjacent keyframes rather than restating the whole scene. "
        "Make the bridge feel like a readable transition from one keyframe to the next, not a duplicate of the REF prompt. "
        "Prefer one clear motion and one continuity detail. "
        "Use the start_ref and end_ref context to emphasize what changes between the two keyframes. "
        "Do not add a face-lock line such as 'Keep the face.' or any lens, lighting, or film-finish sentence unless it is already present in the base prompt. "
        "Keep the tone grounded and cinematic, not analytical. "
        "Return strict JSON only. "
        f"Item: shot_id={shot_id} | section={section_label} | pair={start_ref}->{end_ref} | place={place} | action={action} | carry={carry} | "
        f"start_ref={start_ref_text} | end_ref={end_ref_text} | base_prompt={base}"
    )


def _wan_naturalize_schema(row: dict) -> dict:
    shot_id = str(row.get("shot_id", "")).strip()
    return {
        "type": "object",
        "required": ["shot_id", "prompt_text"],
        "properties": {
            "shot_id": {"type": "string", "enum": [shot_id]},
            "prompt_text": {"type": "string"},
        },
    }


def _normalize_wan_naturalize_result(raw: dict, row: dict) -> str:
    if not isinstance(raw, dict):
        return ""
    shot_id = str(raw.get("shot_id", "")).strip()
    expected = str(row.get("shot_id", "")).strip()
    prompt_text = str(raw.get("prompt_text", "")).strip()
    if not shot_id or shot_id != expected or not prompt_text:
        return ""
    return prompt_text
