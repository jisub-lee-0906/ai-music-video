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
                "start_beat_index": int(shot.get("start_beat_index", 0) or 0),
                "end_beat_index": int(shot.get("end_beat_index", 0) or 0),
                "start_sec": float(shot.get("start_sec", 0.0) or 0.0),
                "end_sec": float(shot.get("end_sec", 0.0) or 0.0),
                "anchor_sec": float(shot.get("anchor_sec", shot.get("start_sec", 0.0)) or shot.get("start_sec", 0.0)),
                "ref_prompt_text": "",
            }
        )
    _seed_ref_items(config, ref_items)
    _draft_ref_items(config, ref_items, brief)
    _polish_ref_items(config, ref_items, brief)

    wan_items: list[dict] = []
    for previous, current in zip(ref_items, ref_items[1:]):
        start_anchor_sec = float(previous.get("anchor_sec", 0.0) or 0.0)
        end_anchor_sec = float(current.get("anchor_sec", start_anchor_sec) or start_anchor_sec)
        wan_items.append(
            {
                "shot_id": str(current.get("shot_id", "")).strip(),
                "section_name": str(current.get("section_name", "")).strip(),
                "section_label": str(current.get("section_label", "")).strip(),
                "start_ref_shot_id": str(previous.get("shot_id", "")).strip(),
                "end_ref_shot_id": str(current.get("shot_id", "")).strip(),
                "duration_sec": _pair_duration(previous, current),
                "place": str(current.get("place", "")).strip() or str(previous.get("place", "")).strip(),
                "bridge_action": _bridge_action(previous, current),
                "carry": str(current.get("carry", "")).strip() or str(previous.get("carry", "")).strip(),
                "start_anchor_sec": start_anchor_sec,
                "end_anchor_sec": end_anchor_sec,
                "wan_positive_prompt_text": "",
            }
        )
    _seed_wan_items(config, wan_items)
    ref_by_id = {
        str(row.get("shot_id", "")).strip(): row
        for row in ref_items
        if str(row.get("shot_id", "")).strip()
    }
    _draft_wan_items(config, wan_items, ref_by_id, brief)
    _polish_wan_items(config, wan_items, ref_by_id, brief)

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
        "Turn each structured shot card into a REF prompt and each adjacent pair into a WAN bridge prompt. "
        "Use a draft pass and a polish pass. Do not let code rewrite wording."
    )


def build_render_plan_preview_prompt(config: dict, payload: dict) -> str:
    return build_prompt_plan_preview_prompt(config, payload)


def _seed_ref_items(config: dict, ref_items: list[dict]) -> None:
    prompts = verbalize_ref_prompts(config, ref_items)
    for row in ref_items:
        row["ref_prompt_text"] = str(prompts.get(row["shot_id"], "")).strip()


def _seed_wan_items(config: dict, wan_items: list[dict]) -> None:
    prompts = verbalize_wan_prompts(config, wan_items)
    for row in wan_items:
        row["wan_positive_prompt_text"] = str(prompts.get(row["shot_id"], "")).strip()


def _draft_ref_items(config: dict, ref_items: list[dict], brief: dict) -> None:
    render = config.get("render", {}) if isinstance(config, dict) else {}
    if not isinstance(render, dict) or not bool(render.get("ref_naturalize", False)):
        return
    for row in ref_items:
        rewritten = generate_structured(config, _ref_draft_prompt(row, brief), _prompt_schema(row), attempts=1)
        text = _normalize_ref_result(rewritten, row)
        if not text:
            raise RuntimeError(f"ref draft invalid: {row.get('shot_id', '')}")
        row["ref_prompt_text"] = text


def _polish_ref_items(config: dict, ref_items: list[dict], brief: dict) -> None:
    render = config.get("render", {}) if isinstance(config, dict) else {}
    if not isinstance(render, dict) or not bool(render.get("ref_polish", False)):
        return
    for row in ref_items:
        rewritten = generate_structured(config, _ref_polish_prompt(row, brief), _prompt_schema(row), attempts=1)
        text = _normalize_ref_result(rewritten, row)
        if not text:
            raise RuntimeError(f"ref polish invalid: {row.get('shot_id', '')}")
        row["ref_prompt_text"] = text


