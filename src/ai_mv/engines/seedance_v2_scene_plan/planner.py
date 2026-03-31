from __future__ import annotations

import itertools
import zlib

from ai_mv.core.contracts.seedance_v2_normalize import normalize_scene_plan_v2
from ai_mv.core.director_brief import build_director_brief_intent
from ai_mv.infra.codex_cli_client import generate_structured, ping_codex


def build_scene_plan_v2(config: dict, payload: dict) -> dict:
    brief = build_director_brief_intent(config)
    timeline = payload["lyrics_timeline"]
    sections = [row for row in timeline.get("sections", []) if isinstance(row, dict)]
    translations = _translate_beat_render_phrases(config, sections)
    motifs = brief.get("motif_families", []) or ["world motif"]
    grammar = brief.get("section_grammar", {})
    shot_packages: list[dict] = []
    zone_progression: list[dict] = []
    motif_progression: list[dict] = []
    for section_index, section in enumerate(sections, start=1):
        section_name = str(section.get("section_name", "")).strip()
        section_label = str(section.get("section_label", section_name)).strip() or section_name or f"Section {section_index}"
        zone = _zone_for_section(section_label, section_index)
        story_role = grammar.get(section_label) or grammar.get(section_name) or _fallback_story_role(section_label)
        zone_progression.append({"section_name": section_name, "section_label": section_label, "zone": zone, "story_role": story_role})
        section_beats = [row for row in section.get("lyric_beats", []) if isinstance(row, dict)]
        section_beat_count = len(section_beats)
        motif_sequence = _motif_sequence_for_section(motifs, section_label, zone, section_beat_count)
        section_shots: list[dict] = []
        for beat_index, beat in enumerate(section_beats, start=1):
            if not isinstance(beat, dict):
                continue
            beat_id = str(beat.get("beat_id", "")).strip()
            if not beat_id:
                continue
            translated = translations.get(beat_id, {})
            motif = motif_sequence[(beat_index - 1) % len(motif_sequence)]
            continuity_group = f"{section_label}:{zone}"
            environment_anchor = _environment_anchor(zone, motif, beat, translated)
            visual_role = _visual_role(section_label, zone, beat_index, section_beat_count)
            section_shots.append(
                {
                    "shot_id": beat_id,
                    "section_name": section_name,
                    "section_label": section_label,
                    "beat_refs": [beat_id],
                    "line_refs": [int(x) for x in beat.get("line_refs", []) if int(x) > 0],
                    "story_role": story_role,
                    "visual_role": visual_role,
                    "zone": zone,
                    "motif_family": motif,
                    "continuity_group": continuity_group,
                    "identity_core": brief["identity_core"],
                    "environment_family": _environment_family(motif),
                    "camera_distance_band": _camera_distance_band(zone, section_label, visual_role),
                    "environment_anchor": environment_anchor,
                    "literal_image": _translated_phrase(beat, translated, "literal_image"),
                    "visible_action": _translated_phrase(beat, translated, "visible_action"),
                    "subject_action": _translated_phrase(beat, translated, "subject_action"),
                    "beat_continuity_anchor": _translated_phrase(beat, translated, "continuity_anchor"),
                    "payoff_role_hint": _translated_phrase(beat, translated, "payoff_role"),
                    "section_beat_index": beat_index,
                    "section_beat_count": section_beat_count,
                }
            )
            motif_progression.append(
                {
                    "shot_id": beat_id,
                    "section_label": section_label,
                    "motif_family": motif,
                    "environment_anchor": environment_anchor,
                }
            )
        _apply_transition_contracts(section_shots)
        shot_packages.extend(section_shots)
    _rewrite_location_descriptions(config, shot_packages)
    rewritten_locations = {
        str(row.get("shot_id", "")).strip(): str(row.get("environment_anchor", "")).strip()
        for row in shot_packages
        if str(row.get("shot_id", "")).strip()
    }
    for row in motif_progression:
        shot_id = str(row.get("shot_id", "")).strip()
        location = rewritten_locations.get(shot_id, "")
        if location:
            row["environment_anchor"] = location
    scene_plan = {
        "brief_name": brief["brief_name"],
        "identity_core": brief["identity_core"],
        "style_contract": brief["style_contract"],
        "world_core": brief["world_core"],
        "zone_progression": zone_progression,
        "motif_progression": motif_progression,
        "section_grammar": grammar,
        "shot_packages": shot_packages,
    }
    return normalize_scene_plan_v2(scene_plan)


