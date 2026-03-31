from __future__ import annotations

from ai_mv.core.contracts.seedance_v2_normalize import normalize_director_plan_v2
from ai_mv.core.director_brief import build_director_brief_intent
from ai_mv.core.stages.flux2_ref_chain_v2 import _literal_scene_description
from ai_mv.infra.codex_cli_client import generate_structured, ping_codex


def build_director_plan_v2(config: dict, payload: dict) -> dict:
    brief = build_director_brief_intent(config)
    scene_plan = payload["scene_plan_v2"]
    durations = _shot_duration_map(payload)
    shot_packages: list[dict] = []
    for index, shot in enumerate(scene_plan.get("shot_packages", []), start=1):
        shot_id = str(shot.get("shot_id", "")).strip()
        current = {
            **dict(shot),
            "duration_sec": float(durations.get(shot_id, 2.0)),
            "camera_intent": _camera_intent(shot, brief, index),
            "performance_intent": _performance_intent(shot),
            "lighting_intent": _lighting_intent(shot, brief),
            "shadow_intent": _shadow_intent(shot, brief),
            "contact_intent": _contact_intent(shot),
            "motion_intent": _motion_intent(shot, brief),
            "transition_intent": _transition_intent(shot, index),
        }
        current["ref_start_action_line"] = ""
        current["ref_end_action_line"] = ""
        current["wan_action_line"] = ""
        current["ref_lighting_line"] = _ref_lighting_line(current)
        shot_packages.append(current)
    _rewrite_prompt_action_lines(config, shot_packages)
    director_plan = {
        "brief_name": brief["brief_name"],
        "style_contract": brief["style_contract"],
        "camera_bias": brief["camera_bias"],
        "lighting_bias": brief["lighting_bias"],
        "shadow_bias": brief["shadow_bias"],
        "motion_bias": brief["motion_bias"],
        "transition_bias": brief["transition_bias"],
        "shot_packages": shot_packages,
    }
    return normalize_director_plan_v2(director_plan)


def build_director_plan_v2_preview_prompt(config: dict, payload: dict) -> str:
    brief = build_director_brief_intent(config)
    return (
        "Create a director-first shot plan with camera, performance, lighting, shadow, contact, motion, and transition intents. "
        f"Camera bias={brief['camera_bias']}. Lighting bias={brief['lighting_bias']}. "
        f"Shadow bias={brief['shadow_bias']}. Motion bias={brief['motion_bias']}. "
        "Keep the heroine identity fixed and move the world through connected zones."
    )


def _camera_intent(shot: dict, brief: dict, index: int) -> str:
    zone = str(shot.get("zone", "")).strip().lower()
    section = str(shot.get("section_label", "")).strip().lower()
    visual_role = str(shot.get("visual_role", "")).strip().lower()
    phase = _section_phase(shot)
    location = _literal_scene_description(shot)
    if visual_role == "opening_frame":
        return f"the place reads clearly first, with her arriving inside {location}"
    if visual_role == "pressure_frame":
        return "the space feels tighter around her without losing depth"
    if visual_role == "payoff_frame":
        return "the place opens one step wider while still feeling lived-in"
    if visual_role == "handoff_frame":
        return "the place leaves a clear direction for the next moment to follow"
    if "final chorus" in section:
        return "the place widens naturally while her movement keeps going through it"
    if "chorus" in section:
        if phase == "entry":
            return "the place opens a little wider and keeps her movement readable inside it"
        if phase == "exit":
            return "the space stays open in the direction her movement is already heading"
        return "the place stays readable while her movement carries through it"
    if "pre" in section:
        return "the place feels tighter and more anticipatory without turning static"
    if "bridge" in section:
        return "the place compresses into one tense pocket without losing depth"
    if zone in {"threshold", "edge"}:
        return "the crossing stays readable as a place she is entering or leaving"
    return "the place stays readable through its objects, surfaces, and depth"

def _performance_intent(shot: dict) -> str:
    zone = str(shot.get("zone", "")).strip().lower()
    visual_role = str(shot.get("visual_role", "")).strip().lower()
    phase = _section_phase(shot)
    if visual_role == "opening_frame":
        return "caught in an in-between moment, with weight settled more on one side before the movement fully begins"
    if visual_role == "handoff_frame":
        return "one readable body change finishes while the direction of motion still carries into the next cut"
    if visual_role == "pressure_frame":
        return "the body stays restrained, but one small off-center change in the head, shoulders, or hands reads clearly"
    if visual_role == "payoff_frame":
        return "the body opens one step wider than before, but the free side still arrives a beat later so the moment feels lived-in rather than posed"
    if zone == "threshold":
        return "one measured breath and a weight shift onto one leg, without fully crossing yet"
    if zone == "edge":
        return "slowing at the edge, with one shoulder line steadier than the other and one deliberate step beginning to form"
    if zone == "compression":
        return "the body nearly still, with movement narrowed to one shoulder, one hand, or one head turn inside one tense pocket"
    if zone == "open_world":
        if phase == "entry":
            return "stepping into the wider space, one shoulder turning ahead of the hips with a stronger forward intention"
        if phase == "exit":
            return "one side of the body already released into the next direction so the motion stays open into the next cut"
        return "moving through the wider space with controlled forward momentum, one-sided weight transfer, and a readable upper-body turn"
    if zone == "open_world_peak":
        return "a broader opening of the stride and torso while still staying grounded inside the same space and not settling into a finished pose"
    if zone == "residue":
        return "the movement falling away, breathing slowing, and the last after-image still hanging in place"
    if zone == "transit_lane":
        return "continuing through the lane with measured pace, asymmetrical weight, and restrained body language"
    return "moving through the close space with one readable, uneven body-led action"


