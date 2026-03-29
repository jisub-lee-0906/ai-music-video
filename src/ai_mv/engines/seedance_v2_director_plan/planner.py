from __future__ import annotations

from ai_mv.core.contracts.seedance_v2_normalize import normalize_director_plan_v2
from ai_mv.core.director_brief import build_director_brief_intent


def build_director_plan_v2(config: dict, payload: dict) -> dict:
    brief = build_director_brief_intent(config)
    scene_plan = payload["scene_plan_v2"]
    shot_packages: list[dict] = []
    for index, shot in enumerate(scene_plan.get("shot_packages", []), start=1):
        shot_packages.append(
            {
                **dict(shot),
                "camera_intent": _camera_intent(shot, brief, index),
                "performance_intent": _performance_intent(shot),
                "lighting_intent": _lighting_intent(shot, brief),
                "shadow_intent": _shadow_intent(shot, brief),
                "motion_intent": _motion_intent(shot, brief),
                "transition_intent": _transition_intent(shot, index),
            }
        )
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
        "Create a director-first shot plan with camera, performance, lighting, shadow, motion, and transition intents. "
        f"Camera bias={brief['camera_bias']}. Lighting bias={brief['lighting_bias']}. "
        f"Shadow bias={brief['shadow_bias']}. Motion bias={brief['motion_bias']}. "
        "Keep the heroine identity fixed and move the world through connected zones."
    )


def _camera_intent(shot: dict, brief: dict, index: int) -> str:
    zone = str(shot.get("zone", "")).strip().lower()
    section = str(shot.get("section_label", "")).strip().lower()
    if "final chorus" in section:
        return "open the frame wider and let the camera commit to the payoff space"
    if "chorus" in section:
        return "shift to a medium-wide cinematic frame that gives the world more air and sideward drift"
    if "pre" in section:
        return "tighten the framing and lean it gently forward as the threshold pressure rises"
    if "bridge" in section:
        return "compress the frame and re-aim attention into a smaller, tenser pocket"
    if zone in {"threshold", "edge"}:
        return "keep the heroine slightly off-center so the threshold line stays readable"
    return "favor objects, surfaces, and space before moving into direct face coverage"


def _performance_intent(shot: dict) -> str:
    zone = str(shot.get("zone", "")).strip().lower()
    if zone == "threshold":
        return "holds one measured breath before crossing the threshold"
    if zone == "edge":
        return "slows at the edge and steadies her shoulders before committing forward"
    if zone == "compression":
        return "keeps the body still under pressure and locks the gaze into one tense pocket"
    if zone == "open_world":
        return "moves into the wider space with controlled forward momentum and a readable turn of the shoulders"
    if zone == "open_world_peak":
        return "commits fully to the forward motion as the world opens around her"
    if zone == "residue":
        return "lets the movement fall away and holds the last after-image in place"
    if zone == "transit_lane":
        return "continues through the lane with measured pace and restrained body language"
    return "moves through the close space with one readable body-led action"


def _lighting_intent(shot: dict, brief: dict) -> str:
    zone = str(shot.get("zone", "")).strip().lower()
    if zone == "open_world_peak":
        return "let the recurring city lights align into the brightest payoff of the whole piece"
    if zone in {"threshold", "edge"}:
        return "use sign glow and floor reflections to sharpen the feeling of crossing a line"
    if zone == "compression":
        return "compress the light into one tighter source with readable directional contrast"
    if zone == "residue":
        return "let the last pools of light linger after the main action has already passed"
    return brief["lighting_bias"]


def _shadow_intent(shot: dict, brief: dict) -> str:
    zone = str(shot.get("zone", "")).strip().lower()
    if zone == "compression":
        return "group the shadows into tighter directional shapes that narrow the frame"
    return brief["shadow_bias"] or "keep shadows readable and grounded rather than stylized or diffuse"


def _motion_intent(shot: dict, brief: dict) -> str:
    section = str(shot.get("section_label", "")).strip().lower()
    if "chorus" in section:
        return "let the motion open out through stable cinematic movement and a more reactive background"
    if "bridge" in section:
        return "keep the motion tighter and more pressurized, with the background reacting less"
    return brief["motion_bias"]


def _transition_intent(shot: dict, index: int) -> str:
    if index <= 1:
        return "establish the first connected zone without forcing a hard reset"
    if "open_world_peak" in str(shot.get("zone", "")):
        return "escalate through previous-end continuity into the largest payoff zone"
    return "advance through previous-end continuity and keep the cut feeling absorbed"
