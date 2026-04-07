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
    _naturalize_wan_items(config, wan_items)

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
    batch_size = max(1, int(render.get("ref_naturalize_batch_size", 12) or 12))
    for start in range(0, len(rows), batch_size):
        batch = rows[start : start + batch_size]
        try:
            rewritten = generate_structured(config, _ref_naturalize_prompt(batch), _ref_naturalize_schema(batch), attempts=1)
        except Exception:
            continue
        prompt_map = _normalize_ref_naturalize_result(rewritten, batch)
        for row in batch:
            text = str(prompt_map.get(str(row.get("shot_id", "")).strip(), "")).strip()
            if text:
                row["ref_prompt_text"] = text


def _verbalize_wan_items(config: dict, wan_items: list[dict]) -> None:
    prompts = verbalize_wan_prompts(config, wan_items)
    for row in wan_items:
        row["wan_positive_prompt_text"] = str(prompts.get(row["shot_id"], "")).strip()


def _naturalize_wan_items(config: dict, wan_items: list[dict]) -> None:
    render = config.get("render", {}) if isinstance(config, dict) else {}
    if not isinstance(render, dict) or not bool(render.get("wan_naturalize", False)):
        return
    rows = [row for row in wan_items if str(row.get("shot_id", "")).strip() and str(row.get("wan_positive_prompt_text", "")).strip()]
    if not rows:
        return
    batch_size = max(1, int(render.get("wan_naturalize_batch_size", 12) or 12))
    for start in range(0, len(rows), batch_size):
        batch = rows[start : start + batch_size]
        try:
            rewritten = generate_structured(config, _wan_naturalize_prompt(batch), _wan_naturalize_schema(batch), attempts=1)
        except Exception:
            continue
        prompt_map = _normalize_wan_naturalize_result(rewritten, batch)
        for row in batch:
            text = str(prompt_map.get(str(row.get("shot_id", "")).strip(), "")).strip()
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


def _ref_naturalize_prompt(rows: list[dict]) -> str:
    chunks: list[str] = []
    for idx, row in enumerate(rows, start=1):
        shot_id = str(row.get("shot_id", "")).strip()
        section_label = str(row.get("section_label", "")).strip()
        place = str(row.get("place", "")).strip()
        action = str(row.get("action", "")).strip()
        carry = str(row.get("carry", "")).strip()
        framing = str(row.get("framing", "")).strip()
        literal_image = str(row.get("literal_image", "")).strip()
        base = str(row.get("ref_prompt_text", "")).strip()
        chunks.append(
            f"{idx}. shot_id={shot_id} | section={section_label} | place={place} | action={action} | carry={carry} | framing={framing} | detail={literal_image} | base_prompt={base}"
        )
    return (
        "Rewrite each REF prompt into more natural cinematic English while preserving the same exact shot meaning. "
        "Do not invent new people, props, places, actions, camera setups, or story beats. "
        "Keep the sequence continuity implied by the order of shots. "
        "Make each prompt read like a fluent image-generation prompt instead of a mechanical summary. "
        "Make adjacent shots feel meaningfully distinct in action, emphasis, or image focus so the sequence does not flatten into repeated paraphrases. "
        "Do not restate the same object twice in two consecutive sentences unless the carry is truly necessary for continuity. "
        "Let the detail sentence and the carry sentence do different jobs: one should deepen the image, the other should preserve continuity. "
        "Prefer one clear action and one clear physical image per shot over stacking multiple similar phrases. "
        "Keep the tone grounded and cinematic, not explanatory or analytical. "
        "Preserve the final face-lock sentence exactly as it already appears in each base prompt. "
        "Return strict JSON only. "
        "Shots: "
        + " || ".join(chunks)
    )


def _ref_naturalize_schema(rows: list[dict]) -> dict:
    allowed = [str(row.get("shot_id", "")).strip() for row in rows if str(row.get("shot_id", "")).strip()]
    return {
        "type": "object",
        "required": ["items"],
        "properties": {
            "items": {
                "type": "array",
                "minItems": len(allowed),
                "maxItems": len(allowed),
                "items": {
                    "type": "object",
                    "required": ["shot_id", "prompt_text"],
                    "properties": {
                        "shot_id": {"type": "string", "enum": allowed},
                        "prompt_text": {"type": "string"},
                    },
                },
            }
        },
    }


