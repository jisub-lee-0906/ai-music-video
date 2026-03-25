from __future__ import annotations

from ai_mv.engines.visual_story_bible.brief_views import compact_section_atoms


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
        "The continuity_clause should describe a clean Japanese manga-anime look with thick clean outlines, cel-shaded color, and readable anime facial features. "
        "Write every ref prompt as a high-quality human-written image prompt, not a placeholder transition note. "
        "Assume the source image already contains the correct character identity, costume, and world. "
        "Your job is to describe one strong changed pose or changed action with a clean camera phrase so the model can preserve the character while making a visible new frame. "
        "Treat the TTI master anchor as a locked character sheet: keep the same face shape, hair shape, hair color, outfit silhouette, body proportions, and core attitude. "
        "Do not redesign the character, do not drift into realism or live-action language, and keep the same manga-anime heroine look established in TTI. "
        "Preserve the same clean anime face, readable eyes, hair silhouette, and attractive stylized body proportions from the master anchor. "
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
        "Another valid example: 'The same anime girl, now turning her eyes sharply to the left. Tight close-up. Clean manga-anime shading, thick clean outlines, readable anime features.' "
        "Another strong example: 'The same anime girl, now stepping through the ticket gate with her coat hem swinging behind her. Off-center walking shot. Clean manga-anime shading, thick clean outlines, readable anime features.' "
        "Another strong example: 'The same anime girl, now pressing one hand to the train window as city bands streak behind the glass. Layered train-window shot. Clean manga-anime shading, thick clean outlines, readable anime features.' "
        "Another strong example: 'The same anime girl, now stopping at the curb as puddle rings widen around her shoes. Low reflective street shot. Clean manga-anime shading, thick clean outlines, readable anime features.' "
        "Another strong example: 'The same anime girl, now pulling her shoulder back as a blue sign stripe crosses her jacket. Off-center platform shot. Clean manga-anime shading, thick clean outlines, readable anime features.' "
        "Another strong example: 'The same anime girl, now looking back over one shoulder as her hair swings across her cheek. Off-center medium shot. Clean manga-anime shading, thick clean outlines, readable anime features.' "
        "Another strong example: 'The same anime girl, now dragging the umbrella tip through the puddle and breaking the surface rings. Tight puddle insert shot. Clean manga-anime shading, thick clean outlines, readable anime features.' "
        "Another strong example: 'The same anime girl, now pressing two fingers to the train glass as station lights split across her reflection. Tight reflective shot. Clean manga-anime shading, thick clean outlines, readable anime features.' "
        "Bad example: 'The same anime girl, now posing beautifully. Nice shot. Clean manga-anime shading, thick clean outlines, readable anime features.' "
        "Bad example: 'The same anime girl, now standing in empty space. Medium shot. Clean manga-anime shading, thick clean outlines, readable anime features.' "
        "Bad example: 'The same anime girl, now leaning slightly toward the mood. Off-center shot. Clean manga-anime shading, thick clean outlines, readable anime features.' "
        "Bad example: 'The same anime girl, now drifting through the forecourt. Wide shot. Clean manga-anime shading, thick clean outlines, readable anime features.' "
        "Bad example: 'The same anime girl, now looking ahead. Medium shot. Clean manga-anime shading, thick clean outlines, readable anime features.' "
        "Bad example: 'The same anime girl, now watching the streetlights slide across the carriage glass. Wide shot. Clean manga-anime shading, thick clean outlines, readable anime features.' "
        "Use the TTI anchor as the source of truth and preserve the same character and same world. "
        "Do not add safety suffixes, negative tags, or typography bans. "
        "Do not use '+' anywhere in any field. "
        "Example prompt_text: 'The same anime girl, now fiercely smashing the guitar onto the ground, bending her knees. Extreme low-angle dynamic shot. Clean manga-anime shading, thick clean outlines, readable anime features.' "
        f"Shot manifest={summary}."
    )


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