def build_scene_plan_v2_preview_prompt(config: dict, payload: dict) -> str:
    brief = build_director_brief_intent(config)
    return (
        "Create a Seedance-style scene plan from the lyric timeline. "
        f"Identity core={brief['identity_core']}. "
        f"World core={brief['world_core']}. "
        f"Motif families={', '.join(brief.get('motif_families', []))}. "
        f"Section grammar={'; '.join(f'{k}:{v}' for k, v in brief.get('section_grammar', {}).items())}. "
        "Map each lyric beat into a zone progression and one concrete place that supports one heroine-centered visible action."
    )


def _zone_for_section(section_label: str, section_index: int) -> str:
    low = section_label.lower()
    if "intro" in low:
        return "threshold"
    if "pre" in low:
        return "edge"
    if "bridge" in low:
        return "compression"
    if "final chorus" in low:
        return "open_world_peak"
    if "chorus" in low:
        return "open_world"
    if "outro" in low:
        return "residue"
    return "narrow_world" if section_index <= 2 else "transit_lane"


def _fallback_story_role(section_label: str) -> str:
    low = section_label.lower()
    if "intro" in low:
        return "threshold setup and motif introduction"
    if "pre" in low:
        return "threshold and anticipation"
    if "final chorus" in low:
        return "motif system peak"
    if "chorus" in low:
        return "open world with wider motion"
    if "bridge" in low:
        return "compressed interruption and reframing"
    if "outro" in low:
        return "residual world after-image"
    return "object-led narrow world"


def _environment_anchor(zone: str, motif: str, beat: dict, translated: dict) -> str:
    zone_seed = _zone_seed_place(zone)
    literal = _translated_phrase(beat, translated, "literal_image")
    continuity = _translated_phrase(beat, translated, "continuity_anchor")
    detail = literal or continuity or _motif_space(motif.strip().lower() or "city detail")
    detail_clean = " ".join(str(detail).strip().rstrip(".").split())
    if not detail_clean:
        return zone_seed
    if detail_clean.lower() in zone_seed.lower():
        return zone_seed
    return f"{zone_seed} with {detail_clean}"


def _rewrite_location_descriptions(config: dict, shot_packages: list[dict]) -> None:
    if not shot_packages:
        return
    rows = [
        {
            "shot_id": str(shot.get("shot_id", "")).strip(),
            "zone": str(shot.get("zone", "")).strip(),
            "motif_family": str(shot.get("motif_family", "")).strip(),
            "base_location": str(shot.get("environment_anchor", "")).strip(),
            "literal_image": str(shot.get("literal_image", "")).strip(),
            "subject_action": str(shot.get("subject_action", "")).strip(),
            "beat_continuity_anchor": str(shot.get("beat_continuity_anchor", "")).strip(),
        }
        for shot in shot_packages
    ]
    try:
        if ping_codex(config):
            rewritten = _rewrite_locations_with_codex(config, rows)
            for shot in shot_packages:
                shot_id = str(shot.get("shot_id", "")).strip()
                location = " ".join(str(rewritten.get(shot_id, "")).strip().rstrip(".").split())
                if location:
                    shot["location_description"] = location
                    shot["environment_anchor"] = location
                    continue
                shot["location_description"] = str(shot.get("environment_anchor", "")).strip()
            return
    except Exception:
        pass
    for shot in shot_packages:
        shot["location_description"] = str(shot.get("environment_anchor", "")).strip()


def _rewrite_locations_with_codex(config: dict, rows: list[dict]) -> dict[str, str]:
    schema = {
        "type": "object",
        "properties": {
            "shots": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "shot_id": {"type": "string"},
                        "location_description": {"type": "string"},
                    },
                    "required": ["shot_id", "location_description"],
                },
            }
        },
        "required": ["shots"],
    }
    prompt = (
        "Rewrite each shot into one concrete English location sentence for image and video prompts. "
        "The output must read like a real place that can hold the heroine's action, not like a caption or production note. "
        "Keep it visual, physical, and specific. "
        "Do not mention frame, shot, prompt, continuity, video, composition, camera, or viewer. "
        "Do not use the word frame anywhere in the output, even for a physical object; use window edge, rail, border, or casing instead. "
        "Do not mention the heroine, body parts, breath, heartbeat, feelings, memories, relationships, or any action. "
        "Do not describe the place with person-like verbs such as stands, waits, watches, remembers, or reaches. "
        "Do not use poetic metaphor that weakens the place into abstract mood. "
        "Stay faithful to the base location, motif, literal image, and subject action, but express only the place, surfaces, structures, and local light. "
        "Prefer the nearest playable surface, path, or threshold around the heroine over a distant symbolic object. "
        "Do not choose a clock, sign, or distant skyline as the main place anchor unless the source clearly makes it the physical center of her visible action. "
        "Do not invent new props or move to a different world. "
        "Return only a concrete place description that can naturally support the described action.\n\n"
        f"Shots={rows}"
    )
    raw = generate_structured(config, prompt, schema, attempts=1)
    out: dict[str, str] = {}
    for row in raw.get("shots", []):
        if not isinstance(row, dict):
            continue
        shot_id = str(row.get("shot_id", "")).strip()
        location = " ".join(str(row.get("location_description", "")).strip().rstrip(".").split())
        if shot_id and location:
            out[shot_id] = location
    return out


