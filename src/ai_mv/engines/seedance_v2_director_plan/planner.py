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
        ref_archetype = _infer_ref_archetype(shot)
        shot_id = str(shot.get("shot_id", "")).strip()
        current = {
            **dict(shot),
            "duration_sec": float(durations.get(shot_id, 2.0)),
            "ref_archetype": ref_archetype,
            "ref_archetype_contract": _ref_archetype_contract(ref_archetype),
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
        current["dominant_action"] = ""
        current["continuity_delta"] = ""
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
                "story_role": str(shot.get("story_role", "")).strip(),
                "zone": str(shot.get("zone", "")).strip(),
                "location": _literal_scene_description(shot),
                "dominant_scene_grammar": str(shot.get("dominant_scene_grammar", "")).strip(),
                "primary_surface": str(shot.get("primary_surface", "")).strip(),
                "support_detail": str(shot.get("support_detail", "")).strip(),
                "literal_image": str(shot.get("literal_image", "")).strip(),
                "subject_action": str(shot.get("subject_action", "")).strip(),
                "visible_action": str(shot.get("visible_action", "")).strip(),
                "continuity_anchor": str(shot.get("beat_continuity_anchor", "")).strip(),
                "payoff_role_hint": str(shot.get("payoff_role_hint", "")).strip(),
                "visual_role": str(shot.get("visual_role", "")).strip(),
                "ref_archetype": str(shot.get("ref_archetype", "")).strip(),
                "ref_archetype_contract": str(shot.get("ref_archetype_contract", "")).strip(),
                "duration_sec": float(shot.get("duration_sec", 2.0) or 2.0),
            }
        )
    try:
        if ping_codex(config):
            rewritten = _rewrite_with_codex(config, rows)
            if rewritten:
                for shot in shot_packages:
                    row = rewritten.get(str(shot.get("shot_id", "")).strip(), {})
                    dominant_action = " ".join(str(row.get("dominant_action", "")).strip().split())
                    continuity_delta = " ".join(str(row.get("continuity_delta", "")).strip().split())
                    start_line = " ".join(str(row.get("ref_start_action_line", "")).strip().split())
                    end_line = " ".join(str(row.get("ref_end_action_line", "")).strip().split())
                    wan_line = " ".join(str(row.get("wan_action_line", "")).strip().split())
                    shot["dominant_action"] = dominant_action or _dominant_action_fallback(shot)
                    shot["continuity_delta"] = continuity_delta or _continuity_delta_fallback(shot)
                    shot["ref_start_action_line"] = start_line or _natural_start_action_line(shot)
                    shot["ref_end_action_line"] = end_line or _natural_end_action_line(shot)
                    shot["wan_action_line"] = wan_line or shot["ref_end_action_line"] or shot["ref_start_action_line"]
                return
    except Exception:
        pass
    for shot in shot_packages:
        shot["dominant_action"] = _dominant_action_fallback(shot)
        shot["continuity_delta"] = _continuity_delta_fallback(shot)
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
                        "dominant_action": {"type": "string"},
                        "continuity_delta": {"type": "string"},
                        "ref_start_action_line": {"type": "string"},
                        "ref_end_action_line": {"type": "string"},
                        "wan_action_line": {"type": "string"},
                    },
                    "required": ["shot_id", "dominant_action", "continuity_delta", "ref_start_action_line", "ref_end_action_line", "wan_action_line"],
                },
            }
        },
        "required": ["shots"],
    }
    prompt = (
        "Rewrite each shot into natural English action lines for image and video prompts. "
        "Write like a music-video director describing what the same heroine is visibly doing inside one real place. "
        "Each shot also has a hidden REF archetype with a proven prompt grammar; use that archetype as guidance for what kind of image structure this model tends to understand best. "
        "Decide the shot's dominant physical relationship first: body-led, crossing-led, or surface-led. "
        "Then decide the dominant action, the primary surface or path carrying that action, one optional support detail that stays secondary, and the visible continuity delta from start to end. "
        "The dominant action must stay more important than any support detail. "
        "Use section_label, story_role, visual_role, and payoff_role_hint as hidden dramatic guidance for why the shot exists in the sequence, but do not repeat those labels in the output. "
        "Use ref_archetype and ref_archetype_contract as hidden guidance for what prompt structure is most reliable for this shot family. "
        "Each action line should feel like a necessary keyframe in a music-video chain, not just a good standalone caption. "
        "opening_frame should establish her direction and presence immediately. "
        "continuity_frame should visibly carry the same movement or intention forward. "
        "pressure_frame should tighten the movement or compress the body-space relation. "
        "handoff_frame should end on a readable direction, crossing, or body shift that hands cleanly into the next shot. "
        "payoff_frame should land a decisive visible change or arrival, not merely a more atmospheric version of the same pose. "
        "Each line must be heroine-centered, start with 'She', and stay faithful to the provided action and place. "
        "Subject and action should be clear immediately. "
        "Keep the heroine as the main subject of the image, not the architecture around her. "
        "Use dominant_scene_grammar, primary_surface, and support_detail as a meaning hierarchy: action first, surface second, support detail last. "
        "support_detail is optional guidance, not required wording. If it distracts from the primary surface or makes the shot more symbolic than physical, leave it out of the action lines. "
        "Honor the ref_archetype_contract unless the source clearly requires a different nearby physical action. "
        "If ref_archetype_contract suggests source surface to destination surface, continuous handrail contact, wall proximity, curb-at-feet proximity, destination space beyond, over-shoulder look-back, or a small continuation hint, prefer that structure over a generic caption. "
        "If ref_archetype is stair_descent, keep the action on stairs, stair run, handrail, or landing progression; do not make glass, reflection, or window mood the action nucleus. "
        "If ref_archetype is platform_edge, keep the action on the edge, yellow line, or forward stride by the drop; do not make blurred glass, a train window, or a nearby sign the action nucleus. "
        "If ref_archetype is threshold_crossing or doorway_handoff, keep the action on clearing the threshold, door edge, gate line, exit line, curb, or street edge; do not make the light beyond or the opening mood the event. "
        "If ref_archetype is gate_pass, keep the gate crossing primary and any ticket or card handling secondary inside that larger movement. "
        "If ref_archetype is sidewalk_continuation or curb_crossing, keep the action on stride, curb, crosswalk, pavement, or street edge; do not redirect the beat toward signage, traffic lights, windows, or surrounding glow. "
        "If ref_archetype is window_contact, keep the action on the edge contact and forward continuation; do not let reflection, signage, or surrounding light replace the bodily passage. "
        "If the place contains a strong symbol such as a gate, doorway, clock, sign, or reflection, do not let that object become more important than her body action. "
        "If the source contains a reflection, clock, sign, or glow together with a readable nearby surface or path, keep the surface or path primary and demote the symbolic element to background support. "
        "Prefer actions that keep her readable and present rather than distant and swallowed by the environment. "
        "Do not mention camera, frame, shot, cut, continuity, prompt, image, reset, carry, or video. "
        "Do not invent new props, new characters, or new locations. "
        "Do not rely on decorative metaphor, symbolic narration, or viewer-facing language. "
        "Prefer one clear body action, one clear place anchor, and at most one clear contact detail in each line. "
        "If continuity is likely to drift, it is acceptable to keep one small identity hook that is already part of the heroine, such as her high ponytail, as long as the line still reads like natural prose and not a checklist. "
        "This is especially acceptable in difficult REF shots such as final-opening crossings or tight bridge contact shots. "
        "For difficult REF shots, a strong pattern is: same heroine, one small identity hook when needed, one body-led action, one place anchor, and one tactile contact detail. "
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
        "In payoff or release shots, do not let spreading fingers, opening hands, breathing out, or looking across space become the main event when she can instead take a step, clear an edge, pass a gate, or carry her stride forward in the same place. "
        "Do not let looking toward lit windows, looking through glass, watching a display, or keeping time with a clock become the main action when she can instead step, turn, brace, pass, descend, or cross within the same place. "
        "Also avoid static reflective phrasing such as studies her reflection, lets the reflection settle, holds the smile, lets a small smile rise, laughs under the light, lifts her face to the light, lifts into the light, opens her fingers toward space, lets the motion settle, lets the floor steady, or holds her ground when a more readable physical progression is possible. "
        "Prefer visible physical actions that read in a keyframe: walking, turning, stepping, leaning, touching, passing, climbing, descending, pausing at a surface, lifting a hand, pushing through, or changing direction. "
        "Favor verbs that read as a full-body or torso-led action, not only a tiny gesture. "
        "Keep those verbs concrete and filmable: prefer step, pass, clear, cross, turn, lean, brace, touch, climb, descend, lengthen her stride, or shift her weight over generic force verbs such as drives, claims, opens the night, breaks free, surges, or conquers the space. "
        "Close body-surface contact often reads better than pure atmosphere, so prefer actions like leaning toward glass, sliding a hand along a rail, bracing at an edge, or stepping through an opening when they fit the source. "
        "If a reflection appears, describe her contact with the glass, window edge, umbrella surface, or wet pavement before mentioning the reflection itself. "
        "Do not let checking a reflection, facing a reflection, or following reflected light become the main action when she can instead pass the glass, clear the door edge, trace the frame, or cross the threshold. "
        "If a clock or sign appears with a doorway, gate, rail, street edge, or platform path, keep the action on the crossing surface or path and let the clock or sign stay secondary. "
        "If glass, a passage line, a platform path, a gate light, a rail, a threshold, or a sidewalk already carries the movement, omit the stopped clock entirely unless she is directly touching, reading, or using it. "
        "If a platform edge, threshold, gate line, doorway edge, passage, or platform path already carries the movement, omit ticking clock, station clock, slow clock, or clock light entirely unless the source literally requires clock contact. "
        "If a blinking light, call light, lit button, or small indicator appears beside a lane, doorway edge, threshold, gate line, wall, or passage, keep that light as a side detail and keep the main action on the larger surface she is crossing. "
        "If a doorway or door edge is present, keep the action on the threshold, passage, frontage, sidewalk, or platform side; do not turn it into a room-entry or bright interior set-piece unless the source literally enters a room. "
        "Avoid vague release locations such as open lane, city margin, city line, widening night, blue morning light, or bright glass edge when the same beat already contains a more playable surface like pavement, platform path, curb, gate lane, exit line, outer sidewalk, or doorway threshold. "
        "Outside release too, do not let lit windows, glowing displays, glass doors, or stopped clocks become the main place or main event when rail, platform edge, turnstile lane, stair, threshold, crosswalk, sidewalk, curb, or gate line can carry the action more clearly. "
        "If lit windows are only nearby, keep the action and place on the platform end, passage line, rail, curb, gate lane, threshold, or wet pavement rather than on the windows. "
        "If a ticket, card, or small object appears with a stopped clock, keep that object as a hand movement inside a larger step, pass, or threshold action rather than turning the shot into a still life under the clock. "
        "If a ticket or card appears with a clock, do not make her fix her gaze on the clock; keep her stride, turn, pass, or threshold movement primary while the hand action stays secondary. "
        "If a gate lane or turnstile lane appears with a clock, do not let the start state become looking up at the clock; make the lane crossing, slowdown, poised lean, or threshold-ready body shift the readable action instead. "
        "If a handrail, rail, or platform edge appears with a clock, do not let the shot become gaze-up-at-clock. Keep her hand, shoulders, and next step on the rail or edge primary while the clock stays only overhead timing. "
        "If a window, glass, or lit opening appears with a readable forward path, do not make looking toward the light or window the action. Keep the action on passing the edge, brushing the wall, tightening the step, or turning back once while still moving. "
        "If lit windows are present, they must remain background support. Do not build a still subject around lit windows, and do not let them replace the body's forward continuation. "
        "If support_detail is a clock, stopped clock, sign, lit windows, signboard light, or other symbolic timing/light cue, it is acceptable to omit that detail entirely from dominant_action, start_state, end_state, and wan_action_line when the primary surface already gives a clearer readable beat. "
        "For doorway, gate, and final-opening shots, prefer step-through or cross-through actions with one hand guiding past a rail, gate, or edge instead of treating the bright opening itself as the main subject. "
        "If a doorway or opening is present, write it as a practical threshold crossing with a door edge, hinge side, threshold strip, or first step through it, not as a portal image or symbolic opening. "
        "When ending a doorway or gate action, land on threshold, gate line, curb, pavement, street edge, or passage beyond it; avoid awkward destination nouns such as frame or abstract opening space. "
        "If final-opening continuity feels fragile, it is acceptable to include one small identity hook, such as her high ponytail, inside the natural prose while keeping the action body-led. "
        "Treat final release as continued forward crossing in the same world, not as a symbolic image of glow, aftermath, or emotional suspension. "
        "For Final Chorus shots, keep the heroine outward-facing and in motion. Prefer walking, crossing, stepping through, clearing, passing, or continuing forward over inward release, private reflection, or symbolic pause. "
        "In final-opening shots, avoid describing distant neon or a bright point farther ahead if the heroine can already be shown crossing the threshold in front of her. "
        "For final-opening shots, prefer clears the gate, passes the rail, crosses the exit line, steps through the threshold, or moves one pace farther through the doorway over holds her ground or lifts into the light. "
        "For final-opening shots, do not make smiling by a window, facing a reflection, a train window reflection, a clock outside, lingering under glow, following warm light ahead, pale dawn light, walking toward a vague opening, reflections brightening behind her, lifting her face to a sign, opening her fingers toward a clearing path, settling/steadying motion, a folded ticket, fading light in her hand, a glass storefront reflection, a lane of light ahead, or lingering light after the last train the main event when a forward crossing action is possible in the same place. "
        "For final-opening shots, keep the destination physical and immediate: gate, threshold, doorway, exit line, stair top, platform edge, or crosswalk, not a distant bright point or symbolic sign. "
        "If daybreak, morning, or wider air is present in a release shot, keep it as background light only and not as the destination, place anchor, or event itself. "
        "If a release shot involves a street crossing, platform exit, or curb entry, anchor the action on the curb, crosswalk, street edge, platform exit line, or threshold surface first, not on glass frontage or surrounding skyline. "
        "If the source action is static, convert it into the smallest believable visible progression in the same place. "
        "Do not use breath, hesitation, heartbeat, memory, loneliness, or pause as the main event when a faithful visible action can carry the same beat. "
        "If the source mentions breath, hesitation, memory, heartbeat, pause, or stillness, express it through a visible body action in the same space rather than breath-only or gaze-only wording. "
        "Prefer hands, shoulders, steps, and contact with nearby surfaces over pause-only or breath-only phrasing. "
        "When the beat is emotionally suspended, show that suspension through a turn, slowed step, hand on glass or rail, shift at a threshold, or another readable physical hold in the same place. "
        "If the source does not explicitly include another person, do not introduce one; keep the action strictly single-subject. "
        "If the source suggests hand-clasping, reunion, or facing someone without an explicitly visible second body, rewrite that beat as a single-subject action through crossing a gate, passing a rail, stepping through a doorway, clearing a platform edge, or reaching the far side of a street in the same place. "
        "If the source suggests a hug or embrace without an explicitly visible second body, rewrite it as a continued step-through or cross-through action while remaining alone in frame. "
        "If the source implies someone turning away, waiting ahead, or receiving her movement without a clearly visible second body, rewrite that as her changed direction, cleared threshold, passed gate rail, or continued forward crossing in the same space. "
        "If the beat releases into a smile, express that release through crossing a threshold, clearing a gate, reaching the far side of a street or platform edge, or stepping through a doorway rather than holding the smile as the main event. "
        "Avoid generic release wording such as one steady rhythm, calm steady pace, open space, brighter direction of travel, or path clearing when a specific crossing action exists in the same place. "
        "In Final Chorus or other release shots, keep light only as supporting illumination on the surface she is crossing; do not let light, glow, dawn, sign, or reflection become the action itself. "
        "In Final Chorus or other release shots, prefer exit line, turnstile lane, gate rail, stair top, curb crossing, street edge, or platform edge as the immediate destination over train window reflection, station clock, signboard, skyline, vague opening, or dawn color. "
        "In Final Chorus or other release shots, avoid generic alley end or alley mouth phrasing when curb, crosswalk, street edge, sidewalk, exit line, or station frontage can name the same movement more concretely. "
        "In Final Chorus or other release shots, omit lit windows from the place anchor when sidewalk, curb, street edge, exit line, or frontage already gives a clearer path of movement. "
        "In Final Chorus or other release shots, do not let wet train window, lit windows, or window line become the main place or payoff when platform edge, threshold, doorway, crosswalk, outer sidewalk, or street edge can describe the same forward movement more directly. "
        "In Final Chorus or other release shots, do not let touching cold glass or turning back to glass become the main beat when the same motion can land more clearly on the exit line, gate opening, platform edge, crosswalk, or street edge. "
        "Avoid late poetic release phrases such as last bright strip, last light, living neon path, widening night, or lingering glow when pavement, platform end, curb, gate lane, exit line, or outer sidewalk can describe the same forward movement more concretely. "
        "If section_label is Bridge or zone is compression, do not make stillness the main event. "
        "For Bridge/compression shots, avoid stand, hold, wait, remain, linger, or stay as the main verb. "
        "Instead, express compression through a small physical progression such as edging forward, shifting along the edge, bracing at a surface, tightening her step, leaning into wind or light, or turning toward a clearer path. "
        "Avoid abstract environment phrases such as tight pocket, quiet light, trembling glass light, map-like glow, brighter edge of town, last strip of night, platform glow spreads, or end of the night when a more literal place and body action can carry the beat. "
        "For Bridge/compression shots, prefer nearby surfaces such as window, rail, edge, wall, or gate over distant symbolic targets such as a clock or far city glow when both are possible. "
        "In Bridge/compression, favor contact or near-contact with the closest surface instead of aiming the action at a distant object. "
        "For Bridge/compression shots, if glass or a clock appears, keep the step, rail, platform end, curb, or passage line primary and reduce the glass or clock to background timing or side detail. "
        "If a stair, rail, tread, stair top, or stairwell is present, keep the action visibly on that stair geometry; do not let the shot flatten into a generic straight walk on an open road or broad plaza. "
        "The action must stay physically compatible with the given location. "
        "The environment should support the heroine's movement instead of overpowering it. "
        "dominant_action should be one short natural phrase naming the shot's main physical action. "
        "continuity_delta should be one short natural phrase naming what visibly changes from start to end. "
        "continuity_delta must describe the heroine's body, direction, or contact changing against the primary surface or path, not a reflection shifting, light moving, or another support detail drifting. "
        "ref_start_action_line should describe a strong readable first keyframe state. "
        "ref_start_action_line should make the shot's dramatic function legible as soon as the image is seen. "
        "ref_end_action_line should describe the same action one natural beat later, still in the same place and scaled to the shot duration. "
        "ref_end_action_line should not just restate the start; it should reveal what changed in her progress, pressure, or arrival. "
        "When showing payoff or arrival, name the concrete surface, edge, curb, gate line, road line, stair top, or threshold she has reached instead of describing abstract victory or open destiny. "
        "In handoff or payoff shots, do not end on glass behind her, reflection behind her, or light lingering behind her if the next readable state can instead end on pavement, curb, street edge, exit line, sidewalk, or threshold already in front of her. "
        "Make the difference between start and end visible enough that the two keyframes do not collapse into the same picture. "
        "ref_start_action_line and ref_end_action_line should feel like adjacent states in one continuous performance, not two unrelated poses. "
        "Use literal place language such as window, platform edge, gate, rail, stair, passage, or doorway instead of atmosphere-first wording when both are possible. "
        "wan_action_line should describe the visible transition between those keyframes in one compact natural sentence with motion or directional change. "
        "wan_action_line should make clear what is actually progressing between the start and end states. "
        "wan_action_line should stay physically specific and should not rely on abstract phrases such as path ahead, open ground, brighter future, or the night opening in front of her. "
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


def _infer_ref_archetype(shot: dict) -> str:
    primary_surface = str(shot.get("primary_surface", "")).strip().lower()
    subject_action = str(shot.get("subject_action", "")).strip().lower()
    visible_action = str(shot.get("visible_action", "")).strip().lower()
    support_detail = str(shot.get("support_detail", "")).strip().lower()
    location = " ".join(
        [
            str(shot.get("location_description", "")).strip(),
            str(shot.get("environment_anchor", "")).strip(),
        ]
    ).lower()
    text = " ".join(
        [
            str(shot.get("visual_role", "")).strip(),
            str(shot.get("zone", "")).strip(),
            location,
            primary_surface,
            support_detail,
            subject_action,
            visible_action,
            str(shot.get("literal_image", "")).strip(),
        ]
    ).lower()
    if any(token in text for token in ("bench", "seat", "sits", "seated")):
        return "bench_rest"
    if any(token in text for token in ("over one shoulder", "looks back", "looks back once", "glances back", "turns back", "turns her head back")):
        return "turn_back_once"
    if any(token in primary_surface for token in ("handrail", "rail", "railing")) and not any(token in primary_surface for token in ("stair", "stairs", "stairwell")):
        return "brace_pause"
    if any(token in primary_surface for token in ("escalator", "escalator steps")):
        return "stair_descent"
    if any(token in primary_surface for token in ("underpass ramp", "ramp", "sloped passage", "slope")):
        return "ramp_descent"
    if any(token in primary_surface for token in ("corridor", "hall")) and "indoor" in text:
        return "indoor_corridor"
    if any(token in primary_surface for token in ("turnstile", "ticket gate", "gate lane")):
        return "gate_pass"
    if any(token in primary_surface for token in ("stair", "stairs", "stairwell", "tread", "handrail", "rail")) and "stair" in text:
        return "stair_descent"
    if any(token in primary_surface for token in ("platform edge", "yellow line")):
        return "platform_edge"
    if any(token in primary_surface for token in ("crosswalk", "far curb", "curb")) and any(
        token in f"{subject_action} {visible_action} {location}" for token in ("cross", "crosses", "crossing", "far side")
    ):
        return "curb_crossing"
    if any(token in primary_surface for token in ("threshold", "exit line", "street edge")):
        return "threshold_crossing"
    if any(token in primary_surface for token in ("doorway", "door edge", "opening")):
        return "doorway_handoff"
    if any(token in primary_surface for token in ("passage", "wall")) and any(token in text for token in ("rail", "narrow", "close")):
        return "passage_compression"
    if any(token in primary_surface for token in ("window", "glass")):
        return "window_contact"
    if "sidewalk" in primary_surface or "pavement" in primary_surface or "street" in primary_surface:
        return "sidewalk_continuation"
    if any(token in text for token in ("passage", "alley", "narrow")) and any(token in text for token in ("wall", "rail")):
        return "passage_compression"
    if any(token in text for token in ("threshold", "exit line", "wet street edge", "curb crossing", "street edge")):
        return "threshold_crossing"
    if any(token in text for token in ("pause", "braces", "braced", "holds for a beat", "holds her step")):
        return "brace_pause"
    return "sidewalk_continuation"


def _ref_archetype_contract(archetype: str) -> str:
    contracts = {
        "threshold_crossing": "Use source surface to destination surface with contact release; keep the threshold secondary to her crossing.",
        "stair_descent": "Use continuous stepped surface with continuous handrail contact; keep stair geometry literal and avoid flattening into a generic walk.",
        "passage_compression": "Use wall proximity plus forward movement plus trailing rail; keep the narrowness visible and avoid broad walkway staging.",
        "platform_edge": "Use edge proximity near her feet plus forward continuation; keep the platform edge more important than rails or skyline.",
        "gate_pass": "Use beyond-the-gate continuation plus destination space ahead; keep the gate as a crossing point, not the main subject.",
        "window_contact": "Use present-tense surface contact plus forward continuation; keep reflection secondary to her contact with the window edge or rail.",
        "curb_crossing": "Use plain crosswalk locomotion plus destination curb; avoid extra objects that compete with the crossing.",
        "sidewalk_continuation": "Use plain locomotion with optional free-arm motion or curb-at-feet proximity; keep the street portable and open-world.",
        "doorway_handoff": "Use doorway crossing plus literal destination space beyond; do not let the metal frame dominate the shot.",
        "brace_pause": "Use simple braced contact with minimal interpretation; keep the pose natural and avoid over-staging the pause.",
        "ramp_descent": "Use slope descent plus trailing rail; keep the ramp identity distinct from stairs and flat sidewalks.",
        "turn_back_once": "Use over-shoulder look-back plus explicit forward continuation; preserve face readability while the body keeps moving.",
        "indoor_corridor": "Use narrow corridor volume plus wall proximity plus forward continuation; keep indoor neutrality stronger than decorative lights.",
        "bench_rest": "Use seated rest plus one small continuation hint; keep the seated pose natural rather than fully settled or theatrical.",
    }
    return contracts.get(archetype, "Use one heroine, one readable body action, one nearby surface, and one chain-friendly visible progression.")


def _dominant_action_fallback(shot: dict) -> str:
    return " ".join(str(shot.get("subject_action", "")).strip().split()) or " ".join(str(shot.get("visible_action", "")).strip().split())


def _continuity_delta_fallback(shot: dict) -> str:
    visual_role = str(shot.get("visual_role", "")).strip().lower()
    zone = str(shot.get("zone", "")).strip().lower()
    if "payoff" in visual_role or "open_world_peak" in zone:
        return "she reaches the next concrete surface and keeps going"
    if "handoff" in visual_role:
        return "her direction becomes clearer for the next shot"
    if "pressure" in visual_role or "compression" in zone:
        return "the same movement tightens inside the place"
    return "the action moves one readable step farther"


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