def _draft_wan_items(config: dict, wan_items: list[dict], ref_by_id: dict[str, dict], brief: dict) -> None:
    render = config.get("render", {}) if isinstance(config, dict) else {}
    if not isinstance(render, dict) or not bool(render.get("wan_naturalize", False)):
        return
    for row in wan_items:
        rewritten = generate_structured(config, _wan_draft_prompt(row, ref_by_id, brief), _prompt_schema(row), attempts=1)
        text = _normalize_wan_result(rewritten, row)
        if not text:
            raise RuntimeError(f"wan draft invalid: {row.get('shot_id', '')}")
        row["wan_positive_prompt_text"] = text


def _polish_wan_items(config: dict, wan_items: list[dict], ref_by_id: dict[str, dict], brief: dict) -> None:
    render = config.get("render", {}) if isinstance(config, dict) else {}
    if not isinstance(render, dict) or not bool(render.get("wan_polish", False)):
        return
    for row in wan_items:
        rewritten = generate_structured(config, _wan_polish_prompt(row, ref_by_id, brief), _prompt_schema(row), attempts=1)
        text = _normalize_wan_result(rewritten, row)
        if not text:
            raise RuntimeError(f"wan polish invalid: {row.get('shot_id', '')}")
        row["wan_positive_prompt_text"] = text


def _bridge_action(previous: dict, current: dict) -> str:
    current_action = str(current.get("action", "")).strip()
    if current_action:
        return current_action
    previous_action = str(previous.get("action", "")).strip()
    if previous_action:
        return previous_action
    return "moving forward with one readable change"


def _pair_duration(previous: dict, current: dict) -> float:
    start_anchor = float(previous.get("anchor_sec", 0.0) or 0.0)
    end_anchor = float(current.get("anchor_sec", start_anchor) or start_anchor)
    delta = max(0.25, end_anchor - start_anchor)
    return round(delta, 3)


def _ref_draft_prompt(row: dict, brief: dict) -> str:
    base = str(row.get("ref_prompt_text", "")).strip()
    face_lock = _face_lock_suffix(base)
    motifs = _brief_motifs(brief)
    return (
        "Write the final REF prompt from this structured shot card. "
        "The contract is generic: preserve the meaning and details exactly, and do not invent new places, props, actions, camera setups, or story beats. "
        "Interpret SubjectForm as guidance about singular/plural and broad identity only; choose the final wording yourself without changing the underlying identity. "
        "Write 2 to 4 fluent English sentences. "
        "Sentence 1 should establish the current visible action and place. "
        "Sentence 2 should deepen the physical image. "
        "Sentence 3, if needed, should preserve continuity without repeating sentence 2. "
        "Keep the prompt grounded and cinematic, but do not add decorative filler or emotional explanation. "
        "If motifs are provided, use them only if they fit the existing shot card; do not force them. "
        "End with the exact face-lock suffix already present in the base draft. "
        "Return strict JSON only. "
        f"Shot card: shot_id={row.get('shot_id', '')} | section={row.get('section_label', '')} | "
        f"start_sec={float(row.get('start_sec', 0.0)):.3f} | end_sec={float(row.get('end_sec', 0.0)):.3f} | "
        f"focus={row.get('segment_focus', '')} | place={row.get('place', '')} | action={row.get('action', '')} | "
        f"detail={row.get('literal_image', '')} | carry={row.get('carry', '')} | framing={row.get('framing', '')} | "
        f"lyric_lines={'; '.join(str(x) for x in row.get('lyric_lines', []))} | motifs={motifs} | "
        f"base_draft={base} | face_lock={face_lock}"
    )


def _ref_polish_prompt(row: dict, brief: dict) -> str:
    base = str(row.get("ref_prompt_text", "")).strip()
    face_lock = _face_lock_suffix(base)
    motifs = _brief_motifs(brief)
    return (
        "Polish this REF prompt lightly. "
        "Do not change the scene meaning, subject identity, place, action, timing, continuity, or face-lock. "
        "Do not invent anything new. "
        "Remove awkward phrasing, reduce repetition, and improve fluency only. "
        "Keep the same subject identity and the exact face-lock suffix. "
        "Return strict JSON only. "
        f"Shot card: shot_id={row.get('shot_id', '')} | focus={row.get('segment_focus', '')} | motifs={motifs} | "
        f"current_prompt={base} | face_lock={face_lock}"
    )


