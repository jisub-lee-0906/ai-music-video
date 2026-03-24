from __future__ import annotations

from ai_mv.core.contracts.prompt_normalize import normalize_flux2_ref_items
from ai_mv.core.contracts.prompt_schema import flux2_ref_schema
from ai_mv.engines.visual_story_bible.brief_views import compact_section_atoms
from ai_mv.infra.codex_cli_client import generate_structured


def build_flux2_ref_plan(config: dict, payload: dict) -> dict:
    routes = [dict(row) for row in payload.get("clip_routes", []) if isinstance(row, dict) and bool(row.get("use_ref", False))]
    if not routes:
        return {"items": []}
    spec = _generate_ref_spec(config, payload, routes)
    keyed = normalize_flux2_ref_items(spec.get("items", []), routes)
    items = [_build_item(route, keyed[str(route["shot_id"])], idx) for idx, route in enumerate(routes, start=1)]
    return {"items": items}


def _flux2_ref_planner_batch_size(config: dict) -> int:
    render = config.get("render", {}) if isinstance(config, dict) else {}
    raw = render.get("flux2_ref_planner_batch_size", 4) if isinstance(render, dict) else 4
    try:
        return max(1, min(20, int(raw)))
    except Exception:
        return 4


def _planner_prompt(config: dict, payload: dict, anchors: list[dict], carry: str) -> str:
    summary = _anchor_summary(payload.get("visual_story_bible", {}), anchors)
    clip_count = len(anchors)
    return (
        "Write Flux2 ref prompts for continuity shots. "
        "Return strict JSON only with shape {\"items\":[...]}. No prose outside JSON. "
        f"Return exactly {clip_count} items, one for each shot_id in the manifest order. "
        "Each item must contain shot_id,prompt_text,subject_clause,action_clause,camera_clause,continuity_clause. "
        "Use this exact formula for prompt_text: [Base Identity] + [Changed Action/Pose] + [Camera/Framing] + [Minimal Style]. "
        "Write prompt_text as natural English sentences only, not as a list and not with plus signs. "
        "prompt_text must be exactly three sentences in this order: "
        "'The same anime girl, now ... .' then the camera sentence then the minimal style sentence. "
        "Do not restate background, palette, location, or long style paragraphs. "
        "The subject_clause must be exactly 'The same anime girl'. "
        "The action_clause must begin with 'now' and must describe only the changed pose or changed action. "
        "The camera_clause must be a single clean camera or framing sentence fragment, for example 'Extreme low-angle dynamic shot' or 'Tight close-up'. "
        "Do not use composition jargon such as crop, tableau, layout, composition, silhouette composition, or frame-within-frame wording in camera_clause. "
        "The continuity_clause must preserve the TTI graphic character style using a short minimal style sentence. "
        "The continuity_clause should describe a flat graphic anime character look with thick clean outlines, simplified deadpan features, and clear color blocking. "
        "Write every ref prompt as a high-quality human-written image prompt, not a placeholder transition note. "
        "Assume the source image already contains the correct character identity, costume, and world. "
        "Your job is to describe one strong changed pose or changed action with a clean camera phrase so the model can preserve the character while making a visible new frame. "
        "Treat the TTI master anchor as a locked character sheet: keep the same face shape, hair shape, hair color, outfit silhouette, body proportions, and core attitude. "
        "Do not redesign the character, do not drift into realism or live-action language, and keep the same simplified graphic heroine look established in TTI. "
        "Preserve the same deadpan symbolic face, flat graphic eyes, clean hair silhouette, and compact readable body proportions from the master anchor. "
        "Avoid timid wording such as slightly, gently, somewhat, quietly, remains there, or barely moves unless the beat truly demands a micro-change. "
        "If the beat is quiet, write a precise visible change anyway, such as eyes cutting left, fingers pressing the glass, shoulders dropping after impact, or one foot planting at the curb. "
        "Use vivid but concise action wording such as 'now stepping through the gate with one shoulder forward', 'now turning sharply into profile', or 'now lifting the umbrella and glancing toward the train window'. "
        "Avoid weak continuations such as standing there, staying in place, keeping the mood, or holding the frame unless the shot is intentionally still. "
        "Even still shots should include a concrete visual change, for example eye direction shift, hand movement, body turn, or weight shift. "
        "Avoid soft generic verbs such as drifting, looking, remaining, holding, or pausing by themselves. "
        "If you use a quiet beat, pair it with a visible physical change, such as 'looking back over one shoulder', 'pressing closer to the window', 'lifting the umbrella tip clear of the puddle', or 'fixing her gaze behind her'. "
        "Do not write weak action clauses like 'now drifting through the forecourt', 'now remaining still', or 'now looking ahead'. "
        "For quiet beats, prefer a concrete body-plus-environment interaction instead of an internal feeling description. "
        "Good quiet-beat actions: 'now pressing two fingers to the fogged glass', 'now planting one heel at the curb and turning back over one shoulder', 'now tightening the bag strap while stepping through the gate', or 'now dragging the umbrella tip once through the puddle rings'. "
        "Bad quiet-beat actions: 'now watching the lights', 'now feeling the night', 'now staying seated', or 'now holding the moment'. "
        "Make sure the changed action still touches the scene so the background stays drawable and present. "
        "Prefer actions tied to the environment, such as touching the train window, stepping through the gate, pausing under the platform sign, or crossing a wet curb line. "
        "Avoid prompts that isolate the girl in empty space or remove all environmental cues unless the beat explicitly calls for symbolic blankness. "
        "Make the action_clause feel like a direct follow-up to the TTI image, not a new scene description. "
        "Use concrete changed actions such as stepping past the gate, turning left, lifting her chin, smashing the guitar downward, or shifting into a profile. "
        "Avoid vague continuations such as holding the mood, keeping the energy, staying inside the frame, or carrying the atmosphere. "
        "The camera sentence should stay short and clean, for example 'Low reflective shot', 'Tight close-up', 'Extreme low-angle dynamic shot', or 'Wide side-tracking shot'. "
        "Another valid example: 'The same anime girl, now turning her eyes sharply to the left. Tight close-up. Flat graphic anime shading, thick clean outlines, simplified deadpan features.' "
        "Another strong example: 'The same anime girl, now stepping through the ticket gate with her coat hem swinging behind her. Off-center walking shot. Flat graphic anime shading, thick clean outlines, simplified deadpan features.' "
        "Another strong example: 'The same anime girl, now pressing one hand to the train window as city bands streak behind the glass. Layered train-window shot. Flat graphic anime shading, thick clean outlines, simplified deadpan features.' "
        "Another strong example: 'The same anime girl, now stopping at the curb as puddle rings widen around her shoes. Low reflective street shot. Flat graphic anime shading, thick clean outlines, simplified deadpan features.' "
        "Another strong example: 'The same anime girl, now pulling her shoulder back as a blue sign stripe crosses her jacket. Off-center platform shot. Flat graphic anime shading, thick clean outlines, simplified deadpan features.' "
        "Another strong example: 'The same anime girl, now looking back over one shoulder as her hair swings across her cheek. Off-center medium shot. Flat graphic anime shading, thick clean outlines, simplified deadpan features.' "
        "Another strong example: 'The same anime girl, now dragging the umbrella tip through the puddle and breaking the surface rings. Tight puddle insert shot. Flat graphic anime shading, thick clean outlines, simplified deadpan features.' "
        "Another strong example: 'The same anime girl, now pressing two fingers to the train glass as station lights split across her reflection. Tight reflective shot. Flat graphic anime shading, thick clean outlines, simplified deadpan features.' "
        "Bad example: 'The same anime girl, now posing beautifully. Nice shot. Flat graphic anime shading, thick clean outlines, simplified deadpan features.' "
        "Bad example: 'The same anime girl, now standing in empty space. Medium shot. Flat graphic anime shading, thick clean outlines, simplified deadpan features.' "
        "Bad example: 'The same anime girl, now leaning slightly toward the mood. Off-center shot. Flat graphic anime shading, thick clean outlines, simplified deadpan features.' "
        "Bad example: 'The same anime girl, now drifting through the forecourt. Wide shot. Flat graphic anime shading, thick clean outlines, simplified deadpan features.' "
        "Bad example: 'The same anime girl, now looking ahead. Medium shot. Flat graphic anime shading, thick clean outlines, simplified deadpan features.' "
        "Bad example: 'The same anime girl, now watching the streetlights slide across the carriage glass. Wide shot. Flat graphic anime shading, thick clean outlines, simplified deadpan features.' "
        "Use the TTI anchor as the source of truth and preserve the same character and same world. "
        "Do not add safety suffixes, negative tags, or typography bans. "
        "Do not use '+' anywhere in any field. "
        "Example prompt_text: 'The same anime girl, now fiercely smashing the guitar onto the ground, bending her knees. Extreme low-angle dynamic shot. Flat graphic anime shading, thick clean outlines, simplified deadpan features.' "
        f"Shot manifest={summary}."
    )