def _zone_environment_phrase(zone: str, motif: str) -> str:
    motif_text = motif.strip().lower() or "city detail"
    zone_key = zone.strip().lower()
    motif_space = _motif_space(motif_text)
    phrases = {
        "threshold": f"a threshold crossing space around {motif_space}",
        "edge": f"an edge-of-decision space with {motif_space}",
        "compression": f"a compressed urban pocket around {motif_space}",
        "open_world": f"a street-level open city space with {motif_space}",
        "open_world_peak": f"the brightest open city release with {motif_space}",
        "residue": f"a lingering after-image space around {motif_space}",
        "narrow_world": f"a close urban pocket around {motif_space}",
        "transit_lane": f"a moving transit lane with {motif_space}",
    }
    return phrases.get(zone_key, f"a city space around {motif_space}")


def _zone_seed_place(zone: str) -> str:
    zone_key = zone.strip().lower()
    phrases = {
        "threshold": "a station entrance at night",
        "edge": "a station gate edge at night",
        "compression": "a narrow station-side passage at night",
        "open_world": "a street-level station frontage at night",
        "open_world_peak": "a bright station-side opening at night",
        "residue": "the last station-side space after the main movement has passed",
        "narrow_world": "a narrow station-side passage at night",
        "transit_lane": "a station-side lane that keeps the movement going",
    }
    return phrases.get(zone_key, "a readable city place at night")


def _beat_phrase(beat: dict, key: str) -> str:
    return " ".join(str(beat.get(key, "")).strip().rstrip(".").split()) if isinstance(beat, dict) else ""


def _translated_phrase(beat: dict, translated: dict, key: str) -> str:
    translated_value = " ".join(str(translated.get(f"{key}_en", "")).strip().rstrip(".").split())
    if translated_value:
        return translated_value
    return _beat_phrase(beat, key)


def _translate_beat_render_phrases(config: dict, sections: list[dict]) -> dict[str, dict]:
    beats: list[dict] = []
    for section in sections:
        if not isinstance(section, dict):
            continue
        for beat in section.get("lyric_beats", []):
            if not isinstance(beat, dict):
                continue
            beat_id = str(beat.get("beat_id", "")).strip()
            if not beat_id:
                continue
            beats.append(
                {
                    "beat_id": beat_id,
                    "literal_image": _beat_phrase(beat, "literal_image"),
                    "visible_action": _beat_phrase(beat, "visible_action"),
                    "continuity_anchor": _beat_phrase(beat, "continuity_anchor"),
                    "payoff_role": _beat_phrase(beat, "payoff_role"),
                }
            )
    if not beats:
        return {}
    try:
        if not ping_codex(config):
            return {}
    except Exception:
        return {}
    translated = _request_translated_beat_render_phrases(config, beats)
    missing_ids = [
        str(row.get("beat_id", "")).strip()
        for row in beats
        if str(row.get("beat_id", "")).strip() and str(row.get("beat_id", "")).strip() not in translated
    ]
    if missing_ids:
        retry_beats = [row for row in beats if str(row.get("beat_id", "")).strip() in set(missing_ids)]
        translated.update(_request_translated_beat_render_phrases(config, retry_beats))
    return translated


