from __future__ import annotations

import itertools
import zlib

from ai_mv.core.contracts.visual_plan_normalize import normalize_scene_plan
from ai_mv.core.director_brief import build_director_brief_intent
from ai_mv.infra.codex_cli_client import generate_structured, ping_codex


def build_scene_plan(config: dict, payload: dict) -> dict:
    brief = build_director_brief_intent(config)
    timeline = payload["lyrics_timeline"]
    sections = [row for row in timeline.get("sections", []) if isinstance(row, dict)]
    motifs = brief.get("motif_families", []) or ["world motif"]
    grammar = brief.get("section_grammar", {})
    translations = _translate_beat_render_phrases(config, sections, grammar)
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
                    "dominant_scene_grammar": _translated_phrase(beat, translated, "dominant_scene_grammar"),
                    "primary_surface": _translated_phrase(beat, translated, "primary_surface"),
                    "support_detail": _translated_phrase(beat, translated, "support_detail"),
                    "beat_continuity_anchor": _translated_phrase(beat, translated, "continuity_anchor"),
                    "payoff_role_hint": _translated_phrase(beat, translated, "payoff_role"),
                    "section_beat_index": beat_index,
                    "section_beat_count": section_beat_count,
                }
            )
            _finalize_scene_shot(section_shots[-1])
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
    return normalize_scene_plan(scene_plan)


