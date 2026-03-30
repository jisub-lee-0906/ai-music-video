from __future__ import annotations

from ai_mv.core.contracts.seedance_v2_normalize import normalize_director_plan_v2
from ai_mv.core.director_brief import build_director_brief_intent


def build_director_plan_v2(config: dict, payload: dict) -> dict:
    brief = build_director_brief_intent(config)
    scene_plan = payload["scene_plan_v2"]
    shot_packages: list[dict] = []
    previous_shot: dict | None = None
    for index, shot in enumerate(scene_plan.get("shot_packages", []), start=1):
        current = {
            **dict(shot),
            "camera_intent": _camera_intent(shot, brief, index),
            "performance_intent": _performance_intent(shot),
            "lighting_intent": _lighting_intent(shot, brief),
            "shadow_intent": _shadow_intent(shot, brief),
            "contact_intent": _contact_intent(shot),
            "motion_intent": _motion_intent(shot, brief),
            "transition_intent": _transition_intent(shot, index),
        }
        current["continuity_anchor"] = _continuity_anchor(current, previous_shot)
        current["carryover_state"] = _carryover_state(current, previous_shot)
        current["incoming_transition"] = _incoming_transition(current, previous_shot)
        current["new_change"] = _new_change(current, previous_shot)
        shot_packages.append(current)
        previous_shot = current
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
    motif = str(shot.get("motif_family", "")).strip().lower()
    family = str(shot.get("environment_family", "")).strip().lower()
    band = str(shot.get("camera_distance_band", "")).strip().lower()
    visual_role = str(shot.get("visual_role", "")).strip().lower()
    phase = _section_phase(shot)
    if visual_role == "opening_frame":
        return _opening_camera_for_family(motif, family, band)
    if visual_role == "pressure_frame":
        return _pressure_camera_for_family(motif, family, band)
    if visual_role == "payoff_frame":
        return _camera_for_motif(motif, family, band, "payoff")
    if visual_role == "handoff_frame":
        return _handoff_camera_for_family(motif, family, band)
    if "final chorus" in section:
        return _camera_for_motif(motif, family, band, "payoff")
    if "chorus" in section:
        if phase == "entry":
            return _camera_for_motif(motif, family, band, "entry")
        if phase == "exit":
            return _camera_for_motif(motif, family, band, "exit")
        return _camera_for_motif(motif, family, band, "middle")
    if "pre" in section:
        return "tighten into a forward-leaning medium frame and let the lens pressure build toward the threshold"
    if "bridge" in section:
        return "compress into a tighter frame, trim the empty space, and lock attention into one tense pocket"
    if zone in {"threshold", "edge"}:
        return "keep the heroine slightly off-center and make the threshold geometry legible behind her"
    if "train window" in motif:
        return "favor a side-on medium frame that keeps the window reflections traveling behind her profile"
    if "ticket gate" in motif:
        return "favor a medium frame that lets foreground gate elements cut across the composition"
    if "curb reflection" in motif or "puddle" in motif:
        return "favor a lower camera line so reflections and wet ground take up more of the frame"
    return "favor objects, surfaces, and environmental depth before moving into direct face coverage"