def _request_translated_beat_render_phrases(config: dict, beats: list[dict]) -> dict[str, dict]:
    if not beats:
        return {}
    schema = {
        "type": "object",
        "properties": {
            "beats": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "beat_id": {"type": "string"},
                        "literal_image_en": {"type": "string"},
                        "visible_action_en": {"type": "string"},
                        "subject_action_en": {"type": "string"},
                        "continuity_anchor_en": {"type": "string"},
                        "payoff_role_en": {"type": "string"},
                    },
                    "required": ["beat_id", "literal_image_en", "visible_action_en", "subject_action_en", "continuity_anchor_en", "payoff_role_en"],
                },
            }
        },
        "required": ["beats"],
    }
    prompt = (
        "Rewrite the following music-video beat fields into short natural English render prose for image and video prompting. "
        "Always rewrite them, even if the source is already in English, so that the result fits cinematic live-action prompt writing. "
        "Stay faithful to the original meaning. Do not add new locations, props, characters, or symbolic story ideas. "
        "Default to a single-heroine scene. If the source does not explicitly include another person, do not introduce one. "
        "This pipeline is single-subject by default. Even if a lyric implies someone remembered, addressed, awaited, or loved, keep the frame centered on one visible heroine unless the source unmistakably requires two visible bodies in one shot. "
        "For this project, assume the intended visual language is a single visible heroine moving through one connected world, not a duet, reunion, hug, or partner scene. "
        "Treat second-person address, implied romance, remembered closeness, or emotional togetherness as non-visible unless the source clearly describes another body physically present in the frame. "
        "Never introduce viewer-facing second-person language such as you or your. "
        "Do not introduce he, him, they, them, or another figure unless the source explicitly names or clearly requires another person. "
        "If the source only implies emotional closeness or shared feeling without literally showing another visible person, keep it single-subject and express that feeling through the heroine's movement in the space. "
        "A lyric addressee or emotional partner is not automatically a visible second character. "
        "Do not use figure, person, silhouette, embrace, arms, together, them, or their unless the source unmistakably requires two visible bodies in one frame. "
        "Write direct visual prose, not production notes and not poetic paraphrase. "
        "Prefer one clear place anchor over a stack of station symbols. "
        "If one doorway, gate, sign, window, rail, or reflection can carry the place, do not pile on several more environment nouns. "
        "Do not turn the beat into a location hero shot; the place should support one heroine-centered visible action. "
        "When choosing the place anchor, prefer the nearest playable surface or path around the heroine, such as a window, rail, gate edge, stair, passage, or wet platform, over a distant symbolic object. "
        "Do not pick a clock, sign, or distant city marker as the main place anchor unless the source literally centers the heroine's visible action on that object. "
        "For opening or payoff beats, prefer the doorway, threshold, gate rail, exit line, or immediate platform path she can physically cross right now over a distant bright point farther ahead. "
        "Every returned field must be natural English prose. Never leave Korean text, mixed-language text, or untranslated fragments in the output. "
        "Do not use the word frame anywhere in the output, even for a physical object; use window edge, rail, border, or casing instead. "
        "literal_image_en should be a concise concrete scene phrase built from one place anchor plus only the surfaces, structures, weather, or local light needed to make that place believable. "
        "Keep literal_image_en compact enough that the heroine can still dominate the image. "
        "literal_image_en must not mention body parts, breath, heartbeat, emotions, memories, hesitation, loneliness, relationships, or camera language. "
        "If the original beat uses an inner feeling, memory, hesitation, heartbeat, loneliness, or fear to describe the scene, convert that into a visible environmental trace in the same place instead of naming the feeling. "
        "visible_action_en should be a concise screen-readable present-tense action fragment that describes what is visibly happening in the scene. "
        "visible_action_en should prefer body-grounded motion or contact over abstract mood. "
        "Prefer actions that read clearly in torso, legs, hands, direction, or contact at a glance. "
        "subject_action_en should rewrite visible_action into a heroine-centered present-tense action fragment suitable for prompts that begin with 'She ...'. "
        "subject_action_en should prefer clear physical actions that read in a keyframe, such as walking, turning, leaning, touching, stepping, passing, pausing at a surface, lifting a hand, descending, or changing direction. "
        "subject_action_en should avoid body-part fixation, decorative metaphor, relationship language, viewer-facing language, and vague emotion-only verbs. "
        "Choose actions that keep the heroine readable and present rather than actions that naturally push her tiny into the distance. "
        "If the beat supports it, prefer actions with one readable contact detail such as a hand on glass, a hand along a rail, or a step through an opening, because those tend to hold the heroine and place together more clearly. "
        "Avoid phrasing that leaves her frozen in place, such as 'stays', 'remains', or 'holds still', unless the original beat explicitly requires stillness as the main visible event. "
        "Avoid weak keyframe verbs such as watches, looks, gazes, waits, breathes, exhales, smiles softly, or lets the scene happen around her when a clearer visible action is possible. "
        "Also avoid static verbs such as studies, admires, lets a reflection settle, holds a smile, lets a smile rise, lets the motion settle, or lets the floor steady when a more readable visible action can carry the beat. "
        "Do not use heartbeat, hesitation, memory, loneliness, or pause as the main visible event unless there is no other faithful physical reading. "
        "If the source suggests a static feeling, convert it into a small but visible physical action in the same place. "
        "If the source says she stands still, pauses, waits, only breathes, or only watches something, rewrite it into a subtle but readable movement such as shifting her weight, taking a step, turning, touching a surface, tracing a rail or glass edge, crossing a threshold, or lifting a hand while staying in the same space. "
        "If breath, hesitation, heartbeat, or memory is important, show it through her hand, shoulders, step, or contact with a nearby surface instead of naming that internal state directly. "
        "If fog, condensation, or cold air matters, prefer the effect on glass, metal, fabric, or light rather than stating breath directly. "
        "If the source offers both a distant symbolic target and a nearby surface or path, prefer the nearby surface or path for visible_action_en and subject_action_en. "
        "For opening or release beats, prefer crossing actions such as stepping through, clearing the gate, passing the rail, crossing the exit line, or moving into the doorway over merely approaching a bright place from afar. "
        "For final opening or release beats, do not make smiling, reflection, reflections brightening behind her, a glowing window, a glass storefront reflection, warm light ahead, pale dawn light, light gathering in front of her, a bright sign, a clearing path, a lane of light ahead, lifted face toward light, settling/steadying motion, a folded ticket, fading light in her hand, or lingering light after the last train the main event when a forward crossing action in the same place can carry the beat. "
        "In final opening or release beats, prefer gate, threshold, exit, street entry, platform edge crossing, stair-top crossing, crosswalk crossing, or doorway crossing over lingering by a window, holding at the edge, moving toward a vague glow, leaving a reflection behind, opening her fingers toward space, using a small hand gesture as the main event, or dwelling on the last train aftermath. "
        "If the source implies reunion, recognition, holding hands, embrace, or togetherness but does not clearly show another visible body, convert that into a single-heroine action such as opening her hand, stepping into light, turning into the space, meeting her own reflection, or moving toward a clearer direction in the same place. "
        "If the source implies a person ahead, behind, beside, or turning away without a clearly visible second body, rewrite it as a trace in the space, a direction of movement, or a changed patch of light in the same place. "
        "Never output another woman, another man, the other woman, the other person, two women, two people, embrace, hug, clasp hands, or holding hands unless the source literally requires two visible bodies in the frame. "
        "If the beat lands on a smile or soft release, show it through crossing a threshold, clearing a gate, reaching the far side of a street or platform edge, or stepping through a doorway rather than describing the smile as a held pose. "
        "Do not use generic release phrases such as one steady rhythm, calm steady pace, open space, brighter direction, or path clearing when a specific crossing action is available in the same place. "
        "If the original mentions camera, frame, shot, cut, filming, shake, zoom, or viewpoint, rewrite only the visible on-screen event and never mention filming language in English. "
        "For example, camera shake should become a visible movement in the space, the heroine, the light, or nearby surfaces, not camera wording. "
        "If the original is metaphorical, convert it into the nearest believable visual event in the same place. "
        "Avoid abstract environment phrases such as pocket, glow-map, quiet light, trembling glass light, brighter edge of town, last strip of night, platform glow spreading, or end of the night when a more literal place and light description can carry the same beat. "
        "When choosing between an inner-state word and a small physical action, always choose the physical action. "
        "continuity_anchor_en should be a short visual state phrase for continuity checking. "
        "payoff_role_en should be a short payoff-role phrase. "
        "Return JSON only.\n\n"
        f"Beats={beats}"
    )
    try:
        raw = generate_structured(config, prompt, schema, attempts=1)
    except Exception:
        return {}
    out: dict[str, dict] = {}
    for row in raw.get("beats", []):
        if not isinstance(row, dict):
            continue
        beat_id = str(row.get("beat_id", "")).strip()
        if not beat_id:
            continue
        cleaned = _clean_translated_beat_row(row)
        if cleaned:
            out[beat_id] = cleaned
    return out


