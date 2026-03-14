from __future__ import annotations

from ai_mv.core.contracts.prompt_normalize import normalize_flux2_ref_items
from ai_mv.core.contracts.prompt_schema import flux2_ref_schema
from ai_mv.core.prompt_digests import style_digest, visual_digest
from ai_mv.core.visual_pipeline import section_semantics_digest
from ai_mv.engines.visual_bridge.brief_views import compact_section_atoms, compact_world_atoms
from ai_mv.infra.codex_cli_client import generate_structured


def build_flux2_ref_plan(config: dict, payload: dict) -> dict:
    routes = [dict(row) for row in payload.get("clip_routes", []) if isinstance(row, dict) and bool(row.get("use_ref", False))]
    if not routes:
        return {"items": []}
    spec = _plan_with_llm(config, payload, routes)
    rules = normalize_flux2_ref_items(spec["items"], routes)
    items = [_build_item(a, rules[a["shot_id"]]) for a in routes]
    return {"items": items}


def _plan_with_llm(config: dict, payload: dict, anchors: list[dict]) -> dict:
    batch_size = min(len(anchors), _flux2_ref_planner_batch_size(config))
    items = _plan_with_batches(config, payload, anchors, batch_size)
    return {"items": items}


def _plan_with_batches(config: dict, payload: dict, anchors: list[dict], batch_size: int) -> list[dict]:
    if batch_size <= 0:
        raise RuntimeError("flux2 reference planner batch_size must be positive")
    out: list[dict] = []
    carry = ""
    for i in range(0, len(anchors), batch_size):
        chunk = anchors[i : i + batch_size]
        rows = _plan_chunk_rows(config, payload, chunk, carry)
        out.extend(rows)
        carry = _batch_tail(rows)
    return out


def _plan_chunk_rows(config: dict, payload: dict, chunk: list[dict], carry: str) -> list[dict]:
    prompt = _planner_prompt(config, payload, chunk, carry)
    raw = generate_structured(config, prompt, flux2_ref_schema())
    return _coerce_item_ids(raw.get("items", []), chunk)


def _planner_prompt(config: dict, payload: dict, anchors: list[dict], carry: str) -> str:
    guidance = style_digest(payload.get("audio_map", {}), 1) or _style_guidance(config, payload)
    visual = visual_digest(payload.get("audio_map", {}), 1)
    brief = _brief_summary(payload["visual_brief"], anchors)
    semantics = section_semantics_digest(payload.get("audio_map", {}))
    anchor_ids = _anchor_ids(anchors)
    summary = _anchor_summary(anchors)
    carry_clause = f"Carry forward={carry}. " if carry else ""
    return (
        "You are a senior Flux2 reference-image keyframe planner. "
        "Return strict JSON only: {\"items\":[...]}. No prose outside JSON. "
        "Each item must include shot_id,subject_clause,action_clause,environment_clause,continuity_clause. "
        "Use shot_id values exactly from Anchors list, without creating new ids. "
        "All anchors refer to the same master identity image. Preserve the same face, hair, outfit, proportions, and accessories across every item. "
        "Item count must match the number of Anchors exactly. "
        "subject_clause must be a short identity clause naming the same lead subject, readable pose or silhouette, and one stable styling cue. "
        "action_clause must describe one small visible change axis only: gaze, pose, hand, orientation, or travel. "
        "environment_clause must ground the same place, light, or reflection relation in short visual language. "
        "continuity_clause must preserve the same side relation or travel direction in short plain English and it must be specific enough to survive image generation. "
        "Do not write full final prompt sentences. Return only short reusable clauses. "
        "Do not invent a new handheld prop, umbrella, shopping bag, phone, or instrument unless the shot blueprint or hero identity lock explicitly requires it. "
        "Good action_clause examples: lifts her gaze toward the crossing; turns one shoulder away from the glass; slows into a shorter step; eases her chin toward the reflection. "
        "Bad action_clause examples: stronger chorus energy; more emotional release; deeper confidence; cinematic payoff. "
        "Good environment_clause examples: under wet storefront glow; beside rain-marked station glass; with the crosswalk light opening ahead; against teal reflections on the pavement. "
        "Bad environment_clause examples: nostalgic city atmosphere; elegant nighttime emotion; polished visual mood. "
        "Good continuity_clause examples: keeping the glass on camera-right; holding the same left-to-right walk line; with the reflection still running beside her; keeping the curb low in frame. "
        "Bad continuity_clause examples: same mood as before; continuity remains strong; visual grammar holds. "
        "When continuity_clause says camera-right, camera-left, left-to-right, or right-to-left, keep that geometry explicit instead of dissolving into generic portrait wording. "
        "Do not mention the hero prop in every item; mention it only when it materially supports the shot. "
        "When a shot series is split into multiple clip parts, earlier parts should establish the body and space relation, middle parts should advance the action, and the last part should resolve or exit the beat. "
        "Do not give identical action_clause to multiple consecutive parts of the same shot series. "
        "Do not change time period, world setting, or character species. "
        "Honor the section story_beat and location_anchor from the visual brief. "
        "Honor the shot space_relation exactly; keep the same left-right geometry unless the shot blueprint explicitly crosses the frame. "
        "Let the story_beat determine the keyframe change before beauty polish does. "
        "Use concrete visual language: pose shift, gaze shift, hand motion, cloth motion, light direction, and reflection relation. "
        "Respect the shot blueprint for pose delta, scene detail, motion hint, and camera feel, but absorb those cues into short clauses instead of prose. "
        "Prefer readable body line and travel direction over another polished front portrait. "
        "Readable action and readable space come before beauty polish, especially for storefront glass, reflection-side, and crosswalk direction cues. "
        "Final Chorus should feel like the visual peak without becoming a different world. "
        "Bridge items should feel interrupted or isolated rather than glamorous. "
        "Outro items should leave one residue image instead of another forward-moving portrait. "
        "Avoid generic phrase pairs like beautiful lighting, emotional atmosphere, cinematic mood, stylish portrait, or dreamy vibes unless tied to a specific visual fact. "
        f"{carry_clause}Style guidance={guidance}; Visual direction={visual}; Section semantics={semantics}; Visual brief={brief}; "
        f"Anchor ids={anchor_ids}; Anchors={summary}."
    )