def _camera_for_motif(motif: str, family: str, band: str, phase: str) -> str:
    if family == "wet_pavement_reflection" or "puddle" in motif:
        if phase == "payoff":
            return "open into a slightly wider street-level frame, keep the heroine offset rather than centered near the wet curb, and let reflective pavement stretch behind and below her"
        if phase == "entry":
            return "shift into a medium-wide street-level frame with the heroine near the wet curb and reflective pavement opening beside her"
        if phase == "exit":
            return "commit to a medium-wide curbside frame with more reflective ground and a longer street plane behind her"
        return "hold a medium-wide curbside frame with the heroine clearly separated from the reflective pavement and city depth behind her"
    if family == "wet_curb_reflection" or "curb reflection" in motif:
        if phase == "payoff":
            return "open into a slightly wider curbside frame, keep the heroine offset near the reflective edge, and let the street depth expand behind her without turning it into a centered hero pose"
        if phase == "entry":
            return "shift into a medium-wide curbside frame with reflective asphalt reading clearly beside her"
        if phase == "exit":
            return "commit to a medium-wide curbside frame with longer street depth and lateral city drift behind her"
        return "hold a medium-wide curbside frame with clear reflective ground and readable space behind her"
    if family == "train_window_glass" or "train window" in motif:
        if phase == "entry":
            return "shift into a side-on medium frame that keeps the train window, profile, and traveling reflections readable together"
        if phase == "exit":
            return "commit to a side-on medium frame with more exterior travel visible beyond the glass"
        if phase == "payoff":
            return "open into a wider side-on window frame, keep the heroine offset against the glass, and let the city travel outside the train without squaring her to camera"
        return "hold a side-on medium window frame with profile, glass, and reflected motion clearly readable"
    if family == "ticket_gate_lane" or "ticket gate" in motif:
        if phase == "entry":
            return "shift into a medium-wide gate-lane frame with the heroine offset inside the barrier geometry so the station depth reads before direct portrait coverage"
        if phase == "exit":
            return "commit to a medium-wide gate-lane frame with more station depth opening behind her while keeping the ticket barriers readable"
        if phase == "payoff":
            return "open into a slightly wider station-gate frame, keep the heroine offset inside the lane geometry, and let the space deepen behind her without collapsing into a centered poster frame"
        return "hold a medium-wide gate-lane frame with waist-high ticket barriers, card readers, and entry lane posts clearly readable beside her"
    if family == "platform_signage" or "platform sign glow" in motif:
        if phase == "entry":
            return "shift into a medium-wide platform frame with signage and lamps opening above and behind her"
        if phase == "exit":
            return "commit to a wider platform frame with more sign glow and station depth behind her"
        if phase == "payoff":
            return "open into a slightly wider platform frame, keep the heroine offset under the sign glow, and let the station depth bloom behind her without flattening into a centered still"
        return "hold a medium-wide platform frame with readable signage, lamps, and environmental depth"
    if family == "stair_landing" or "stair landing" in motif:
        if phase == "entry":
            return "start on a medium-wide stair-landing frame with the heroine offset against the rail and receding steps so the space reads first"
        if phase == "exit":
            return "commit to a wider stair-landing frame with more rail depth and descending steps behind her"
        if phase == "payoff":
            return "open into a wider stair-landing frame, keep the heroine full-figure beside the rail, and let the steps recede behind her"
        return "hold a medium-wide stair-landing frame with rail geometry and step depth clearly readable"
    return "hold a medium-wide cinematic frame with stronger environmental scale and readable shoulder-led movement"


def _opening_camera_for_family(motif: str, family: str, band: str) -> str:
    if family == "wet_pavement_reflection":
        return "start on a medium-wide street-level frame that lets the heroine enter from one side while reflective pavement and city depth pull the eye past her"
    if family == "wet_curb_reflection":
        return "start on a medium-wide curbside frame with the heroine offset from center and the reflective street plane opening around her"
    if family == "ticket_gate_lane":
        return "start on a medium-wide gate-lane frame with the heroine offset inside the barrier geometry so the station depth reads before direct portrait coverage"
    if family == "train_window_glass":
        return "start on a side-on medium frame where the profile, glass, and passing exterior light create an immediate cinematic layer"
    if family == "platform_signage":
        return "start on a medium-wide platform frame with signage and overhead lamps shaping the space around her before the frame settles"
    if family == "stair_landing":
        return "start on a medium-wide stair-landing frame with the heroine offset against the rail and receding steps so the space reads first"
    return "start on an offset medium-wide frame that prioritizes spatial tension before direct full-body presentation"


def _pressure_camera_for_family(motif: str, family: str, band: str) -> str:
    if family == "train_window_glass":
        return "compress into a tighter side-on frame so the profile, glass, and reflections feel pressurized inside one narrow strip of space"
    if family == "ticket_gate_lane":
        return "compress into a tighter gate-lane frame and let the waist-high barriers crowd the heroine without losing body readability"
    return "compress into a tighter frame that trims empty space and turns the environment into a pressurized pocket around her"