def _clean_translated_beat_row(row: dict) -> dict | None:
    cleaned = dict(row)
    required = ("literal_image_en", "visible_action_en", "subject_action_en", "continuity_anchor_en", "payoff_role_en")
    for key in required:
        value = " ".join(str(cleaned.get(key, "")).strip().rstrip(".").split())
        if not value or _contains_render_meta(value) or not _looks_english(value):
            return None
        cleaned[key] = value
    beat_id = str(cleaned.get("beat_id", "")).strip()
    if not beat_id:
        return None
    cleaned["beat_id"] = beat_id
    return cleaned


def _needs_translation(row: dict) -> bool:
    for key in ("literal_image", "visible_action", "continuity_anchor", "payoff_role"):
        text = str(row.get(key, "")).strip()
        if text and (not _looks_english(text) or _contains_render_meta(text)):
            return True
    return False


def _looks_english(text: str) -> bool:
    letters = [ch for ch in str(text) if ch.isalpha()]
    if not letters:
        return False
    ascii_letters = [ch for ch in letters if ("a" <= ch.lower() <= "z")]
    return (len(ascii_letters) / len(letters)) >= 0.8


def _contains_render_meta(text: str) -> bool:
    cleaned = " ".join(str(text).strip().lower().split())
    if not cleaned:
        return False
    forbidden = (
        "camera",
        "frame",
        "shot",
        "cut",
        "filming",
        "video",
        "viewer",
        "close-up",
        "wide shot",
        "medium shot",
    )
    return any(token in cleaned for token in forbidden)


