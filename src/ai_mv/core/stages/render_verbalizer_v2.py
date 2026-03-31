from __future__ import annotations

from ai_mv.infra.codex_cli_client import generate_structured, ping_codex


def verbalize_ref_prompt_pairs(config: dict, rows: list[dict]) -> dict[str, dict]:
    if not rows:
        return {}
    try:
        if ping_codex(config):
            return _verbalize_ref_prompt_pairs_with_codex(config, rows)
    except Exception:
        pass
    out: dict[str, dict] = {}
    for row in rows:
        shot_id = str(row.get("shot_id", "")).strip()
        if not shot_id:
            continue
        out[shot_id] = {
            "start_prompt_text": _join_prompt_parts(
                row.get("location", ""),
                row.get("subject_intro", ""),
                row.get("start_state", ""),
                row.get("lighting", ""),
            ),
            "end_prompt_text": _join_prompt_parts(
                row.get("location", ""),
                row.get("subject_intro", ""),
                row.get("end_state", ""),
                row.get("lighting", ""),
            ),
        }
    return out


def verbalize_wan_prompts(config: dict, rows: list[dict]) -> dict[str, str]:
    if not rows:
        return {}
    try:
        if ping_codex(config):
            return _verbalize_wan_prompts_with_codex(config, rows)
    except Exception:
        pass
    out: dict[str, str] = {}
    for row in rows:
        shot_id = str(row.get("shot_id", "")).strip()
        if not shot_id:
            continue
        out[shot_id] = _join_prompt_parts(
            row.get("location", ""),
            row.get("subject_intro", ""),
            row.get("bridge_action", ""),
            row.get("lighting", ""),
        )
    return out


def _verbalize_ref_prompt_pairs_with_codex(config: dict, rows: list[dict]) -> dict[str, dict]:
    schema = {
        "type": "object",
        "properties": {
            "shots": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "shot_id": {"type": "string"},
                        "start_prompt_text": {"type": "string"},
                        "end_prompt_text": {"type": "string"},
                    },
                    "required": ["shot_id", "start_prompt_text", "end_prompt_text"],
                },
            }
        },
        "required": ["shots"],
    }
    prompt = (
        "You are a render verbalizer for a music-video pipeline. "
        "Your job is only to merge already-decided prompt clauses into natural English prose for Flux image generation. "
        "Preserve meaning exactly. Do not add any new person, place, prop, action, relationship, emotion, symbolism, or story information. "
        "Do not remove any provided meaning. Do not invent another person unless the clauses already include one. "
        "Do not introduce camera, frame, shot, cut, continuity, transition, prompt, or viewer language. "
        "Keep the single-heroine default when the clauses are single-subject. "
        "Each output should read as natural visual prose, not as metadata. "
        "Prefer direct subject-first image prose when possible. "
        "Keep the prose compact so the heroine and her action stay more prominent than the environment. "
        "Do not inflate the setting into a grand set-piece if the clauses only describe a simple place anchor. "
        "Prefer one body-led action and at most one contact detail over layered atmosphere wording. "
        "If the clauses already imply a useful identity hook such as the same heroine with a high ponytail, preserve it instead of flattening it away. "
        "If the clauses describe crossing a doorway, gate, or opening, keep that as a body-led crossing action instead of turning the opening into the main subject of the sentence. "
        "For difficult opening or bridge shots, keep a small identity hook when present rather than rewriting it away into generic heroine wording. "
        "Write complete natural sentence prose, not comma-spliced fragments or keyword lists. "
        "Avoid helper phrasing such as 'is in', 'is at', or 'is standing in' when a cleaner natural sentence can be formed. "
        "Avoid weakening the action into gaze-only, breath-only, or mood-only wording if the clauses already contain a clearer physical action. "
        "Do not foreground pause, hesitation, breath, heartbeat, or memory wording if the clauses already support a more readable physical action in the same place. "
        "For each shot, produce start_prompt_text and end_prompt_text by naturally merging: location, subject_intro, state/action, and lighting. "
        "Keep start and end as adjacent states in the same place. "
        "Return JSON only.\n\n"
        f"Shots={rows}"
    )
    raw = generate_structured(config, prompt, schema, attempts=1)
    out: dict[str, dict] = {}
    for row in raw.get("shots", []):
        if not isinstance(row, dict):
            continue
        shot_id = str(row.get("shot_id", "")).strip()
        start = " ".join(str(row.get("start_prompt_text", "")).strip().split())
        end = " ".join(str(row.get("end_prompt_text", "")).strip().split())
        if shot_id and start and end:
            out[shot_id] = {"start_prompt_text": start, "end_prompt_text": end}
    return out


def _verbalize_wan_prompts_with_codex(config: dict, rows: list[dict]) -> dict[str, str]:
    schema = {
        "type": "object",
        "properties": {
            "shots": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "shot_id": {"type": "string"},
                        "positive_prompt_text": {"type": "string"},
                    },
                    "required": ["shot_id", "positive_prompt_text"],
                },
            }
        },
        "required": ["shots"],
    }
    prompt = (
        "You are a render verbalizer for a Wan first-last-frame bridge pipeline. "
        "Your job is only to merge already-decided clauses into one natural English positive prompt. "
        "Preserve meaning exactly. Do not add any new person, place, prop, action, relationship, emotion, symbolism, or story information. "
        "Do not invent another person unless the clauses already include one. "
        "Do not introduce camera, frame, shot, cut, continuity, transition, prompt, or viewer language. "
        "Prefer direct subject-first image prose when possible. "
        "Keep the prose compact so the heroine and the bridge action stay more prominent than the environment. "
        "Do not inflate the place into a grand set-piece if the clauses only describe a simple place anchor. "
        "Prefer one body-led transition and at most one contact detail over layered atmosphere wording. "
        "Write one complete natural sentence for each prompt, not a comma-spliced fragment list. "
        "Avoid helper phrasing such as 'is in' or 'is at' when a cleaner natural sentence can be formed. "
        "Avoid weakening the bridge into gaze-only, breath-only, or mood-only wording if the clauses already contain a clearer physical transition. "
        "Do not foreground pause, hesitation, breath, heartbeat, or memory wording if the clauses already support a more readable physical transition in the same place. "
        "Do not verbalize the bridge with static main verbs such as stands, holds, waits, or remains if the clauses already support even a small physical progression. "
        "The result must read like one visible transition between start and end frames in the same scene. "
        "Return JSON only.\n\n"
        f"Shots={rows}"
    )
    raw = generate_structured(config, prompt, schema, attempts=1)
    out: dict[str, str] = {}
    for row in raw.get("shots", []):
        if not isinstance(row, dict):
            continue
        shot_id = str(row.get("shot_id", "")).strip()
        text = " ".join(str(row.get("positive_prompt_text", "")).strip().split())
        if shot_id and text:
            out[shot_id] = text
    return out


def _join_prompt_parts(location: object, subject: object, action: object, lighting: object) -> str:
    return " ".join(_sentence(part) for part in (subject, location, action, lighting) if _sentence(part))


def _sentence(text: object) -> str:
    cleaned = " ".join(str(text).strip().rstrip(". ").split())
    return f"{cleaned}." if cleaned else ""