def _handoff_camera_for_family(motif: str, family: str, band: str) -> str:
    if family == "wet_pavement_reflection":
        return "hold the same medium-wide street-level distance but angle the body and street plane so the motion feels carried forward into the next cut"
    if family == "wet_curb_reflection":
        return "hold the same curbside distance and leave more open street depth in the direction of motion so the next cut can inherit it"
    if family == "ticket_gate_lane":
        return "hold the same gate-lane distance and leave the lane opening in front of her so the cut can carry through the station geometry"
    if family == "train_window_glass":
        return "hold the same side-on distance and let the exterior travel continue past the profile so the cut inherits the direction"
    return "hold the same framing band but leave more directional space in front of the movement so the cut can absorb it"


def _performance_intent(shot: dict) -> str:
    zone = str(shot.get("zone", "")).strip().lower()
    motif = str(shot.get("motif_family", "")).strip().lower()
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
        if "stair" in motif:
            return "the next step taken at measured pace, one foot clearly loaded before the other, with one hip and shoulder arriving before the other"
        return "continuing through the lane with measured pace, asymmetrical weight, and restrained body language"
    if "window" in motif:
        return "the body staying oriented along one clear side-facing direction so the profile shift reads cleanly"
    if "gate" in motif:
        return "moving through the lane with one clear shoulder-led turn while staying inside the same directional flow"
    if "reflection" in motif or "puddle" in motif:
        return "one step landing clearly before the other side settles so the reflected movement reads in the ground"
    return "moving through the close space with one readable, uneven body-led action"


def _lighting_intent(shot: dict, brief: dict) -> str:
    zone = str(shot.get("zone", "")).strip().lower()
    motif = str(shot.get("motif_family", "")).strip().lower()
    if zone == "open_world_peak":
        return "let the recurring city lights align into the brightest payoff of the whole piece"
    if zone in {"threshold", "edge"}:
        return "use sign glow and floor reflections to sharpen the feeling of crossing a line"
    if zone == "compression":
        return "compress the light into one tighter source with readable directional contrast"
    if zone == "residue":
        return "let the last pools of light linger after the main action has already passed"
    if "window" in motif:
        return "let moving window reflections skim across the frame while keeping skin tones grounded"
    if "gate" in motif:
        return "mix hard station practicals with cooler reflected spill around the gate surfaces"
    return brief["lighting_bias"]


def _shadow_intent(shot: dict, brief: dict) -> str:
    zone = str(shot.get("zone", "")).strip().lower()
    if zone == "compression":
        return "group the shadows into tighter directional shapes that narrow the frame"
    return brief["shadow_bias"] or "keep shadows readable and grounded rather than stylized or diffuse"


def _motion_intent(shot: dict, brief: dict) -> str:
    section = str(shot.get("section_label", "")).strip().lower()
    visual_role = str(shot.get("visual_role", "")).strip().lower()
    phase = _section_phase(shot)
    if visual_role == "opening_frame":
        return "keep the first motion cinematic and legible, with a small carry already in progress rather than a fully static posed start"
    if visual_role == "handoff_frame":
        return "let the motion resolve with enough carry-through in the body and environment that the next cut can inherit it cleanly"
    if visual_role == "pressure_frame":
        return "keep motion restrained and focused into small body shifts, with the environment reacting less than the performer"
    if "chorus" in section:
        if phase == "exit":
            return "let the motion resolve with a stronger carry-through in the body and more reactive background movement"
        return "let the motion open out through stable cinematic movement, stronger body carry, and a more reactive background"
    if "bridge" in section:
        return "keep the motion tighter and more pressurized, with the background reacting less"
    if "pre" in section:
        return "build motion through small forward pressure, sleeve and hair reaction, and restrained camera creep"
    return brief["motion_bias"]