def build_scene_plan_preview_prompt(config: dict, payload: dict) -> str:
    brief = build_director_brief_intent(config)
    return (
        "Create a cinematic music video scene plan from the lyric timeline. "
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
    primary_surface = _translated_phrase(beat, translated, "primary_surface")
    support_detail = _translated_phrase(beat, translated, "support_detail")
    literal = _translated_phrase(beat, translated, "literal_image")
    continuity = _translated_phrase(beat, translated, "continuity_anchor")
    if primary_surface:
        return _anchor_from_surface(zone_seed, primary_surface, support_detail)
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
            "visual_role": str(shot.get("visual_role", "")).strip(),
            "base_location": _location_rewrite_base(shot),
            "dominant_scene_grammar": str(shot.get("dominant_scene_grammar", "")).strip(),
            "primary_surface": str(shot.get("primary_surface", "")).strip(),
            "support_detail": _lean_support_detail(
                str(shot.get("primary_surface", "")).strip(),
                str(shot.get("support_detail", "")).strip(),
            ),
            "literal_image": _lean_literal_image(
                str(shot.get("primary_surface", "")).strip(),
                str(shot.get("support_detail", "")).strip(),
                str(shot.get("literal_image", "")).strip(),
            ),
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
                    _finalize_scene_shot(shot)
                    continue
                shot["location_description"] = str(shot.get("environment_anchor", "")).strip()
                _finalize_scene_shot(shot)
            return
    except Exception:
        pass
    for shot in shot_packages:
        shot["location_description"] = str(shot.get("environment_anchor", "")).strip()
        _finalize_scene_shot(shot)


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
        "Rewrite each shot into one concrete English location phrase for image and video prompts. "
        "The output must be a short noun phrase naming a real place that can hold the heroine's action, not a full sentence, caption, or production note. "
        "Keep it visual, physical, and specific. "
        "Do not write finite verbs such as is, are, runs, opens, cuts, marks, turns, sits, holds, or waits. "
        "Prefer concise location phrases built with along, at, by, under, beside, behind, across, or near. "
        "Do not mention frame, shot, prompt, continuity, video, composition, camera, or viewer. "
        "Do not use the word frame anywhere in the output, even for a physical object; use window edge, rail, border, or casing instead. "
        "Do not mention the heroine, body parts, breath, heartbeat, feelings, memories, relationships, or any action. "
        "Do not describe the place with person-like verbs such as stands, waits, watches, remembers, or reaches. "
        "Do not use poetic metaphor that weakens the place into abstract mood. "
        "Stay faithful to the base location, primary_surface, support_detail, literal image, and subject action, but express only the place, surfaces, structures, and local light. "
        "If primary_surface is present, use it as the main place anchor unless the source plainly makes another nearby playable surface more central. "
        "Keep support_detail secondary to the primary_surface. "
        "If base_location and literal_image are already lean, do not restore decorative nearby objects that were removed from support_detail. "
        "If support_detail is empty, do not invent a replacement light cue, sign, window, display, clock, or atmospheric texture just to make the sentence feel richer. "
        "If support_detail is empty, keep the location on the primary_surface and the nearest structural surface only. "
        "Do not add morning light, thin light, warm light, storefront light, board glow, station glow, window glow, or widened air unless that exact physical light is already necessary to identify the playable surface. "
        "Do not add lit windows, train windows, carriage windows, or window light to the location phrase unless primary_surface itself is a window edge and the heroine is physically using that edge. "
        "If primary_surface is stair, stairwell, handrail, platform edge, threshold, gate line, turnstile lane, curb, crosswalk, sidewalk, street edge, or passage, do not let glass, signage, a ticket, a clock, or a light effect become the head noun of the place. "
        "If primary_surface is window edge or glass edge, keep the place on the edge or path beside it, not on reflection, signage, or vague neon mood. "
        "Prefer the nearest playable surface, path, or threshold around the heroine over a distant symbolic object. "
        "Do not choose a clock, sign, or distant skyline as the main place anchor unless the source clearly makes it the physical center of her visible action. "
        "If zone is open_world_peak or the shot is a release/payoff beat, prefer exit line, turnstile lane, gate rail, stair top, curb crossing, street edge, or platform edge over train window reflection, station clock, signboard, skyline, vague glow, or dawn color. "
        "If zone is open_world_peak or the shot is a release/payoff beat, keep dawn, morning, brighter air, or wider light only as supporting local light, not as the place anchor. "
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


def _anchor_from_surface(zone_seed: str, primary_surface: str, support_detail: str) -> str:
    surface = " ".join(str(primary_surface).strip().rstrip(".").split())
    if not surface:
        return zone_seed
    support = " ".join(str(support_detail).strip().rstrip(".").split())
    base = _surface_location_phrase(zone_seed, surface)
    if not support or not _support_detail_is_material(support, surface):
        return base
    return f"{base}, with {support}"


def _location_rewrite_base(shot: dict) -> str:
    zone_seed = _zone_seed_place(str(shot.get("zone", "")).strip())
    primary_surface = str(shot.get("primary_surface", "")).strip()
    support_detail = str(shot.get("support_detail", "")).strip()
    if primary_surface:
        return _anchor_from_surface(zone_seed, primary_surface, support_detail)
    return str(shot.get("environment_anchor", "")).strip()


def _finalize_scene_shot(shot: dict) -> None:
    primary_surface = _normalize_primary_surface(
        str(shot.get("primary_surface", "")).strip(),
        str(shot.get("subject_action", "")).strip(),
        str(shot.get("literal_image", "")).strip(),
    )
    support_detail = _lean_support_detail(primary_surface, str(shot.get("support_detail", "")).strip())
    shot["primary_surface"] = primary_surface
    shot["support_detail"] = support_detail
    shot["literal_image"] = _lean_literal_image(
        primary_surface,
        support_detail,
        str(shot.get("literal_image", "")).strip(),
    )
    zone_seed = _zone_seed_place(str(shot.get("zone", "")).strip())
    lean_anchor = _anchor_from_surface(zone_seed, primary_surface, support_detail) if primary_surface else ""
    location = " ".join(str(shot.get("location_description", "")).strip().rstrip(".").split())
    environment_anchor = " ".join(str(shot.get("environment_anchor", "")).strip().rstrip(".").split())
    if _location_anchor_is_decorative(location):
        location = lean_anchor or location
    if _location_anchor_is_decorative(environment_anchor):
        environment_anchor = lean_anchor or environment_anchor
    if location:
        shot["location_description"] = location
    if environment_anchor:
        shot["environment_anchor"] = environment_anchor


def _location_anchor_is_decorative(text: str) -> bool:
    lowered = " ".join(str(text).strip().lower().split())
    if not lowered:
        return False
    decorative_tokens = (
        "lit windows",
        "window line",
        "train lights",
        "train window",
        "glass window",
        "glass door",
        "speaker",
        "signal light",
        "vending machine light",
        "wet neon",
        "dimming window",
        "wind",
        "boundary line",
        "across the track",
    )
    return any(token in lowered for token in decorative_tokens)


def _surface_location_phrase(zone_seed: str, surface: str) -> str:
    lowered = surface.lower()
    if any(token in lowered for token in ("threshold", "door edge", "doorway", "gate line", "gate rail", "gate lane", "exit line", "turnstile lane")):
        return f"{zone_seed} at the {surface}"
    if any(token in lowered for token in ("platform edge", "crosswalk", "curb", "street edge", "sidewalk", "pavement", "path", "passage", "corridor", "stair", "stairwell", "ramp", "landing")):
        return f"{zone_seed} along the {surface}"
    if any(token in lowered for token in ("window", "glass", "rail")):
        return f"{zone_seed} by the {surface}"
    return f"{zone_seed} around the {surface}"


def _support_detail_is_symbolic(detail: str) -> bool:
    lowered = detail.lower()
    symbolic_tokens = (
        "clock",
        "sign",
        "reflection",
        "reflections",
        "glow",
        "dawn",
        "window light",
        "thin light",
        "lingering light",
        "soft light",
        "bright light",
        "station light",
        "train lights",
        "departing train lights",
        "window line",
        "lit window line",
        "dimming window line",
        "wet neon",
        "neon",
        "ticket",
        "flyers",
        "hair tie",
    )
    return any(token in lowered for token in symbolic_tokens)


def _support_detail_is_material(detail: str, primary_surface: str = "") -> bool:
    lowered = detail.lower()
    surface = primary_surface.lower()
    if not lowered:
        return False
    if _support_detail_is_symbolic(lowered):
        return False
    material_tokens = (
        "rain",
        "drizzle",
        "puddle",
        "wet",
        "footprint",
        "footprints",
        "footprint trail",
        "wet footprints",
        "ground trail",
        "trail on the ground",
        "mist",
        "fogged",
        "fog",
        "condensation",
        "rail",
        "handrail",
        "railing",
        "handle",
        "door movement",
        "door swing",
        "hinge",
        "threshold strip",
        "yellow line",
        "water on the ground",
        "passing traffic",
        "traffic blur",
        "door edge",
        "window edge",
    )
    if any(token in lowered for token in material_tokens):
        return True
    if any(token in surface for token in ("window", "glass", "car window")) and any(
        token in lowered for token in ("fog", "fogged", "condensation", "mist")
    ):
        return True
    return False


def _lean_support_detail(primary_surface: str, support_detail: str) -> str:
    detail = " ".join(str(support_detail).strip().rstrip(".").split())
    surface = " ".join(str(primary_surface).strip().rstrip(".").split())
    if not detail or not surface:
        return ""
    if not _support_detail_is_material(detail, surface):
        return ""
    return detail


def _lean_literal_image(primary_surface: str, support_detail: str, literal_image: str) -> str:
    surface = " ".join(str(primary_surface).strip().rstrip(".").split())
    detail = _lean_support_detail(surface, support_detail)
    if surface:
        if detail:
            return f"{surface} with {detail}"
        return surface
    literal = " ".join(str(literal_image).strip().rstrip(".").split())
    return literal


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
        "threshold": "a station entrance",
        "edge": "a station gate edge",
        "compression": "a narrow station-side passage",
        "open_world": "a street-level station frontage",
        "open_world_peak": "a station-side exit line",
        "residue": "the last station-side space after the main movement has passed",
        "narrow_world": "a narrow station-side passage",
        "transit_lane": "a station-side lane",
    }
    return phrases.get(zone_key, "a readable city place at night")


def _beat_phrase(beat: dict, key: str) -> str:
    return " ".join(str(beat.get(key, "")).strip().rstrip(".").split()) if isinstance(beat, dict) else ""