def _lighting_intent(shot: dict, brief: dict) -> str:
    zone = str(shot.get("zone", "")).strip().lower()
    location = _literal_scene_description(shot).lower()
    if zone == "open_world_peak":
        return "Bright city light gathers across the wet ground and stays clear on her skin, clothes, and the nearby metal"
    if any(token in location for token in ("window", "glass", "storefront")):
        return "Window glow and soft reflected floor light stay clear on her, the glass, and the ground around her"
    if any(token in location for token in ("vending machine", "vending", "machine")):
        return "Vending-machine glow and wet pavement reflections stay clean on her and the ground beside her"
    if any(token in location for token in ("platform", "concourse", "sign", "track")):
        return "Platform light and sign glow stay clean on her and the surrounding floor and rail surfaces"
    if any(token in location for token in ("stair", "step", "landing", "rail")):
        return "City night light catches on the steps, railings, and the edges of her clothes without flattening the depth"
    if any(token in location for token in ("road", "street", "pavement", "curb", "crosswalk", "alley")):
        return "Streetlight and wet-ground reflections stay grounded on her skin, clothes, and the road surface"
    if zone in {"threshold", "edge"}:
        return "Gate light and reflected floor light stay sharp on her and the crossing surfaces around her"
    if zone == "compression":
        return "A tighter directional pool of light holds on her and the nearby station surfaces"
    if zone == "residue":
        return "The last pools of city light linger on the wet ground and fade slowly across her"
    if any(token in location for token in ("gate", "barrier", "card reader", "checkpoint", "station")):
        return "Station light and reflected floor light stay clear on her skin, clothes, and the metal around her"
    lighting_bias = " ".join(str(brief.get("lighting_bias", "")).strip().rstrip(".").split())
    if lighting_bias:
        return _naturalize_lighting_bias(lighting_bias)
    return "Natural city-night light stays grounded across her and the space around her"


def _shadow_intent(shot: dict, brief: dict) -> str:
    zone = str(shot.get("zone", "")).strip().lower()
    if zone == "compression":
        return "the shadows gather into a tighter directional pocket around her"
    return "the shadows stay readable and grounded without turning harsh or graphic"


def _motion_intent(shot: dict, brief: dict) -> str:
    section = str(shot.get("section_label", "")).strip().lower()
    visual_role = str(shot.get("visual_role", "")).strip().lower()
    phase = _section_phase(shot)
    if visual_role == "opening_frame":
        return "the motion is already lightly underway instead of starting from a posed stop"
    if visual_role == "handoff_frame":
        return "the motion carries through cleanly enough for the next moment to pick it up"
    if visual_role == "pressure_frame":
        return "the motion stays restrained and focused into small body shifts"
    if "chorus" in section:
        if phase == "exit":
            return "the motion resolves with stronger carry-through in her body and the surrounding space"
        return "the motion opens out with stronger body carry and a more reactive space around her"
    if "bridge" in section:
        return "the motion stays tighter and more pressurized, with less movement in the space around her"
    if "pre" in section:
        return "the motion builds through small forward pressure and restrained reactions in hair, fabric, and space"
    return "the motion stays stable, readable, and physically grounded inside the place"


def _contact_intent(shot: dict) -> str:
    role = str(shot.get("visual_role", "")).strip().lower()
    if role == "payoff_frame":
        return "keep the body physically grounded in the place so the space still feels shared around her as it opens"
    return "make the feet, body shadow, and nearby surfaces feel physically connected inside the same shot"


def _transition_intent(shot: dict, index: int) -> str:
    if index <= 1:
        return "establish the first connected zone without forcing a hard reset"
    if "open_world_peak" in str(shot.get("zone", "")):
        return "escalate through previous-end continuity into the largest payoff zone"
    return "advance through previous-end continuity and keep the cut feeling absorbed"


def _section_phase(shot: dict) -> str:
    index = int(shot.get("section_beat_index", 1) or 1)
    total = int(shot.get("section_beat_count", 1) or 1)
    if total <= 1:
        return "single"
    if index == 1:
        return "entry"
    if index >= total:
        return "exit"
    return "middle"


def _natural_start_action_line(shot: dict) -> str:
    subject_action = " ".join(str(shot.get("subject_action", "")).strip().split())
    if subject_action:
        return subject_action
    visible_action = " ".join(str(shot.get("visible_action", "")).strip().split())
    if visible_action:
        return visible_action
    return ""