def _contact_intent(shot: dict) -> str:
    family = str(shot.get("environment_family", "")).strip().lower()
    zone = str(shot.get("zone", "")).strip().lower()
    role = str(shot.get("visual_role", "")).strip().lower()
    if family == "wet_pavement_reflection":
        if role == "payoff_frame":
            return "keep the lower body grounded in the wet pavement, let the reflected step spread under her, and make the body read as part of the same street plane"
        return "keep the shoes grounded in the wet pavement, keep a readable reflection close to her feet, and let nearby light spill across the lower legs"
    if family == "wet_curb_reflection":
        if role == "payoff_frame":
            return "keep the leading step readable against the curb edge, let the reflective asphalt hold the lower-body line, and make the body open through the street depth instead of posing on top of it"
        return "keep one foot near the curb edge, let the wet asphalt reflect the legs, and make the body feel anchored to the street plane"
    if family == "ticket_gate_lane":
        if role == "payoff_frame":
            return "keep the body opened through the gate lane while the lane geometry still feels shared around her rather than flattened behind her"
        return "keep the body physically aligned with the waist-high gate barriers and make the lane geometry feel shared with her movement"
    if family == "train_window_glass":
        if role == "payoff_frame":
            return "keep the body close enough to the glass line that reflections and profile direction still feel tied to the same surface"
        return "keep the profile and body close enough to the glass line that reflections and skin proximity read as one shared surface instead of a pasted figure"
    if family == "platform_signage":
        if role == "payoff_frame":
            return "let station light spill across the face and shoulders while the feet stay locked into the platform plane and the body opens under the signage"
        return "let platform light spill onto the face and jacket while the feet stay locked to the station ground plane"
    if family == "stair_landing":
        if role == "payoff_frame":
            return "keep one foot clearly weighted on the step and make the stair depth read around the body as it opens"
        return "keep one foot planted on the landing and make the step depth read around her"
    if zone == "compression":
        return "anchor the body tightly into one small pocket of space so the frame does not feel composited"
    return "make the feet, body shadow, and nearby surfaces feel physically connected inside the same shot"


def _transition_intent(shot: dict, index: int) -> str:
    if index <= 1:
        return "establish the first connected zone without forcing a hard reset"
    if "open_world_peak" in str(shot.get("zone", "")):
        return "escalate through previous-end continuity into the largest payoff zone"
    return "advance through previous-end continuity and keep the cut feeling absorbed"


def _continuity_anchor(shot: dict, previous_shot: dict | None) -> str:
    family = str(shot.get("environment_family", "")).strip().lower()
    band = str(shot.get("camera_distance_band", "")).strip().lower()
    if not previous_shot:
        return "one readable spatial anchor in the same geography before larger movement"
    if family == str(previous_shot.get("environment_family", "")).strip().lower():
        if family == "wet_curb_reflection":
            return "the same wet curb edge, reflective asphalt plane, and medium-wide street direction"
        if family == "wet_pavement_reflection":
            return "the same wet pavement plane, shallow reflections, and street-level medium-wide geography"
        if family == "ticket_gate_lane":
            return "the same ticket-gate lane, waist-high barriers, and entry-lane direction"
        if family == "train_window_glass":
            return "the same side-on glass line, interior reflection layer, and exterior travel direction"
        if family == "platform_signage":
            return "the same platform depth, signage layer, and station light direction"
        if family == "stair_landing":
            return "the same stair landing, rail direction, and step depth"
    if band == str(previous_shot.get("camera_distance_band", "")).strip().lower():
        return f"the same {band.replace('_', '-')} framing band and directional screen flow"
    return "the same connected city block and previous-end continuity without a hard reset"


def _carryover_state(shot: dict, previous_shot: dict | None) -> str:
    if not previous_shot:
        return "a clean but already alive cinematic state rather than a flat reset pose"
    previous_family = str(previous_shot.get("environment_family", "")).strip().lower()
    current_family = str(shot.get("environment_family", "")).strip().lower()
    if previous_family != current_family:
        return _generic_continuity_state(previous_shot)
    prev_change = str(previous_shot.get("new_change", "")).strip()
    prev_perf = str(previous_shot.get("performance_intent", "")).strip()
    if prev_change:
        return prev_change
    if prev_perf:
        lowered = prev_perf[:1].lower() + prev_perf[1:] if prev_perf else prev_perf
        return f"the last body state where she {lowered.rstrip('.')}"
    return "the last readable body orientation and direction of motion"