def _generate_ref_spec(config: dict, payload: dict, anchors: list[dict], attempts: int = 3) -> dict:
    prompt = _planner_prompt(config, payload, anchors, "")
    expected_ids = [str(anchor["shot_id"]) for anchor in anchors]
    current_prompt = prompt
    last_exc: Exception | None = None
    for attempt in range(1, max(1, int(attempts)) + 1):
        spec = generate_structured(config, current_prompt, flux2_ref_schema(), attempts=1)
        try:
            keyed = normalize_flux2_ref_items(spec.get("items", []), anchors)
            for shot_id in expected_ids:
                row = keyed[shot_id]
                if "+" in str(row["prompt_text"]) or "+" in str(row["action_clause"]) or "+" in str(row["camera_clause"]):
                    raise RuntimeError(f"plus-sign formatting mismatch: {shot_id}")
                if str(row["prompt_text"]).strip() != _compose_prompt_text(
                    row["subject_clause"],
                    row["action_clause"],
                    row["camera_clause"],
                    row["continuity_clause"],
                ):
                    raise RuntimeError(f"prompt_text formula mismatch: {shot_id}")
            return spec
        except RuntimeError as exc:
            last_exc = exc
            if attempt >= attempts:
                raise
            actual_ids = [
                str(row.get("shot_id", "")).strip()
                for row in spec.get("items", [])
                if isinstance(row, dict) and str(row.get("shot_id", "")).strip()
            ]
            current_prompt = (
                f"{prompt}\n\n"
                "Previous output failed validation. "
                f"Failure={exc}. "
                f"Expected shot_id order={', '.join(expected_ids)}. "
                f"Previous shot_id order={', '.join(actual_ids)}. "
                "Rewrite the JSON only and follow the exact prompt_text formula."
            )
    if last_exc is not None:
        raise last_exc
    raise RuntimeError("flux2_ref planner failed without validation error")