def _translated_phrase(beat: dict, translated: dict, key: str) -> str:
    translated_value = " ".join(str(translated.get(f"{key}_en", "")).strip().rstrip(".").split())
    if translated_value:
        return translated_value
    return _beat_phrase(beat, key)


def _translate_beat_render_phrases(config: dict, sections: list[dict], grammar: dict[str, str] | None = None) -> dict[str, dict]:
    beats: list[dict] = []
    grammar_map = grammar or {}
    for section in sections:
        if not isinstance(section, dict):
            continue
        section_name = str(section.get("section_name", "")).strip()
        section_label = str(section.get("section_label", section_name)).strip() or section_name
        story_role = str(grammar_map.get(section_label) or grammar_map.get(section_name) or _fallback_story_role(section_label)).strip()
        section_beats = [row for row in section.get("lyric_beats", []) if isinstance(row, dict)]
        beat_count = len(section_beats)
        for beat_index, beat in enumerate(section_beats, start=1):
            if not isinstance(beat, dict):
                continue
            beat_id = str(beat.get("beat_id", "")).strip()
            if not beat_id:
                continue
            beats.append(
                {
                    "beat_id": beat_id,
                    "section_label": section_label,
                    "story_role": story_role,
                    "visual_role": _visual_role(section_label, _zone_for_section(section_label, 1), beat_index, beat_count),
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
                        "dominant_scene_grammar_en": {"type": "string"},
                        "primary_surface_en": {"type": "string"},
                        "support_detail_en": {"type": "string"},
                        "continuity_anchor_en": {"type": "string"},
                        "payoff_role_en": {"type": "string"},
                    },
                    "required": ["beat_id", "literal_image_en", "visible_action_en", "subject_action_en", "dominant_scene_grammar_en", "primary_surface_en", "support_detail_en", "continuity_anchor_en", "payoff_role_en"],
                },
            }
        },
        "required": ["beats"],
    }
    prompt = (
        "Rewrite the following music-video beat fields into short natural English render prose for image and video prompting. "
        "Always rewrite them, even if the source is already in English, so that the result fits cinematic live-action prompt writing. "
        "Stay faithful to the original meaning. Do not add new locations, props, characters, or symbolic story ideas. "
        "Use section_label, story_role, and visual_role as hidden dramatic guidance for why this shot exists in the chain, but do not repeat those labels in the output. "
        "Make each beat feel like a necessary music-video keyframe, not just a nice sentence about a place. "
        "Before writing prose, decide the beat's dominant scene grammar: body-led, crossing-led, or surface-led. "
        "Also decide the primary playable surface or path she is using, and one optional supporting detail that stays secondary. "
        "The dominant scene grammar should control the sentence. The support detail must never be the reason the shot exists. "
        "opening_frame should establish the heroine's presence and direction in the world immediately. "
        "continuity_frame should visibly carry the same movement or intention forward one step. "
        "pressure_frame should show a compressed or tightened version of the movement in the same place. "
        "handoff_frame should clearly prepare the next shot by ending on a readable direction, crossing, or body shift. "
        "payoff_frame should land a decisive visible change, not just prettier atmosphere. "
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
        "If the source mentions a reflection, anchor the place on the glass, window edge, umbrella surface, wet pavement, or other physical surface first; reflection should stay secondary unless she is directly tracing or touching it. "
        "Do not use reflection itself as the event. If glass is present, keep the place on the glass edge, door edge, window edge, threshold, or the path beside it, and keep the heroine's movement more important than the reflected image. "
        "If the source mentions a clock or sign together with a doorway, gate, rail, street edge, or platform path, prefer the crossing surface or path as the literal place anchor and treat the clock or sign as background timing only. "
        "If the same beat already has a glass wall, passage line, platform path, gate light, rail, sidewalk, threshold, or curb carrying the heroine's movement, do not mention the stopped clock at all unless her hand or body is directly touching or reading it. "
        "If a platform edge, platform path, threshold, gate line, doorway edge, or passage already carries the action, omit ticking clock, slow clock, station clock, or clock light entirely unless the source literally requires clock contact. "
        "If the source mentions glow or brighter light, anchor the literal place on the object or surface carrying that light, such as wet pavement, a gate lane, a stair, or a doorway, rather than on glow itself. "
        "If a blinking light, call light, sign light, or small illuminated indicator appears beside a stronger surface such as a lane, doorway edge, threshold, gate line, or wall, keep that light as a small side detail and anchor the place on the stronger surface. "
        "If a doorway or door edge is present, keep the place on the threshold, door edge, passage, frontage, sidewalk, or platform side; do not rename it as a room or interior stage unless the source literally enters a room. "
        "Avoid vague place anchors such as open lane, city margin, city line, widening night, blue morning light, or bright glass edge when a more playable surface exists in the same beat. Prefer platform path, gate lane, curb, street edge, exit line, outer sidewalk, stair top, doorway threshold, or wet pavement. "
        "Also avoid making lit windows, glowing displays, glass doors, or stopped clocks the main place anchor when rail, platform edge, turnstile lane, stair, threshold, crosswalk, sidewalk, curb, or gate line is already present in the same beat. "
        "If lit windows are only nearby, anchor the place on the platform end, passage line, rail, curb, gate lane, threshold, or wet pavement instead of on the windows. "
        "If an old ticket appears with a stopped clock, anchor the place on the hand, passage line, gate edge, threshold, or nearby walking surface rather than on the stopped clock. "
        "For opening or payoff beats, prefer the doorway, threshold, gate rail, exit line, or immediate platform path she can physically cross right now over a distant bright point farther ahead. "
        "Every returned field must be natural English prose. Never leave Korean text, mixed-language text, or untranslated fragments in the output. "
        "Do not use the word frame anywhere in the output, even for a physical object; use window edge, rail, border, or casing instead. "
        "literal_image_en should be a concise concrete scene phrase built from one place anchor plus only the surfaces, structures, weather, or local light needed to make that place believable. "
        "Keep literal_image_en compact enough that the heroine can still dominate the image. "
        "literal_image_en should support the beat's dramatic function, so the place feels playable for the action that must happen now, not merely atmospheric. "
        "literal_image_en must not mention body parts, breath, heartbeat, emotions, memories, hesitation, loneliness, relationships, or camera language. "
        "If the original beat uses an inner feeling, memory, hesitation, heartbeat, loneliness, or fear to describe the scene, convert that into a visible environmental trace in the same place instead of naming the feeling. "
        "visible_action_en should be a concise screen-readable present-tense action fragment that describes what is visibly happening in the scene. "
        "visible_action_en should prefer body-grounded motion or contact over abstract mood. "
        "Prefer actions that read clearly in torso, legs, hands, direction, or contact at a glance. "
        "subject_action_en should rewrite visible_action into a heroine-centered present-tense action fragment suitable for prompts that begin with 'She ...'. "
        "subject_action_en should prefer clear physical actions that read in a keyframe, such as walking, turning, leaning, touching, stepping, passing, pausing at a surface, lifting a hand, descending, or changing direction. "
        "subject_action_en should make the beat's role in the chain legible: establish, carry forward, compress, hand off, or land a payoff through visible action. "
        "Keep that progression concrete: prefer step, pass, clear, cross, turn, lean, brace, touch, climb, descend, or lengthen her stride over generic dramatic verbs such as drives, claims, opens the night, breaks free, or pushes destiny forward. "
        "subject_action_en should avoid body-part fixation, decorative metaphor, relationship language, viewer-facing language, and vague emotion-only verbs. "
        "Choose actions that keep the heroine readable and present rather than actions that naturally push her tiny into the distance. "
        "If the beat supports it, prefer actions with one readable contact detail such as a hand on glass, a hand along a rail, or a step through an opening, because those tend to hold the heroine and place together more clearly. "
        "If glass is present, prefer passing the glass, tracing the edge, pushing past the door edge, or clearing the threshold over checking the reflection, facing the reflection, or letting reflected light become the action. "
        "If stairs, stairwell, landing, escalator, or ramp are present together with a nearby window, keep the primary movement on the stair geometry first; do not promote the window edge unless she is directly touching or bracing on that surface. "
        "If she passes through a doorway, gate, or opening, end on threshold, gate line, doorway edge, passage, curb, pavement, or street edge; do not use awkward meta-like nouns such as frame as the destination. "
        "If a doorway is already readable as a threshold, do not write opens the doorway, opens the glass doorway, opens the last door, or enters the brighter corridor when clears the doorway, steps through the threshold, or lands beyond the door edge is more literal. "
        "Avoid phrasing that leaves her frozen in place, such as 'stays', 'remains', or 'holds still', unless the original beat explicitly requires stillness as the main visible event. "
        "Avoid weak keyframe verbs such as watches, looks, gazes, waits, breathes, exhales, smiles softly, or lets the scene happen around her when a clearer visible action is possible. "
        "Do not use spreading fingers, opening hands, breathing out, or looking across space as the main visible action in payoff or release beats when a clearer forward step, pass, clear, or crossing action is available in the same place. "
        "Do not use opening her hand, opening her palm, or letting old light fade across her hand as the main visible action when a threshold, lane, edge, or step can carry the same beat more clearly. "
        "Do not use looking toward lit windows, looking through glass, watching a display, or keeping time with a clock as the main visible action when a step, turn, rail contact, curb crossing, gate pass, stair descent, or threshold crossing is available in the same beat. "
        "If a ticket, card, or other small object is present, keep it as a hand action inside a larger movement through the place, not as a still life under a clock, sign, or display. "
        "If a ticket or card appears with a clock, do not make her gaze lock onto the clock; keep her movement on the platform edge, gate line, curb, threshold, or path while the hand action with the ticket stays secondary. "
        "If a ticket, card, or paper appears with a window, keep the path or threshold movement primary; do not write turning the ticket in her hand as the main event when she can keep moving past the edge beside her. "
        "If a gate lane or turnstile lane is present with a clock, do not write looking up at the clock as the visible action; rewrite the beat as slowing, leaning, or stepping into the lane while the clock remains only background timing. "
        "If a handrail, rail, or platform edge is present with a clock, do not write her gaze rising to the clock; keep the action on the handrail, edge, or next step while the clock stays overhead as background timing only. "
        "If a window, glass, or lit opening is present, do not make turning toward the light, facing the light, or watching the light the event when she can instead pass the edge, keep moving, angle forward, or turn back once while continuing on. "
        "If lit windows are present, never make them the still subject of the beat. Keep them background-only while the heroine checks the ticket, turns back once, keeps moving forward, or clears the next surface. "
        "If the beat already has a strong primary surface such as ticket gate, turnstile lane, platform edge, rail, stair, passage, threshold, curb, sidewalk, street edge, or station floor, do not mention clock light, lit windows, sign light, or window glow in literal_image_en unless that light physically changes the surface she is using right now. "
        "If lit windows, a sign, or a clock only sit nearby, keep them out of literal_image_en and continuity_anchor_en; let the primary surface and the heroine's movement carry the beat. "
        "If a signal or countdown light is present, mention it only when the action is actually tied to a change in timing on the same surface, such as stepping as the signal changes. Otherwise omit it. "
        "If a glass wall or ad board is only adjacent to the path, do not mention it in literal_image_en or support_detail_en unless she directly brushes, touches, or turns across that edge. "
        "If primary_surface is platform edge, platform lane, station floor, sidewalk, street edge, or threshold, prefer rain, puddles, rail contact, doorway movement, or the next reachable surface over wind, glass wall, speaker detail, vending machine light, or generic signal light as the support detail. "
        "If wind only adds atmosphere and does not materially change her balance, bracing, or crossing, omit wind from literal_image_en, visible_action_en, subject_action_en, support_detail_en, and continuity_anchor_en. "
        "Do not describe wind pushing her coat, splitting around her, moving ahead of her, or pulling at her hair when the same beat can be carried by stride, threshold, curb, gate, stair, frontage, or sidewalk movement alone. "
        "If wind is tied only to a passing bus, train, or vehicle and not to her actual balance on the surface, omit that bus wind or passing wind entirely and keep the beat on the step, stair, curb, or path instead. "
        "If the beat is on a platform edge or doorway gap and she is not visibly bracing into the wind, omit crosswind and platform wind entirely and keep the beat on turning, stepping through, or continuing along the edge. "
        "If the primary movement is on steps, stairs, stairwell, landing, or escalator and she is not visibly bracing into the wind, omit wind entirely and keep the beat on the climb, descent, or continued step. "
        "If she is already clearing a doorway, threshold, or exit line, do not add 'into the wind' unless the source clearly requires the wind as the obstacle of the beat. "
        "If the beat implies wet footprints, a trail on the ground, or marks spreading behind her, keep that as a material ground trace rather than deleting it as abstract mood. "
        "In Bridge or other compression beats, a wet-footprint trail can survive as support_detail_en or continuity_anchor_en when it strengthens the same playable surface she is moving on. "
        "If wet footprints or a track on the floor are present, keep the action on the same platform, pavement, or floor while the footprints remain a secondary trace of motion behind her. "
        "Do not build literal_image_en as a still life of a ticket and a clock together when the same beat already has a playable surface or lane she can move through. "
        "Also avoid static verbs such as studies, admires, lets a reflection settle, holds a smile, lets a smile rise, lets the motion settle, or lets the floor steady when a more readable visible action can carry the beat. "
        "Do not use heartbeat, hesitation, memory, loneliness, or pause as the main visible event unless there is no other faithful physical reading. "
        "If the source suggests a static feeling, convert it into a small but visible physical action in the same place. "
        "If the source says she stands still, pauses, waits, only breathes, or only watches something, rewrite it into a subtle but readable movement such as shifting her weight, taking a step, turning, touching a surface, tracing a rail or glass edge, crossing a threshold, or lifting a hand while staying in the same space. "
        "If the source says she looks up at a clock, rewrite that into a slowed step, tightened hand on rail, poised lean at the gate, or forward-ready pause in the same place instead of an upward-looking beat. "
        "If the source says she looks at lit windows or light beyond the glass, rewrite that into passing the window edge, brushing the wall, turning back once while still moving, or angling her body forward in the same space. "
        "If windows are only side structure beside a sidewalk, frontage, passage, compressed lane, gate lane, threshold path, platform edge, or stair run, omit the windows entirely from visible_action_en, subject_action_en, and continuity_anchor_en unless she is directly touching, fogging, pressing into, or turning back from that surface. "
        "If the primary movement is on a crosswalk, curb, street edge, sidewalk, stair, stairwell, landing, escalator, or ramp, do not keep nearby windows, lit windows, or neon on the window as part of the action or continuity unless she is directly using that window surface. "
        "If the primary movement is on a platform edge, platform lane, or platform end, do not keep blurred windows, passing train windows, a passing train window, opposite windows, or a nearby window edge in visible_action_en, subject_action_en, support_detail_en, or continuity_anchor_en unless her body is directly pressed to that moving window surface. "
        "If the primary movement is on stairs, stairwell, landing, escalator, ramp, sidewalk, or street edge, do not let windows above her, lit windows beside her, or windows switching on become part of the action or continuity. Keep the beat on the climb, descent, or stride instead. "
        "Do not describe a generic neon-smeared window edge or passing window light streaking by unless the heroine is directly touching, tracing, fogging, or pressing against that window surface. "
        "If the primary movement is on a gate line, gate lane, turnstile lane, or gate pass, do not keep window light, passing window light, lit panels, or window glow in visible_action_en, subject_action_en, support_detail_en, or continuity_anchor_en. Keep the beat on clearing the gate and landing beyond it. "
        "If the primary movement is on a landing, stair top, wet road, street edge, sidewalk, or open pavement, do not keep window light, passing window light, or light spilling from windows in visible_action_en, subject_action_en, support_detail_en, or continuity_anchor_en unless the heroine is directly using that window surface. "
        "If a cold handle, door handle, rail handle, or pull handle appears with a carriage window or train window, make the handle or door edge the playable surface and omit the carriage window from visible_action_en, subject_action_en, and continuity_anchor_en unless she is directly pressed to the glass. "
        "If she is already walking on a sidewalk or street edge while carrying a cup, bag, or other small object, do not make a store window or convenience-store window the action anchor; keep the beat on the sidewalk continuation and the carried object instead. "
        "If she is already on a curb, sidewalk, or street edge, do not keep a convenience-store window, store window, or passing car window in visible_action_en, subject_action_en, or continuity_anchor_en. Keep the beat on the curb or sidewalk continuation instead. "
        "If a beat is sidewalk_continuation, curb_crossing, or another plain locomotion shot, do not write lit windows falling behind her, windows beside her, or city light moving in the glass as the continuity anchor. Keep continuity_anchor_en on stride, curb, crosswalk, sidewalk, or the next reachable surface instead. "
        "If a beat is true window contact, keep the continuity on her contact changing against the window edge or glass edge. Do not widen it into lit windows behind her or city light drifting across the glass unless that contact itself is still the event. "
        "If a ticket, card, or paper action happens while she is already walking on a sidewalk, gate lane, or platform path, keep the action on the walk and the hand movement; omit nearby opposite windows entirely. "
        "If the source suggests opening a hand, releasing a hand, or light fading over her hand, rewrite that as a step, clear, pass, or threshold move in the same place rather than a hand-only event. "
        "If a doorway or opening appears, describe the threshold crossing itself, the hinge side, the door edge, or the first step through it; do not turn the beat into a symbolic portal or a theatrical opening image. "
        "If windows, carriage windows, or a window line appear beside a path, platform edge, sidewalk, or passage, treat the window line as side structure rather than the route itself unless her body is pressed directly to that edge. "
        "Do not describe windows rising above her, the city opening wide beside the windows, or brighter corridor mood when a simpler path, threshold, or edge movement can carry the beat. "
        "If breath, hesitation, heartbeat, or memory is important, show it through her hand, shoulders, step, or contact with a nearby surface instead of naming that internal state directly. "
        "If fog, condensation, or cold air matters, prefer the effect on glass, metal, fabric, or light rather than stating breath directly. "
        "If the source offers both a distant symbolic target and a nearby surface or path, prefer the nearby surface or path for visible_action_en and subject_action_en. "
        "If the source mentions reflection, clock, sign, or glow together with a readable body movement, keep the body movement and nearby surface primary and demote the symbolic element to background support. "
        "When a stopped clock appears next to glass, a passage, a gate, or a sidewalk, keep the action on crossing that surface and omit the clock from subject_action_en unless the source literally makes the clock-contact the event. "
        "If a stair, rail, tread, stair top, or stairwell appears, keep the heroine on that stair geometry; do not flatten the shot into a generic road walk, wide crosswalk, or open boulevard. "
        "For opening or release beats, prefer crossing actions such as stepping through, clearing the gate, passing the rail, crossing the exit line, or moving into the doorway over merely approaching a bright place from afar. "
        "For payoff or release beats, express arrival through a concrete surface reached or crossed, such as the far curb, the road edge, the last step, the gate line, or the platform exit, rather than abstract triumph language. "
        "In handoff or payoff beats, do not finish the action by describing a reflection, glass surface, or light lingering behind her when a concrete next surface such as pavement, curb, street edge, exit line, or sidewalk is available ahead of her. "
        "Treat final release as continued forward crossing inside the same world, not as a symbolic tableau of light or aftermath. "
        "For Final Chorus beats, keep the heroine outward-facing and locomotor. Prefer walking, crossing, stepping through, clearing, passing, or continuing forward over inward emotional release. "
        "For final opening or release beats, do not make smiling, reflection, reflections brightening behind her, a train window reflection, a glowing window, a glass storefront reflection, a clock outside, warm light ahead, pale dawn light, light gathering in front of her, a bright sign, a clearing path, a lane of light ahead, lifted face toward light, settling/steadying motion, a folded ticket, fading light in her hand, or lingering light after the last train the main event when a forward crossing action in the same place can carry the beat. "
        "In final opening or release beats, prefer gate, threshold, exit, street entry, platform edge crossing, stair-top crossing, crosswalk crossing, or doorway crossing over lingering by a window, holding at the edge, moving toward a vague glow, leaving a reflection behind, opening her fingers toward space, using a small hand gesture as the main event, or dwelling on the last train aftermath. "
        "If daybreak, morning, or brighter air is present in a release beat, keep it as background light only; do not use dawn, morning, sunrise, or brighter sky as the place anchor or the event itself. "
        "If a release beat involves a street crossing, platform exit, or curb entry, anchor the literal place on the curb, crosswalk, street edge, platform exit line, or threshold surface first, not on glass frontage or surrounding skyline. "
        "If the source implies reunion, recognition, holding hands, embrace, or togetherness but does not clearly show another visible body, convert that into a single-heroine action such as crossing a gate, passing a rail, stepping through a doorway, clearing a platform edge, or reaching the far side of a street in the same place. "
        "If the source implies a person ahead, behind, beside, or turning away without a clearly visible second body, rewrite it as her changed direction, a crossed threshold, or a cleared exit line in the same place. "
        "Never output another woman, another man, the other woman, the other person, two women, two people, embrace, hug, clasp hands, or holding hands unless the source literally requires two visible bodies in the frame. "
        "If the beat lands on a smile or soft release, show it through crossing a threshold, clearing a gate, reaching the far side of a street or platform edge, or stepping through a doorway rather than describing the smile as a held pose. "
        "Do not use generic release phrases such as one steady rhythm, calm steady pace, open space, brighter direction, or path clearing when a specific crossing action is available in the same place. "
        "In Final Chorus or other release beats, keep light only as supporting local illumination on a surface or threshold; do not let light, glow, dawn, sign, or reflection become the event itself. "
        "In Final Chorus or other release beats, prefer exit line, turnstile lane, gate rail, stair top, curb crossing, street edge, or platform edge as the literal place anchor over window reflection, clock, signboard, skyline, or vague opening. "
        "In Final Chorus or other release beats, avoid generic alley end or alley mouth wording when curb, crosswalk, street edge, exit line, sidewalk, or station frontage can carry the same movement more clearly. "
        "In Final Chorus or other release beats, do not keep lit windows in the place anchor when outer sidewalk, curb, street edge, exit line, or frontage already carries the movement. "
        "In open-world or release beats, avoid city margin, city line, widening night, open lane, blue morning light, or bright glass edge as the place anchor when pavement, platform path, curb, gate lane, exit line, or outer sidewalk is available in the same beat. "
        "In Final Chorus or other release beats, do not make train window, lit windows, or window line the place anchor when platform edge, exit line, crosswalk, doorway, outer sidewalk, or street edge can carry the same movement more directly. "
        "In Final Chorus or other release beats, do not make cold glass, window touch, or reflection touch the main action when the same beat can instead land on the exit line, gate opening, platform edge, crosswalk, or street edge. "
        "Avoid late poetic light phrases such as last bright strip of the day, last light, lingering strip of light, or living neon path when exit line, pavement, platform end, curb, or doorway threshold can carry the same beat more concretely. "
        "If the original mentions camera, frame, shot, cut, filming, shake, zoom, or viewpoint, rewrite only the visible on-screen event and never mention filming language in English. "
        "For example, camera shake should become a visible movement in the space, the heroine, the light, or nearby surfaces, not camera wording. "
        "If the original is metaphorical, convert it into the nearest believable visual event in the same place. "
        "Avoid abstract environment phrases such as pocket, glow-map, quiet light, trembling glass light, brighter edge of town, last strip of night, platform glow spreading, or end of the night when a more literal place and light description can carry the same beat. "
        "When choosing between an inner-state word and a small physical action, always choose the physical action. "
        "dominant_scene_grammar_en must be exactly one short phrase chosen from: body-led, crossing-led, or surface-led. "
        "primary_surface_en should name the one playable surface, path, edge, threshold, rail, curb, stair, lane, or pavement that actually carries the action. "
        "support_detail_en should be one short optional secondary detail, such as supporting light, rain on glass, or a nearby sign, and it must stay subordinate to the primary surface and action. "
        "support_detail_en may be empty. If the only available detail is a clock, sign, lit window, stopped clock, display, or symbolic light cue that does not materially strengthen the playable surface, leave support_detail_en blank instead of forcing it in. "
        "If a clock, lit windows, sign, or window light only repeats atmosphere already implied by the place, omit it from support_detail_en and keep the beat cleaner. "
        "Prefer support_detail_en values like rain, puddles, handle, rail, door movement, or wet ground over wind, clock light, lit windows, sign glow, speaker detail, vending machine light, or symbolic glass light. "
        "Wet footprints, footprint trails, or dark tracks on wet ground count as material support details when they directly belong to the same surface she is using. "
        "Also prefer rail contact, doorway movement, and wet ground over wind, ad board edge, glass wall, speaker detail, or fixed signal light when those elements are only adjacent background structures. "
        "If removing the support detail would break the scene's core meaning, then it is not a support detail and you must choose a more physical primary surface instead. "
        "continuity_anchor_en should be a short visual state phrase for continuity checking. "
        "The continuity anchor must track the heroine's body relation to the primary surface or path, not the motion of a reflection, light effect, or other support detail. "
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
    grammar = " ".join(str(cleaned.get("dominant_scene_grammar_en", "")).strip().rstrip(".").split()).lower()
    if grammar not in {"body-led", "crossing-led", "surface-led"}:
        grammar = _infer_scene_grammar(
            " ".join(str(cleaned.get("subject_action_en", "")).strip().split()),
            " ".join(str(cleaned.get("literal_image_en", "")).strip().split()),
        )
    cleaned["dominant_scene_grammar_en"] = grammar
    primary_surface = " ".join(str(cleaned.get("primary_surface_en", "")).strip().rstrip(".").split())
    if not primary_surface or _contains_render_meta(primary_surface):
        primary_surface = _infer_primary_surface(
            " ".join(str(cleaned.get("literal_image_en", "")).strip().split()),
            " ".join(str(cleaned.get("subject_action_en", "")).strip().split()),
        )
    primary_surface = _normalize_primary_surface(
        primary_surface,
        " ".join(str(cleaned.get("subject_action_en", "")).strip().split()),
        " ".join(str(cleaned.get("literal_image_en", "")).strip().split()),
    )
    if _primary_surface_is_unplayable(primary_surface):
        primary_surface = _normalize_primary_surface(
            _infer_primary_surface(
                " ".join(str(cleaned.get("literal_image_en", "")).strip().split()),
                " ".join(str(cleaned.get("subject_action_en", "")).strip().split()),
            ),
            " ".join(str(cleaned.get("subject_action_en", "")).strip().split()),
            " ".join(str(cleaned.get("literal_image_en", "")).strip().split()),
        )
    cleaned["primary_surface_en"] = primary_surface
    support_detail = " ".join(str(cleaned.get("support_detail_en", "")).strip().rstrip(".").split())
    if _contains_render_meta(support_detail):
        support_detail = ""
    support_detail = _lean_support_detail(primary_surface, support_detail)
    cleaned["support_detail_en"] = support_detail
    cleaned["literal_image_en"] = _lean_literal_image(
        primary_surface,
        support_detail,
        " ".join(str(cleaned.get("literal_image_en", "")).strip().split()),
    )
    cleaned["continuity_anchor_en"] = _lean_continuity_anchor(
        primary_surface,
        " ".join(str(cleaned.get("continuity_anchor_en", "")).strip().split()),
    )
    return cleaned


def _lean_continuity_anchor(primary_surface: str, continuity_anchor: str) -> str:
    surface = " ".join(str(primary_surface).strip().rstrip(".").split())
    continuity = " ".join(str(continuity_anchor).strip().rstrip(".").split())
    if not continuity:
        return continuity
    lowered = continuity.lower()
    if any(
        token in lowered
        for token in (
            "clock",
            "sign",
            "lit windows",
            "window light",
            "signal light",
            "display",
            "glow",
            "reflection",
            "glass light",
        )
    ):
        if surface:
            return f"She stays on the {surface}"
    return continuity


def _infer_scene_grammar(action: str, literal: str) -> str:
    text = f"{action} {literal}".lower()
    if any(token in text for token in ("cross", "clear", "through", "threshold", "gate", "doorway", "exit", "curb", "crosswalk")):
        return "crossing-led"
    if any(token in text for token in ("rail", "glass", "window", "edge", "stair", "pavement", "sidewalk", "platform")):
        return "surface-led"
    return "body-led"


def _infer_primary_surface(literal: str, action: str) -> str:
    text = f"{literal} {action}".lower()
    candidates = (
        "platform edge",
        "platform path",
        "wet pavement",
        "sidewalk",
        "curb",
        "crosswalk",
        "gate line",
        "gate lane",
        "threshold",
        "door edge",
        "passage",
        "glass edge",
        "window edge",
        "rail",
        "handrail",
        "stairwell",
        "stairs",
        "street edge",
    )
    for candidate in candidates:
        if candidate in text:
            return candidate
    return "path through the place"


def _normalize_primary_surface(primary_surface: str, action: str, literal: str) -> str:
    surface = " ".join(str(primary_surface).strip().rstrip(".").split()).lower()
    context = f"{action} {literal}".lower()
    if not surface:
        return surface
    replacements = {
        "train window": "window edge",
        "train window edge": "window edge",
        "last-train window edge": "window edge",
        "last-train window": "window edge",
        "carriage window": "window edge",
        "car window edge": "window edge",
        "train window line": "window edge",
        "train windows": "window edge",
        "lit windows": "window edge",
        "glass window": "window edge",
        "glass window edge": "window edge",
        "glass door threshold": "doorway threshold",
        "glass doorway threshold": "doorway threshold",
        "automatic door threshold": "doorway threshold",
        "wet crosswalk edge": "wet crosswalk",
        "wet track edge": "platform edge",
        "track-side platform edge": "platform edge",
        "station frontage lane": "platform lane",
        "station gate lane": "gate lane",
        "ticket gate": "gate lane",
        "station approach path": "sidewalk",
        "station frontage at street level": "street frontage",
        "carriage window line": "passage line",
        "glass door edge": "doorway threshold",
        "door edge": "doorway threshold",
        "boundary line": "exit line",
        "escalator by the train windows": "escalator steps",
        "street": "street edge",
        "alley lane": "passage line",
        "old stairs": "stairs",
        "neon road": "wet road",
        "station edge": "station walkway",
        "station front": "street frontage",
    }
    if surface in replacements:
        surface = replacements[surface]
    if "vending machine glass" in surface:
        surface = "passage line"
    if "warm cup" in surface:
        surface = "station floor"
    if "platform wind" in surface:
        surface = "platform edge"
    if "speaker" in surface:
        surface = "street edge"
    if "signal light" in surface:
        surface = "street edge"
    if "vending machine light" in surface:
        surface = "gate lane"
    if "train windows" in surface and "escalator" in context:
        surface = "escalator steps"
    if "window" in surface and any(token in context for token in ("escalator", "stairs", "stairwell", "rises", "climbs")):
        return "escalator steps" if "escalator" in context else "stairs"
    if any(token in surface for token in ("window edge", "glass edge", "last-train window edge", "wet window edge")):
        contact_tokens = ("press", "pressed", "palm", "touch", "touches", "touching", "brush", "brushing", "trace", "tracing", "hand on", "shoulder against")
        if not any(token in context for token in contact_tokens):
            if any(token in context for token in ("stairs", "stair", "stairwell", "landing", "escalator", "ramp", "climbs", "climbing", "descends", "descending")):
                return "escalator steps" if "escalator" in context else "stairs"
            if any(token in context for token in ("doorway", "threshold", "exit", "opening", "gate")):
                return "doorway threshold"
            if any(token in context for token in ("platform", "yellow line", "tracks")):
                return "platform edge"
            if any(token in context for token in ("street", "curb", "crosswalk", "sidewalk", "frontage")):
                return "street edge"
            return "passage line"
    if surface == "window edge" and any(
        token in context
        for token in (
            "walk",
            "walking",
            "moving past",
            "moves past",
            "passes",
            "passes the",
            "keeps moving",
            "walks along",
            "keeps her direction",
            "keeps his direction",
            "keeps the direction",
            "beside the window",
            "along the window",
        )
    ):
        return "passage line"
    if surface == "window edge" and any(
        token in context
        for token in (
            "station entrance",
            "turnstile",
            "gate line",
            "gate lane",
            "threshold",
            "platform edge",
            "platform path",
            "wet platform",
        )
    ):
        if any(token in context for token in ("turnstile", "gate line", "gate lane", "threshold", "station entrance")):
            return "doorway threshold"
        return "platform edge"
    if surface == "platform rail" and any(token in context for token in ("walk", "moving past", "keeps moving", "cross", "clear")):
        return "platform edge"
    if surface == "window edge" and any(token in context for token in ("threshold", "cross", "clear", "exit", "doorway")):
        return "doorway threshold"
    if surface == "gate lane" and "wind" in context:
        return "gate lane"
    if surface == "door edge" and "threshold" in context:
        return "doorway threshold"
    return surface


def _primary_surface_is_unplayable(primary_surface: str) -> bool:
    surface = str(primary_surface).strip().lower()
    if not surface:
        return True
    blocked = (
        "cup",
        "bag strap",
        "display",
        "glow",
        "light",
        "neon",
        "lit windows",
        "window line",
        "window lights",
        "sign",
        "clock",
        "vending machine glass",
        "car-window lights",
    )
    return any(token in surface for token in blocked)


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
        return "a transit-side edge and moving side structure"
    if "ticket gate" in motif_text:
        return "a gate lane and threshold surface"
    if "curb reflection" in motif_text:
        return "wet curbside pavement and ground contact"
    if "puddle" in motif_text:
        return "wet ground and curb-adjacent pavement"
    if "platform sign glow" in motif_text:
        return "a platform path and overhead station edge"
    if "stair landing" in motif_text:
        return "stairs, landing, and handrail geometry"
    return motif_text


def _environment_family(motif_text: str) -> str:
    motif = motif_text.strip().lower()
    if "train window" in motif:
        return "transit_side_edge"
    if "ticket gate" in motif:
        return "gate_threshold"
    if "curb reflection" in motif:
        return "wet_ground_path"
    if "puddle" in motif:
        return "wet_ground_path"
    if "platform sign glow" in motif:
        return "platform_path"
    if "stair landing" in motif:
        return "vertical_path"
    return "urban_path"


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
        "transit_side_edge": {
            "space_type": "threshold",
            "axis_type": "side_path",
            "contact_plane": "side_edge",
            "transition_group": "transit_path",
        },
        "gate_threshold": {
            "space_type": "threshold",
            "axis_type": "lane_forward",
            "contact_plane": "barrier_lane",
            "transition_group": "station_threshold",
        },
        "wet_ground_path": {
            "space_type": "open_exterior",
            "axis_type": "street_plane",
            "contact_plane": "ground_plane",
            "transition_group": "street_path",
        },
        "platform_path": {
            "space_type": "threshold",
            "axis_type": "station_depth",
            "contact_plane": "platform_plane",
            "transition_group": "station_threshold",
        },
        "vertical_path": {
            "space_type": "vertical_path",
            "axis_type": "stair_depth",
            "contact_plane": "step_depth",
            "transition_group": "vertical_transit",
        },
        "urban_path": {
            "space_type": "threshold",
            "axis_type": "street_plane",
            "contact_plane": "ground_plane",
            "transition_group": "generic_urban",
        },
    }
    return dict(traits.get(family, traits["urban_path"]))


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