def _incoming_transition(shot: dict, previous_shot: dict | None) -> str:
    if not previous_shot:
        return ""
    previous_family = str(previous_shot.get("environment_family", "")).strip().lower()
    current_family = str(shot.get("environment_family", "")).strip().lower()
    if previous_family == current_family:
        return ""
    previous_band = str(previous_shot.get("camera_distance_band", "")).strip().lower()
    current_band = str(shot.get("camera_distance_band", "")).strip().lower()
    if previous_band == current_band:
        return "preserve the same off-center screen direction and body axis from the previous frame while the environment shifts into the new space"
    return "preserve the previous frame's directional body flow and off-center staging while the environment changes"


def _generic_continuity_state(previous_shot: dict) -> str:
    role = str(previous_shot.get("visual_role", "")).strip().lower()
    family = str(previous_shot.get("environment_family", "")).strip().lower()
    if role == "payoff_frame":
        return "the same off-center release, lower-body weight shift, and directional body axis from the last frame"
    if role == "handoff_frame":
        return "the same carry-through direction and uneven body weight from the last frame"
    if family in {"wet_curb_reflection", "wet_pavement_reflection"}:
        return "the same street-level weight transfer and off-center body axis from the last frame"
    if family == "ticket_gate_lane":
        return "the same lane-driven body direction and off-center staging from the last frame"
    if family == "train_window_glass":
        return "the same side-on body axis and directional travel from the last frame"
    if family == "stair_landing":
        return "the same step-loaded body axis and uneven lower-body balance from the last frame"
    return "the same off-center body axis and directional motion from the last frame"


def _new_change(shot: dict, previous_shot: dict | None) -> str:
    role = str(shot.get("visual_role", "")).strip().lower()
    family = str(shot.get("environment_family", "")).strip().lower()
    if role == "opening_frame":
        if family in {"wet_curb_reflection", "wet_pavement_reflection"}:
            return "the first step entering the reflective street plane before the body fully settles"
        if family == "ticket_gate_lane":
            return "the first shoulder-led move into the gate lane before the body fully settles"
        if family == "stair_landing":
            return "the first loaded stair step and torso angle that opens the stair depth before the body fully balances"
        return "the first readable movement that turns the shot into a live moment"
    if role == "handoff_frame":
        return "the last body carry-through still pointing directly into the next cut"
    if role == "pressure_frame":
        return "one sharper head, shoulder, or hand change inside the compressed frame"
    if role == "payoff_frame":
        return _payoff_change_for_family(family)
    if family == "wet_pavement_reflection":
        return "one clear reflected step reading through the wet pavement"
    if family == "wet_curb_reflection":
        return "one curbside body shift with the street plane still readable"
    if family == "ticket_gate_lane":
        return "one shoulder-led advance along the gate lane"
    if family == "train_window_glass":
        return "one readable profile shift along the glass line"
    if family == "platform_signage":
        return "one body turn under the platform light"
    if family == "stair_landing":
        return "one measured stair-step change beside the rail with one hip and shoulder arriving before the other"
    return "one small readable body change while the surrounding space stays continuous"


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


def _payoff_change_for_family(family: str) -> str:
    if family == "stair_landing":
        return "a broader torso opening and weighted step that still stays tied to the rail and stair depth, with the free side arriving later"
    if family == "wet_curb_reflection":
        return "a broader body opening with the leading step still tracing the curb edge and one side arriving later than the other"
    if family == "wet_pavement_reflection":
        return "a broader stride with the reflected lower-body movement still readable and the body not yet fully settled"
    if family == "ticket_gate_lane":
        return "a broader body opening that still stays inside the gate lane and keeps the lane direction alive"
    if family == "train_window_glass":
        return "a broader release that still keeps the body tied to the glass line and reflected travel"
    if family == "platform_signage":
        return "a broader body opening under the platform glow with the station depth still carrying the frame"
    return "the widest body opening and strongest world-facing release of the section"
