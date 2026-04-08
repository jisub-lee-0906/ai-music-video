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
                "segment_focus": str(shot.get("segment_focus", "")).strip(),
                "ref_prompt_text": "",
            }
        )
    _verbalize_ref_items(config, ref_items)
    _draft_ref_items(config, ref_items)
    _polish_ref_items(config, ref_items)

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
    _draft_wan_items(config, wan_items, ref_by_id)
    _polish_wan_items(config, wan_items)

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


def _draft_ref_items(config: dict, ref_items: list[dict]) -> None:
    render = config.get("render", {}) if isinstance(config, dict) else {}
    if not isinstance(render, dict) or not bool(render.get("ref_naturalize", False)):
        return
    rows = [row for row in ref_items if str(row.get("shot_id", "")).strip() and str(row.get("ref_prompt_text", "")).strip()]
    if not rows:
        return
    for row in rows:
        try:
            rewritten = generate_structured(config, _ref_draft_prompt(row), _ref_draft_schema(row), attempts=1)
        except Exception:
            continue
        text = _normalize_ref_draft_result(rewritten, row)
        if text:
            row["ref_prompt_text"] = text


def _polish_ref_items(config: dict, ref_items: list[dict]) -> None:
    render = config.get("render", {}) if isinstance(config, dict) else {}
    if not isinstance(render, dict) or not bool(render.get("ref_polish", False)):
        return
    rows = [row for row in ref_items if str(row.get("shot_id", "")).strip() and str(row.get("ref_prompt_text", "")).strip()]
    if not rows:
        return
    for row in rows:
        try:
            rewritten = generate_structured(config, _ref_polish_prompt(row), _ref_polish_schema(row), attempts=1)
        except Exception:
            continue
        text = _normalize_ref_polish_result(rewritten, row)
        if text:
            row["ref_prompt_text"] = text


def _verbalize_wan_items(config: dict, wan_items: list[dict]) -> None:
    prompts = verbalize_wan_prompts(config, wan_items)
    for row in wan_items:
        row["wan_positive_prompt_text"] = str(prompts.get(row["shot_id"], "")).strip()


def _draft_wan_items(config: dict, wan_items: list[dict], ref_by_id: dict[str, dict]) -> None:
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
                _wan_draft_prompt(row, ref_by_id),
                _wan_draft_schema(row),
                attempts=1,
            )
        except Exception:
            continue
        text = _normalize_wan_draft_result(rewritten, row)
        if text:
            row["wan_positive_prompt_text"] = text


def _polish_wan_items(config: dict, wan_items: list[dict]) -> None:
    render = config.get("render", {}) if isinstance(config, dict) else {}
    if not isinstance(render, dict) or not bool(render.get("wan_polish", False)):
        return
    rows = [row for row in wan_items if str(row.get("shot_id", "")).strip() and str(row.get("wan_positive_prompt_text", "")).strip()]
    if not rows:
        return
    for row in rows:
        try:
            rewritten = generate_structured(config, _wan_polish_prompt(row), _wan_polish_schema(row), attempts=1)
        except Exception:
            continue
        text = _normalize_wan_polish_result(rewritten, row)
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


def _ref_draft_prompt(row: dict) -> str:
    shot_id = str(row.get("shot_id", "")).strip()
    section_label = str(row.get("section_label", "")).strip()
    place = str(row.get("place", "")).strip()
    action = str(row.get("action", "")).strip()
    carry = str(row.get("carry", "")).strip()
    framing = str(row.get("framing", "")).strip()
    segment_focus = str(row.get("segment_focus", "")).strip()
    literal_image = str(row.get("literal_image", "")).strip()
    base = str(row.get("ref_prompt_text", "")).strip()
    subject_seed = _subject_seed(base)
    return (
        "Write a final REF prompt in natural cinematic English from this shot card. "
        "Do not invent new people, props, places, actions, camera setups, or story beats. "
        "Do not change the subject identity or introduce gendered terms that are not already present in the base prompt. "
        "Preserve the same leading subject wording and grammatical person already used in the base prompt. "
        "Do not replace that lead with 'a woman', 'the woman', or 'the performer' if the base prompt already starts with a pronoun form. "
        "Do not introduce singular/plural or possessive mismatches like 'their' for a solo subject. "
        "Keep the same exact shot meaning and continuity anchor. "
        "Write the full prompt directly rather than editing the base prompt line by line. "
        "Make each prompt read like a fluent image-generation prompt instead of a mechanical summary. "
        "If nearby shots in the same location would otherwise feel too similar, make this prompt distinguish itself through a different immediate action emphasis, body focus, or physical detail focus without changing the underlying event. "
        "Prefer one dominant moment per shot instead of describing the whole beat the same way every time. "
        "Use complete, grammatically fluent English sentences rather than fragments or note-like phrases. "
        "Do not restate the same object twice in consecutive sentences unless the carry is truly necessary for continuity. "
        "Let the detail sentence and the carry sentence do different jobs: one should deepen the image, and the other should preserve continuity. "
        "Prefer concrete physical details over abstract emotional commentary; let mood emerge from the image instead of explaining it directly. "
        "Prefer one clear action and one clear physical image per shot over stacking multiple similar phrases. "
        "Keep the tone grounded and cinematic, not explanatory or analytical. "
        "End with the exact face-lock sentence from the base prompt. "
        "Return strict JSON only. "
        f"Shot: shot_id={shot_id} | section={section_label} | place={place} | action={action} | carry={carry} | framing={framing} | segment_focus={segment_focus} | detail={literal_image} | subject_seed={subject_seed} | base_prompt={base}"
    )