def _flux2_ref_planner_batch_size(config: dict) -> int:
    render = config.get("render", {}) if isinstance(config, dict) else {}
    if not isinstance(render, dict):
        return 4
    raw = render.get("flux2_ref_planner_batch_size", 4)
    try:
        n = int(raw)
    except Exception:
        return 4
    return max(1, min(20, n))


def _style_guidance(config: dict, payload: dict) -> str:
    audio_map = payload.get("audio_map", {}) if isinstance(payload, dict) else {}
    guided = str(audio_map.get("style_guidance", "")).strip() if isinstance(audio_map, dict) else ""
    if guided:
        return guided
    style = config.get("style", {}) if isinstance(config, dict) else {}
    return str(style.get("guidance", "")).strip() if isinstance(style, dict) else ""


def _brief_summary(brief: dict, anchors: list[dict]) -> str:
    world = compact_world_atoms(brief)
    return (
        f"hero={world['hero_identity']}; world={world['world_rules']}; "
        f"sections={_section_briefs(brief, anchors)}"
    )


def _section_briefs(brief: dict, anchors: list[dict]) -> str:
    rows = []
    ordered_names: list[str] = []
    seen: set[str] = set()
    for anchor in anchors:
        name = str(anchor.get("section_name", "")).strip()
        if name and name not in seen:
            seen.add(name)
            ordered_names.append(name)
    names = ordered_names or [str(row.get("section_name", "")).strip() for row in brief.get("section_briefs", [])]
    for name in names:
        row = compact_section_atoms(brief, name)
        rows.append(
            f"{row['section_name']}|{row['story_beat']}|{row['location_anchor']}"
        )
    return ", ".join(rows)


def _batch_tail(rows: list[dict]) -> str:
    if not rows:
        return ""
    last = rows[-1]
    parts = [
        str(last.get("subject_clause", "")).strip(),
        str(last.get("action_clause", "")).strip(),
        str(last.get("continuity_clause", "")).strip(),
    ]
    return " | ".join(part for part in parts if part)[:140]


def _coerce_item_ids(items: list[dict], anchors: list[dict]) -> list[dict]:
    pool = [_normalize_item_id(x) for x in items if isinstance(x, dict)]
    keyed: dict[str, dict] = {}
    for row in pool:
        sid = str(row.get("shot_id", "")).strip()
        if not sid:
            raise RuntimeError("Flux2 reference planner missing shot_id")
        if sid in keyed:
            raise RuntimeError(f"Flux2 reference planner duplicate shot_id: {sid}")
        keyed[sid] = row
    expected = [str(anchor["shot_id"]) for anchor in anchors]
    actual = list(keyed.keys())
    expected_set = set(expected)
    missing = [sid for sid in expected if sid not in keyed]
    extra = [sid for sid in actual if sid not in expected_set]
    if missing:
        raise RuntimeError(f"Flux2 reference planner shot_id mismatch: missing {missing[0]}")
    if extra:
        raise RuntimeError(f"Flux2 reference planner shot_id mismatch: unknown {extra[0]}")
    if len(actual) != len(expected):
        raise RuntimeError(f"Flux2 reference planner item count mismatch: expected={len(expected)} actual={len(actual)}")
    out: list[dict] = []
    for a in anchors:
        sid = str(a["shot_id"])
        row = keyed.get(sid)
        if row is None:
            raise RuntimeError(f"Flux2 reference planner shot_id mismatch: missing {sid}")
        out.append(_with_shot_id(row, sid))
    return out