def _motif_space(motif_text: str) -> str:
    if "train window" in motif_text:
        return "train-side glass, interior reflections, and passing exterior light"
    if "ticket gate" in motif_text:
        return "ticket gate lanes, card readers, and station barriers"
    if "curb reflection" in motif_text:
        return "a wet curb edge with reflective asphalt and passing street light"
    if "puddle" in motif_text:
        return "wet pavement, shallow puddle reflections, and a curb-adjacent street surface"
    if "platform sign glow" in motif_text:
        return "platform signage, overhead lamps, and glowing station markers"
    if "stair landing" in motif_text:
        return "a stair landing, railings, and receding steps"
    return motif_text


def _environment_family(motif_text: str) -> str:
    motif = motif_text.strip().lower()
    if "train window" in motif:
        return "train_window_glass"
    if "ticket gate" in motif:
        return "ticket_gate_lane"
    if "curb reflection" in motif:
        return "wet_curb_reflection"
    if "puddle" in motif:
        return "wet_pavement_reflection"
    if "platform sign glow" in motif:
        return "platform_signage"
    if "stair landing" in motif:
        return "stair_landing"
    return "urban_detail"


def _camera_distance_band(zone: str, section_label: str, visual_role: str) -> str:
    zone_key = zone.strip().lower()
    section = section_label.strip().lower()
    role = visual_role.strip().lower()
    if "bridge" in section or zone_key == "compression":
        return "tight_medium"
    if role == "payoff_frame" and "final chorus" in section:
        return "wide_full_figure"
    if "chorus" in section:
        return "medium_wide"
    if zone_key in {"threshold", "edge"}:
        return "medium"
    return "medium"


def _visual_role(section_label: str, zone: str, beat_index: int, beat_count: int) -> str:
    section = section_label.strip().lower()
    zone_key = zone.strip().lower()
    if "intro" in section or beat_index == 1:
        return "opening_frame"
    if "final chorus" in section or zone_key == "open_world_peak":
        return _final_chorus_visual_role(beat_index, beat_count)
    if "bridge" in section or zone_key == "compression":
        return "pressure_frame"
    if beat_index >= beat_count:
        return "handoff_frame"
    return "continuity_frame"


def _final_chorus_visual_role(beat_index: int, beat_count: int) -> str:
    if beat_count <= 1:
        return "opening_frame"
    if beat_index == 1:
        return "opening_frame"
    if beat_index == beat_count:
        return "payoff_frame"
    if beat_count >= 4 and beat_index == beat_count - 1:
        return "handoff_frame"
    return "continuity_frame"


def _motif_sequence_for_section(motifs: list[str], section_label: str, zone: str, beat_count: int) -> list[str]:
    motif_rows = [str(m).strip() for m in motifs if str(m).strip()]
    if not motif_rows:
        return ["world motif"]
    if len(motif_rows) == 1:
        return motif_rows
    offset = zlib.crc32(section_label.encode("utf-8")) % len(motif_rows)
    rotated = motif_rows[offset:] + motif_rows[:offset]
    target_length = max(1, min(int(beat_count or 1), len(rotated)))
    if target_length < len(rotated):
        return _lowest_cost_path(rotated, motif_rows, zone, target_length)
    if len(rotated) <= 8:
        return _lowest_cost_cycle(rotated, motif_rows, zone)
    return _greedy_low_cost_cycle(rotated, motif_rows, zone)