def _ref_draft_schema(row: dict) -> dict:
    shot_id = str(row.get("shot_id", "")).strip()
    return {
        "type": "object",
        "required": ["shot_id", "prompt_text"],
        "properties": {
            "shot_id": {"type": "string", "enum": [shot_id]},
            "prompt_text": {"type": "string"},
        },
    }


def _normalize_ref_draft_result(raw: dict, row: dict) -> str:
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
    subject_seed = _subject_seed(str(row.get("ref_prompt_text", "")).strip())
    if subject_seed and not prompt_text.startswith(subject_seed):
        return ""
    return prompt_text


def _ref_polish_prompt(row: dict) -> str:
    shot_id = str(row.get("shot_id", "")).strip()
    base = str(row.get("ref_prompt_text", "")).strip()
    subject_seed = _subject_seed(base)
    return (
        "Polish this REF prompt lightly. "
        "Keep the exact same shot meaning, identity, place, action, continuity, and face-lock. "
        "Do not invent anything new. "
        "Preserve the same leading subject wording and grammatical person already used in the prompt. "
        "Fix grammar, remove awkward phrasing, and smooth sentence flow only. "
        "Return strict JSON only. "
        f"Shot: shot_id={shot_id} | subject_seed={subject_seed} | prompt_text={base}"
    )


def _ref_polish_schema(row: dict) -> dict:
    return _ref_draft_schema(row)


def _normalize_ref_polish_result(raw: dict, row: dict) -> str:
    return _normalize_ref_draft_result(raw, row)


def _face_lock_suffix(prompt_text: str) -> str:
    text = str(prompt_text).strip()
    if text.endswith("Keep the face."):
        return "Keep the face."
    if text.endswith("Keep the faces consistent."):
        return "Keep the faces consistent."
    return ""


def _subject_seed(prompt_text: str) -> str:
    text = str(prompt_text).strip()
    for prefix in ("She is ", "He is ", "They are ", "The performer is "):
        if text.startswith(prefix):
            return prefix
    return ""


def _wan_draft_prompt(row: dict, ref_by_id: dict[str, dict]) -> str:
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
        "Write a final WAN bridge prompt in short natural English from this transition card. "
        "Do not invent new places, props, actions, camera setups, or story beats. "
        "Do not change the subject identity or introduce gendered terms that are not already present in the base prompt. "
        "Keep the same exact transition meaning between the two keyframes. "
        "Write the full bridge prompt directly rather than editing the base prompt line by line. "
        "Keep the prompt focused on continuity between adjacent keyframes rather than restating the whole scene. "
        "Make the bridge feel like a readable transition from one keyframe to the next, not a duplicate of the REF prompt. "
        "Use one or two short fluent sentences, not a long paragraph. "
        "Prefer one clear motion and one continuity detail only. "
        "Prefer concrete physical continuity details over abstract mood or style description. "
        "Use the start_ref and end_ref context to emphasize what changes between the two keyframes. "
        "Do not add a face-lock line such as 'Keep the face.' or any lens, lighting, or film-finish sentence unless it is already present in the base prompt. "
        "Avoid decorative wording, emotional explanation, and repeated scene-setting. "
        "Keep the tone grounded and direct. "
        "Return strict JSON only. "
        f"Item: shot_id={shot_id} | section={section_label} | pair={start_ref}->{end_ref} | place={place} | action={action} | carry={carry} | "
        f"start_ref={start_ref_text} | end_ref={end_ref_text} | base_prompt={base}"
    )


def _wan_draft_schema(row: dict) -> dict:
    shot_id = str(row.get("shot_id", "")).strip()
    return {
        "type": "object",
        "required": ["shot_id", "prompt_text"],
        "properties": {
            "shot_id": {"type": "string", "enum": [shot_id]},
            "prompt_text": {"type": "string"},
        },
    }


def _normalize_wan_draft_result(raw: dict, row: dict) -> str:
    if not isinstance(raw, dict):
        return ""
    shot_id = str(raw.get("shot_id", "")).strip()
    expected = str(row.get("shot_id", "")).strip()
    prompt_text = str(raw.get("prompt_text", "")).strip()
    if not shot_id or shot_id != expected or not prompt_text:
        return ""
    return prompt_text


def _wan_polish_prompt(row: dict) -> str:
    shot_id = str(row.get("shot_id", "")).strip()
    base = str(row.get("wan_positive_prompt_text", "")).strip()
    return (
        "Polish this WAN bridge prompt lightly. "
        "Keep the exact same transition meaning, identity, place, action, and continuity. "
        "Do not invent anything new. "
        "Keep it short and direct. "
        "Fix grammar, remove awkward phrasing, and smooth sentence flow only. "
        "Return strict JSON only. "
        f"Item: shot_id={shot_id} | prompt_text={base}"
    )


def _wan_polish_schema(row: dict) -> dict:
    return _wan_draft_schema(row)


def _normalize_wan_polish_result(raw: dict, row: dict) -> str:
    return _normalize_wan_draft_result(raw, row)