def _normalize_item_id(row: dict) -> dict:
    out = dict(row)
    sid = str(out.get("shot_id", "")).strip().strip(".;:")
    if sid:
        out["shot_id"] = sid
    return out


def _with_shot_id(row: dict, shot_id: str) -> dict:
    out = dict(row)
    out["shot_id"] = shot_id
    return out


def _anchor_summary(anchors: list[dict]) -> str:
    return ", ".join(_anchor_summary_row(a) for a in anchors)


def _anchor_summary_row(anchor: dict) -> str:
    sid = str(anchor["shot_id"])
    section = str(anchor.get("section_name", "section"))
    label = str(anchor.get("section_label", section))
    shot_type = str(anchor.get("shot_type", "CHAR_MASTER"))
    emotion = str(anchor.get("emotion", "")).strip() or "steady"
    pose = str(anchor.get("pose_delta", "")).strip() or "small pose shift"
    detail = str(anchor.get("scene_detail", "")).strip() or "hero focus"
    relation = str(anchor.get("space_relation", "")).strip() or "space stays stable"
    phase = _clip_phase(anchor)
    return f"{sid}({section}|{label}|{shot_type}|{emotion}|{pose}|{detail}|{relation}|{phase})"


def _anchor_ids(anchors: list[dict]) -> str:
    ids = [str(anchor["shot_id"]) for anchor in anchors]
    if not ids:
        raise RuntimeError("anchors missing for Flux2 reference prompt planner")
    return ", ".join(ids)


def _build_item(anchor: dict, rule: dict) -> dict:
    ref = str(anchor.get("identity_anchor", anchor["anchor"]))
    prompt_text = _compose_flux2_ref_prompt(anchor, rule)
    return {
        "shot_id": anchor["shot_id"],
        "anchor": anchor["anchor"],
        "ref": ref,
        "style_ref": "",
        "prompt_text": prompt_text,
        "subject_clause": str(rule["subject_clause"]),
        "action_clause": str(rule["action_clause"]),
        "environment_clause": str(rule["environment_clause"]),
        "continuity_clause": str(rule["continuity_clause"]),
        "duration_sec": float(anchor["duration_sec"]),
        "clip_index": int(anchor.get("clip_index", 1)),
        "clip_count": int(anchor.get("clip_count", 1)),
        "clip_phase": _clip_phase(anchor),
        "shot_type": str(anchor["shot_type"]),
        "section_name": str(anchor.get("section_name", "section")),
        "section_label": str(anchor.get("section_label", anchor.get("section_name", "section"))),
        "is_chorus": bool(anchor.get("is_chorus", False)),
        "camera_language": str(anchor.get("camera_language", "")),
        "pose_delta": str(anchor.get("pose_delta", "")),
        "emotion": str(anchor.get("emotion", "")),
        "scene_detail": str(anchor.get("scene_detail", "")),
        "motion_hint": str(anchor.get("motion_hint", "")),
        "space_relation": str(anchor.get("space_relation", "")),
        "route_reason": str(anchor.get("route_reason", "")),
    }


def _compose_flux2_ref_prompt(anchor: dict, rule: dict) -> str:
    parts = [
        _clause(rule.get("subject_clause", "")),
        _clause(rule.get("action_clause", "")),
        _clause(rule.get("continuity_clause", "")),
        _clause(rule.get("environment_clause", "")),
    ]
    text = ", ".join(part for part in parts if part)
    if not text:
        raise RuntimeError(f"empty composed Flux2 reference prompt: {anchor['shot_id']}")
    return _sentence(text)


def _clause(text: object) -> str:
    return " ".join(str(text).strip().rstrip(". ").split())


def _sentence(text: str) -> str:
    cleaned = str(text).strip().rstrip(". ")
    return f"{cleaned}."


def _clip_phase(anchor: dict) -> str:
    index = int(anchor.get("clip_index", 1))
    count = int(anchor.get("clip_count", 1))
    if count <= 1:
        return "single beat"
    if index <= 1:
        return "establish"
    if index >= count:
        return "resolve"
    return "advance"