def _wan_draft_prompt(row: dict, ref_by_id: dict[str, dict], brief: dict) -> str:
    start_ref = str(row.get("start_ref_shot_id", "")).strip()
    end_ref = str(row.get("end_ref_shot_id", "")).strip()
    start_ref_text = str(ref_by_id.get(start_ref, {}).get("ref_prompt_text", "")).strip()
    end_ref_text = str(ref_by_id.get(end_ref, {}).get("ref_prompt_text", "")).strip()
    motifs = _brief_motifs(brief)
    base = str(row.get("wan_positive_prompt_text", "")).strip()
    return (
        "Write the final WAN bridge prompt from this structured transition card. "
        "The contract is generic: preserve the transition meaning exactly, and do not invent new places, props, actions, or story beats. "
        "Write one or two short fluent English sentences only. "
        "Use one clear motion and one continuity detail. "
        "Do not restate the full REF prompts, do not add decorative scene-setting, and do not include any face-lock line. "
        "If motifs are provided, use them only when they naturally fit the same transition. "
        "Return strict JSON only. "
        f"Transition card: shot_id={row.get('shot_id', '')} | section={row.get('section_label', '')} | "
        f"pair={start_ref}->{end_ref} | start_anchor_sec={float(row.get('start_anchor_sec', 0.0)):.3f} | "
        f"end_anchor_sec={float(row.get('end_anchor_sec', 0.0)):.3f} | duration_sec={float(row.get('duration_sec', 0.0)):.3f} | "
        f"place={row.get('place', '')} | motion={row.get('bridge_action', '')} | carry={row.get('carry', '')} | motifs={motifs} | "
        f"start_ref={start_ref_text} | end_ref={end_ref_text} | base_draft={base}"
    )


def _wan_polish_prompt(row: dict, ref_by_id: dict[str, dict], brief: dict) -> str:
    start_ref = str(row.get("start_ref_shot_id", "")).strip()
    end_ref = str(row.get("end_ref_shot_id", "")).strip()
    motifs = _brief_motifs(brief)
    base = str(row.get("wan_positive_prompt_text", "")).strip()
    return (
        "Polish this WAN bridge prompt lightly. "
        "Do not change the transition meaning, identity, continuity, or timing. "
        "Do not invent anything new and do not add a face-lock suffix. "
        "Keep it short and fluent. "
        "Return strict JSON only. "
        f"Transition card: shot_id={row.get('shot_id', '')} | pair={start_ref}->{end_ref} | motifs={motifs} | current_prompt={base}"
    )


def _prompt_schema(row: dict) -> dict:
    shot_id = str(row.get("shot_id", "")).strip()
    return {
        "type": "object",
        "required": ["shot_id", "prompt_text"],
        "properties": {
            "shot_id": {"type": "string", "enum": [shot_id]},
            "prompt_text": {"type": "string"},
        },
    }


def _normalize_ref_result(raw: dict, row: dict) -> str:
    if not isinstance(raw, dict):
        return ""
    shot_id = str(raw.get("shot_id", "")).strip()
    expected = str(row.get("shot_id", "")).strip()
    prompt_text = " ".join(str(raw.get("prompt_text", "")).strip().split())
    if not shot_id or shot_id != expected or not prompt_text:
        return ""
    face_lock = _face_lock_suffix(str(row.get("ref_prompt_text", "")).strip())
    if face_lock and not prompt_text.endswith(face_lock):
        return ""
    return prompt_text


def _normalize_wan_result(raw: dict, row: dict) -> str:
    if not isinstance(raw, dict):
        return ""
    shot_id = str(raw.get("shot_id", "")).strip()
    expected = str(row.get("shot_id", "")).strip()
    prompt_text = " ".join(str(raw.get("prompt_text", "")).strip().split())
    if not shot_id or shot_id != expected or not prompt_text:
        return ""
    if "Keep the face." in prompt_text or "Keep the faces consistent." in prompt_text:
        return ""
    return prompt_text


def _brief_motifs(brief: dict) -> str:
    rows = [str(x).strip() for x in brief.get("profile_motifs", []) if str(x).strip()]
    return ", ".join(rows[:4]) if rows else "none"


def _face_lock_suffix(prompt_text: str) -> str:
    text = str(prompt_text).strip()
    if text.endswith("Keep the face."):
        return "Keep the face."
    if text.endswith("Keep the faces consistent."):
        return "Keep the faces consistent."
    return ""