def _lowest_cost_path(rotated: list[str], profile_order: list[str], zone: str, target_length: int) -> list[str]:
    start = rotated[0]
    remaining = rotated[1:]
    best_sequence = [start, *remaining[: max(0, target_length - 1)]]
    best_score: tuple[float, float] | None = None
    for perm in itertools.permutations(remaining, max(0, target_length - 1)):
        candidate = [start, *perm]
        score = (
            _path_transition_cost(candidate) + _zone_sequence_penalty(candidate, zone),
            _order_penalty(candidate, profile_order, cyclic=False),
        )
        if best_score is None or score < best_score:
            best_score = score
            best_sequence = candidate
    return best_sequence


def _lowest_cost_cycle(rotated: list[str], profile_order: list[str], zone: str) -> list[str]:
    start = rotated[0]
    remaining = rotated[1:]
    best_sequence = rotated[:]
    best_score: tuple[float, float] | None = None
    for perm in itertools.permutations(remaining):
        candidate = [start, *perm]
        score = (
            _cycle_transition_cost(candidate) + _zone_sequence_penalty(candidate, zone),
            _order_penalty(candidate, profile_order, cyclic=True),
        )
        if best_score is None or score < best_score:
            best_score = score
            best_sequence = candidate
    return best_sequence


def _greedy_low_cost_cycle(rotated: list[str], profile_order: list[str], zone: str) -> list[str]:
    sequence = [rotated[0]]
    remaining = rotated[1:]
    while remaining:
        current = sequence[-1]
        next_motif = min(
            remaining,
            key=lambda motif: (
                _transition_cost_between_families(_environment_family(current), _environment_family(motif))
                + _zone_family_penalty(zone, _environment_family(motif)),
                _profile_gap(profile_order, current, motif),
                motif,
            ),
        )
        sequence.append(next_motif)
        remaining.remove(next_motif)
    return sequence


def _cycle_transition_cost(sequence: list[str]) -> float:
    families = [_environment_family(motif) for motif in sequence]
    total = 0.0
    for index, family in enumerate(families):
        next_family = families[(index + 1) % len(families)]
        total += _transition_cost_between_families(family, next_family)
    return total


def _path_transition_cost(sequence: list[str]) -> float:
    families = [_environment_family(motif) for motif in sequence]
    total = 0.0
    for index in range(len(families) - 1):
        total += _transition_cost_between_families(families[index], families[index + 1])
    return total


def _order_penalty(sequence: list[str], profile_order: list[str], cyclic: bool) -> float:
    total = 0.0
    limit = len(sequence) if cyclic else len(sequence) - 1
    for index in range(limit):
        motif = sequence[index]
        next_motif = sequence[(index + 1) % len(sequence)]
        total += _profile_gap(profile_order, motif, next_motif)
    return total


def _profile_gap(profile_order: list[str], left: str, right: str) -> float:
    if left not in profile_order or right not in profile_order:
        return float(len(profile_order))
    left_index = profile_order.index(left)
    right_index = profile_order.index(right)
    forward_gap = (right_index - left_index) % len(profile_order)
    backward_gap = (left_index - right_index) % len(profile_order)
    return float(min(forward_gap, backward_gap))


def _transition_cost_between_families(left_family: str, right_family: str) -> float:
    if left_family == right_family:
        return 0.0
    left = _environment_traits(left_family)
    right = _environment_traits(right_family)
    cost = 0.0
    if left["space_type"] != right["space_type"]:
        cost += _space_transition_penalty(left["space_type"], right["space_type"])
    if left["axis_type"] != right["axis_type"]:
        cost += 1.0
    if left["contact_plane"] != right["contact_plane"]:
        cost += 0.75
    if left["transition_group"] != right["transition_group"]:
        cost += 0.5
    return cost


def _zone_sequence_penalty(sequence: list[str], zone: str) -> float:
    total = 0.0
    for motif in sequence:
        total += _zone_family_penalty(zone, _environment_family(motif))
    return total