def _natural_end_action_line(shot: dict) -> str:
    subject_action = " ".join(str(shot.get("subject_action", "")).strip().split())
    if subject_action:
        return subject_action
    visible_action = " ".join(str(shot.get("visible_action", "")).strip().split())
    if visible_action:
        return visible_action
    return ""


def _rewrite_prompt_action_lines(config: dict, shot_packages: list[dict]) -> None:
    if not shot_packages:
        return
    rows = []
    for shot in shot_packages:
        rows.append(
            {
                "shot_id": str(shot.get("shot_id", "")).strip(),
                "location": _literal_scene_description(shot),
                "literal_image": str(shot.get("literal_image", "")).strip(),
                "subject_action": str(shot.get("subject_action", "")).strip(),
                "visible_action": str(shot.get("visible_action", "")).strip(),
                "visual_role": str(shot.get("visual_role", "")).strip(),
                "duration_sec": float(shot.get("duration_sec", 2.0) or 2.0),
            }
        )
    try:
        if ping_codex(config):
            rewritten = _rewrite_with_codex(config, rows)
            if rewritten:
                for shot in shot_packages:
                    row = rewritten.get(str(shot.get("shot_id", "")).strip(), {})
                    start_line = " ".join(str(row.get("ref_start_action_line", "")).strip().split())
                    end_line = " ".join(str(row.get("ref_end_action_line", "")).strip().split())
                    wan_line = " ".join(str(row.get("wan_action_line", "")).strip().split())
                    shot["ref_start_action_line"] = start_line or _natural_start_action_line(shot)
                    shot["ref_end_action_line"] = end_line or _natural_end_action_line(shot)
                    shot["wan_action_line"] = wan_line or shot["ref_end_action_line"] or shot["ref_start_action_line"]
                return
    except Exception:
        pass
    for shot in shot_packages:
        shot["ref_start_action_line"] = _natural_start_action_line(shot)
        shot["ref_end_action_line"] = _natural_end_action_line(shot)
        shot["wan_action_line"] = shot["ref_end_action_line"] or shot["ref_start_action_line"]


def _rewrite_with_codex(config: dict, rows: list[dict]) -> dict[str, dict]:
    schema = {
        "type": "object",
        "properties": {
            "shots": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "shot_id": {"type": "string"},
                        "ref_start_action_line": {"type": "string"},
                        "ref_end_action_line": {"type": "string"},
                        "wan_action_line": {"type": "string"},
                    },
                    "required": ["shot_id", "ref_start_action_line", "ref_end_action_line", "wan_action_line"],
                },
            }
        },
        "required": ["shots"],
    }
    prompt = (
        "Rewrite each shot into natural English action lines for image/video prompts. "
        "Each line must be heroine-centered, start with 'She', and stay faithful to the provided action and place. "
        "Do not mention camera, frame, shot, cut, continuity, prompt, image, reset, carry, or video. "
        "Do not invent new props or locations. "
        "The action must stay physically compatible with the given location. "
        "ref_start_action_line should describe what she is doing in the first keyframe. "
        "ref_end_action_line should describe the same action one natural step later, scaled to the shot duration. "
        "wan_action_line should describe the motion between those keyframes as one natural sentence. "
        "Keep the language concrete and screen-readable.\n\n"
        f"Shots={rows}"
    )
    raw = generate_structured(config, prompt, schema, attempts=1)
    out: dict[str, dict] = {}
    for row in raw.get("shots", []):
        if not isinstance(row, dict):
            continue
        shot_id = str(row.get("shot_id", "")).strip()
        if shot_id:
            out[shot_id] = dict(row)
    return out


def _shot_duration_map(payload: dict) -> dict[str, float]:
    out: dict[str, float] = {}
    timeline = payload.get("lyrics_timeline", {})
    for section in timeline.get("sections", []):
        if not isinstance(section, dict):
            continue
        for beat in section.get("lyric_beats", []):
            if not isinstance(beat, dict):
                continue
            beat_id = str(beat.get("beat_id", "")).strip()
            if not beat_id:
                continue
            start = float(beat.get("start_sec", 0.0) or 0.0)
            end = float(beat.get("end_sec", 0.0) or 0.0)
            out[beat_id] = max(0.5, end - start) if end > start else 2.0
    return out
def _ref_lighting_line(shot: dict) -> str:
    lighting = " ".join(str(shot.get("lighting_intent", "")).strip().rstrip(".").split())
    if lighting:
        return lighting[:1].upper() + lighting[1:]
    return "Ground the light naturally across her and the space around her"


def _naturalize_lighting_bias(text: str) -> str:
    cleaned = " ".join(str(text).strip().rstrip(".").split())
    if not cleaned:
        return ""
    lower = cleaned.lower()
    if "sign glow" in lower or "platform" in lower or "station" in lower:
        return "Station sign glow and reflected floor light stay clean on her and the nearby surfaces"
    if "street" in lower or "wet" in lower or "reflection" in lower:
        return "Streetlight and reflected wet-ground light stay clear on her and the surrounding surfaces"
    return "City light stays clean and grounded on her and the nearby surfaces"