def _build_item(anchor: dict, row: dict, timeline_index: int) -> dict:
    ref = str(anchor.get("identity_anchor", anchor["anchor"]))
    return {
        "shot_id": anchor["shot_id"],
        "chain_key": _chain_key(anchor),
        "timeline_index": int(timeline_index),
        "anchor": anchor["anchor"],
        "ref": ref,
        "style_ref": "",
        "prompt_text": str(row["prompt_text"]),
        "style_clause": "",
        "subject_clause": str(row["subject_clause"]),
        "action_clause": str(row["action_clause"]),
        "camera_clause": str(row["camera_clause"]),
        "environment_clause": "",
        "continuity_clause": str(row["continuity_clause"]),
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
        "kinetic_transition": str(anchor.get("kinetic_transition", "")),
        "lighting_fx": str(anchor.get("lighting_fx", "")),
        "kinetic_intensity": str(anchor.get("kinetic_intensity", "")),
        "route_reason": str(anchor.get("route_reason", "")),
        "scene_change_level": str(anchor.get("scene_change_level", "evolve")),
        "anchor_strategy": str(anchor.get("anchor_strategy", "refine_anchor")),
        "continuity_basis": str(anchor.get("continuity_basis", "world")),
    }


def _compose_prompt_text(subject_clause: str, action_clause: str, camera_clause: str, continuity_clause: str) -> str:
    subject = " ".join(str(subject_clause).strip().split())
    action = " ".join(str(action_clause).strip().split())
    if action and not action.lower().startswith(("now ", "while ", "as ")):
        action = f"now {action}"
    if subject and action:
        lead = f"{subject}, {action}"
    else:
        lead = subject or action
    parts = [lead, camera_clause.strip(), continuity_clause.strip()]
    return " ".join(_sentence(part) for part in parts if part).strip()


def _anchor_summary(brief: dict, anchors: list[dict]) -> str:
    return ", ".join(_anchor_summary_row(brief, a) for a in anchors)


def _anchor_summary_row(brief: dict, anchor: dict) -> str:
    sid = str(anchor["shot_id"])
    shot_type = str(anchor.get("shot_type", "CHAR_MASTER"))
    focus = str(anchor.get("prompt_focus", "")).strip().lower() or "heroine"
    phase = _clip_phase(anchor)
    section = _beat_atoms(brief, anchor)
    pose = str(anchor.get("pose_delta", "")).strip() or "pose shift"
    camera = str(anchor.get("camera_language", "")).strip() or "framing shift"
    visible_action = str(section.get("visible_action", "")).strip()
    return f"{sid}({shot_type}|{focus}|{phase}|{pose}|{camera}|{visible_action})"


def _chain_key(anchor: dict) -> str:
    return f"{str(anchor.get('shot_id', '')).strip()}:{int(anchor.get('clip_index', 1))}"


def _sentence(text: str) -> str:
    cleaned = " ".join(str(text).strip().rstrip(". ").split())
    return f"{cleaned}." if cleaned else ""


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


def _beat_atoms(brief: dict, anchor: dict) -> dict:
    beat_id = str(anchor.get("lyric_beat_id", "")).strip()
    if beat_id:
        for beat in brief.get("lyric_beats", []):
            if not isinstance(beat, dict):
                continue
            if str(beat.get("beat_id", "")).strip() == beat_id:
                return dict(beat)
    return compact_section_atoms(brief, str(anchor.get("section_name", "")), beat_id)