def _zone_family_penalty(zone: str, family: str) -> float:
    zone_key = str(zone).strip().lower()
    traits = _environment_traits(family)
    space = traits["space_type"]
    group = traits["transition_group"]
    penalties = {
        "threshold": {
            "threshold": 0.0,
            "open_exterior": 1.0,
            "vertical_path": 1.0,
            "contained_interior": 1.5,
        },
        "edge": {
            "threshold": 0.0,
            "open_exterior": 0.5,
            "vertical_path": 1.25,
            "contained_interior": 1.75,
        },
        "narrow_world": {
            "threshold": 0.25,
            "open_exterior": 0.75,
            "vertical_path": 0.5,
            "contained_interior": 2.25,
        },
        "transit_lane": {
            "threshold": 0.0,
            "open_exterior": 0.5,
            "vertical_path": 0.75,
            "contained_interior": 1.75,
        },
        "open_world": {
            "open_exterior": 0.0,
            "threshold": 0.75,
            "vertical_path": 1.0,
            "contained_interior": 3.5,
        },
        "open_world_peak": {
            "open_exterior": 0.0,
            "threshold": 0.75,
            "vertical_path": 1.0,
            "contained_interior": 4.0,
        },
        "compression": {
            "contained_interior": 0.25,
            "threshold": 0.75,
            "vertical_path": 0.75,
            "open_exterior": 1.5,
        },
        "residue": {
            "open_exterior": 0.25,
            "threshold": 0.5,
            "vertical_path": 0.75,
            "contained_interior": 1.5,
        },
    }
    zone_penalty = penalties.get(zone_key, {})
    value = float(zone_penalty.get(space, 1.0))
    if zone_key in {"open_world", "open_world_peak"} and group == "transit_enclosure":
        value += 1.5
    return value


def _space_transition_penalty(left_space: str, right_space: str) -> float:
    pair = {left_space, right_space}
    if pair == {"open_exterior", "contained_interior"}:
        return 4.0
    if pair == {"open_exterior", "threshold"}:
        return 1.5
    if pair == {"contained_interior", "threshold"}:
        return 1.5
    if pair == {"vertical_path", "contained_interior"}:
        return 2.5
    if pair == {"vertical_path", "open_exterior"}:
        return 2.0
    if pair == {"vertical_path", "threshold"}:
        return 2.0
    return 2.0


def _environment_traits(family: str) -> dict[str, str]:
    traits = {
        "train_window_glass": {
            "space_type": "contained_interior",
            "axis_type": "side_glass",
            "contact_plane": "glass_line",
            "transition_group": "transit_enclosure",
        },
        "ticket_gate_lane": {
            "space_type": "threshold",
            "axis_type": "lane_forward",
            "contact_plane": "barrier_lane",
            "transition_group": "station_threshold",
        },
        "wet_curb_reflection": {
            "space_type": "open_exterior",
            "axis_type": "street_plane",
            "contact_plane": "ground_reflection",
            "transition_group": "street_reflection",
        },
        "wet_pavement_reflection": {
            "space_type": "open_exterior",
            "axis_type": "street_plane",
            "contact_plane": "ground_reflection",
            "transition_group": "street_reflection",
        },
        "platform_signage": {
            "space_type": "threshold",
            "axis_type": "station_depth",
            "contact_plane": "platform_plane",
            "transition_group": "station_threshold",
        },
        "stair_landing": {
            "space_type": "vertical_path",
            "axis_type": "stair_depth",
            "contact_plane": "step_depth",
            "transition_group": "vertical_transit",
        },
        "urban_detail": {
            "space_type": "threshold",
            "axis_type": "street_plane",
            "contact_plane": "ground_plane",
            "transition_group": "generic_urban",
        },
    }
    return dict(traits.get(family, traits["urban_detail"]))


def _apply_transition_contracts(section_shots: list[dict]) -> None:
    if len(section_shots) < 2:
        return
    for index in range(len(section_shots) - 1):
        current = section_shots[index]
        following = section_shots[index + 1]
        cost = _transition_cost_between_families(
            str(current.get("environment_family", "")).strip().lower(),
            str(following.get("environment_family", "")).strip().lower(),
        )
        if cost < 4.0:
            continue
        role = str(current.get("visual_role", "")).strip().lower()
        if role in {"opening_frame", "payoff_frame", "pressure_frame"}:
            continue
        current["visual_role"] = "handoff_frame"
        current["camera_distance_band"] = _camera_distance_band(
            str(current.get("zone", "")).strip(),
            str(current.get("section_label", "")).strip(),
            "handoff_frame",
        )
