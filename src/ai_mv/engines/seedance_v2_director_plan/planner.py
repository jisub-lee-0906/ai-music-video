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
        "Create a director-first shot plan that turns the brief into character-centered keyframe actions. "
        f"Style={brief['style_contract']}. World={brief['world_core']}. "
        "Keep the same heroine readable, single-subject by default, and physically grounded in one connected world."
    )


def _camera_intent(shot: dict, brief: dict, index: int) -> str:
    return ""

def _performance_intent(shot: dict) -> str:
    return ""


def _lighting_intent(shot: dict, brief: dict) -> str:
    return ""


def _shadow_intent(shot: dict, brief: dict) -> str:
    return ""


def _motion_intent(shot: dict, brief: dict) -> str:
    return ""


def _contact_intent(shot: dict) -> str:
    return ""


def _transition_intent(shot: dict, index: int) -> str:
    return ""


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
                "section_label": str(shot.get("section_label", "")).strip(),
                "zone": str(shot.get("zone", "")).strip(),
                "location": _literal_scene_description(shot),
                "literal_image": str(shot.get("literal_image", "")).strip(),
                "subject_action": str(shot.get("subject_action", "")).strip(),
                "visible_action": str(shot.get("visible_action", "")).strip(),
                "continuity_anchor": str(shot.get("beat_continuity_anchor", "")).strip(),
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
        "Rewrite each shot into natural English action lines for image and video prompts. "
        "Write like a music-video director describing what the same heroine is visibly doing inside one real place. "
        "Each line must be heroine-centered, start with 'She', and stay faithful to the provided action and place. "
        "Subject and action should be clear immediately. "
        "Do not mention camera, frame, shot, cut, continuity, prompt, image, reset, carry, or video. "
        "Do not invent new props, new characters, or new locations. "
        "Do not rely on decorative metaphor, symbolic narration, or viewer-facing language. "
        "Default to a single-heroine scene. Never introduce you, your, he, him, they, them, or another figure unless the source explicitly names or clearly requires another person. "
        "This visual pipeline should stay single-subject by default. Even if the lyric implies an addressee, reunion, longing, or mutual feeling, keep only one visible heroine in frame unless the source unmistakably requires two visible bodies in one shot. "
        "For this project, prefer one visible heroine moving through one connected world over any duet, reunion, embrace, or partner staging. "
        "Treat a lyric addressee, implied romance, remembered closeness, or emotional togetherness as non-visible unless the source clearly shows another body physically present in the same frame. "
        "If the source only implies emotional connection or shared feeling without a clearly visible second person, keep the shot single-subject and express the feeling through the heroine's body, direction, and contact with the space. "
        "Do not turn reunion, recognition, or togetherness into a literal second character unless the source plainly requires two visible bodies in frame. "
        "Do not use figure, person, silhouette, embrace, arms, together, them, or their unless the source unmistakably requires two visible bodies in one frame. "
        "Never output another woman, another man, the other woman, the other person, two women, two people, embrace, hug, clasp hands, or holding hands unless the source literally requires two visible bodies in the frame. "
        "Do not fixate on isolated body parts unless the original action truly depends on them. "
        "Avoid weak static phrasing such as merely standing still, waiting, feeling, remembering, or watching from a distance unless the beat absolutely requires it. "
        "Also avoid fallback-feeling verbs such as stays, remains, keeps her place, or holds still when a clearer visible progression is possible. "
        "Also avoid weak mood-led verbs such as watches, looks toward, gazes at, breathes out, smiles faintly, or lets the space act on her when a more readable physical action is available. "
        "Also avoid static reflective phrasing such as studies her reflection, lets the reflection settle, holds the smile, or lets a small smile rise when a more readable physical progression is possible. "
        "Prefer visible physical actions that read in a keyframe: walking, turning, stepping, leaning, touching, passing, climbing, descending, pausing at a surface, lifting a hand, pushing through, or changing direction. "
        "If the source action is static, convert it into the smallest believable visible progression in the same place. "
        "Do not use breath, hesitation, heartbeat, memory, loneliness, or pause as the main event when a faithful visible action can carry the same beat. "
        "If the source mentions breath, hesitation, memory, heartbeat, pause, or stillness, express it through a visible body action in the same space rather than breath-only or gaze-only wording. "
        "Prefer hands, shoulders, steps, and contact with nearby surfaces over pause-only or breath-only phrasing. "
        "When the beat is emotionally suspended, show that suspension through a turn, slowed step, hand on glass or rail, shift at a threshold, or another readable physical hold in the same place. "
        "If the source does not explicitly include another person, do not introduce one; keep the action strictly single-subject. "
        "If the source suggests hand-clasping, reunion, or facing someone without an explicitly visible second body, rewrite that beat as a single-subject action through opening hands, stepping forward, lifting her face, turning into the light, or moving into an opening in the same place. "
        "If the source suggests a hug or embrace without an explicitly visible second body, rewrite it as entering a pool of light, settling into open space, or opening her posture while remaining alone in frame. "
        "If the source implies someone turning away, waiting ahead, or receiving her movement without a clearly visible second body, rewrite that as her moving toward a doorway, reflection, threshold, lit opening, or changed direction in the same space. "
        "If the beat releases into a smile, express that release through movement into open space, lifted posture, or a brightened direction of travel rather than holding the smile as the main event. "
        "If section_label is Bridge or zone is compression, do not make stillness the main event. "
        "For Bridge/compression shots, avoid stand, hold, wait, remain, linger, or stay as the main verb. "
        "Instead, express compression through a small physical progression such as edging forward, shifting along the edge, bracing at a surface, tightening her step, leaning into wind or light, or turning toward an opening. "
        "The action must stay physically compatible with the given location. "
        "The environment should support the heroine's movement instead of overpowering it. "
        "ref_start_action_line should describe a strong readable first keyframe state. "
        "ref_end_action_line should describe the same action one natural beat later, still in the same place and scaled to the shot duration. "
        "ref_start_action_line and ref_end_action_line should feel like adjacent states in one continuous performance, not two unrelated poses. "
        "wan_action_line should describe the visible transition between those keyframes in one compact natural sentence with motion or directional change. "
        "wan_action_line should never reduce the bridge to only pausing, only breathing, or only watching. "
        "Keep the language concrete, visual, and screen-readable for a cinematic live-action music video.\n\n"
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
    return lighting