def _normalize_ref_naturalize_result(raw: dict, rows: list[dict]) -> dict[str, str]:
    allowed = {str(row.get("shot_id", "")).strip(): str(row.get("ref_prompt_text", "")).strip() for row in rows}
    out: dict[str, str] = {}
    for item in raw.get("items", []) if isinstance(raw, dict) else []:
        if not isinstance(item, dict):
            continue
        shot_id = str(item.get("shot_id", "")).strip()
        prompt_text = str(item.get("prompt_text", "")).strip()
        if not shot_id or shot_id not in allowed or not prompt_text:
            continue
        face_lock = _face_lock_suffix(allowed[shot_id])
        if face_lock and not prompt_text.endswith(face_lock):
            continue
        out[shot_id] = prompt_text
    return out


def _face_lock_suffix(prompt_text: str) -> str:
    text = str(prompt_text).strip()
    if text.endswith("Keep the face."):
        return "Keep the face."
    if text.endswith("Keep the faces consistent."):
        return "Keep the faces consistent."
    return ""


def _wan_naturalize_prompt(rows: list[dict]) -> str:
    chunks: list[str] = []
    for idx, row in enumerate(rows, start=1):
        shot_id = str(row.get("shot_id", "")).strip()
        section_label = str(row.get("section_label", "")).strip()
        start_ref = str(row.get("start_ref_shot_id", "")).strip()
        end_ref = str(row.get("end_ref_shot_id", "")).strip()
        place = str(row.get("place", "")).strip()
        action = str(row.get("bridge_action", "")).strip()
        carry = str(row.get("carry", "")).strip()
        base = str(row.get("wan_positive_prompt_text", "")).strip()
        chunks.append(
            f"{idx}. shot_id={shot_id} | section={section_label} | pair={start_ref}->{end_ref} | place={place} | action={action} | carry={carry} | base_prompt={base}"
        )
    return (
        "Rewrite each WAN bridge prompt into more natural cinematic English while preserving the same exact transition meaning. "
        "Do not invent new places, props, actions, camera setups, or story beats. "
        "Keep the prompt focused on continuity between adjacent keyframes rather than restating the whole scene. "
        "Make the bridge feel like a readable transition from one keyframe to the next, not a duplicate of the REF prompt. "
        "Prefer one clear motion and one continuity detail. "
        "Keep the tone grounded and cinematic, not analytical. "
        "Return strict JSON only. "
        "Items: "
        + " || ".join(chunks)
    )


def _wan_naturalize_schema(rows: list[dict]) -> dict:
    allowed = [str(row.get("shot_id", "")).strip() for row in rows if str(row.get("shot_id", "")).strip()]
    return {
        "type": "object",
        "required": ["items"],
        "properties": {
            "items": {
                "type": "array",
                "minItems": len(allowed),
                "maxItems": len(allowed),
                "items": {
                    "type": "object",
                    "required": ["shot_id", "prompt_text"],
                    "properties": {
                        "shot_id": {"type": "string", "enum": allowed},
                        "prompt_text": {"type": "string"},
                    },
                },
            }
        },
    }


def _normalize_wan_naturalize_result(raw: dict, rows: list[dict]) -> dict[str, str]:
    allowed = {str(row.get("shot_id", "")).strip(): str(row.get("wan_positive_prompt_text", "")).strip() for row in rows}
    out: dict[str, str] = {}
    for item in raw.get("items", []) if isinstance(raw, dict) else []:
        if not isinstance(item, dict):
            continue
        shot_id = str(item.get("shot_id", "")).strip()
        prompt_text = str(item.get("prompt_text", "")).strip()
        if not shot_id or shot_id not in allowed or not prompt_text:
            continue
        out[shot_id] = prompt_text
    return out
