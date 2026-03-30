from __future__ import annotations

import zlib

from ai_mv.core.contracts.seedance_v2_normalize import normalize_scene_plan_v2
from ai_mv.core.director_brief import build_director_brief_intent


def build_scene_plan_v2(config: dict, payload: dict) -> dict:
    brief = build_director_brief_intent(config)
    timeline = payload["lyrics_timeline"]
    sections = [row for row in timeline.get("sections", []) if isinstance(row, dict)]
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
        motif_sequence = _motif_sequence_for_section(motifs, section_label)
        for beat_index, beat in enumerate(section_beats, start=1):
            if not isinstance(beat, dict):
                continue
            beat_id = str(beat.get("beat_id", "")).strip()
            if not beat_id:
                continue
            motif = motif_sequence[(beat_index - 1) % len(motif_sequence)]
            continuity_group = f"{section_label}:{zone}"
            environment_anchor = _environment_anchor(zone, motif, beat)
            shot_packages.append(
                {
                    "shot_id": beat_id,
                    "section_name": section_name,
                    "section_label": section_label,
                    "beat_refs": [beat_id],
                    "line_refs": [int(x) for x in beat.get("line_refs", []) if int(x) > 0],
                    "story_role": story_role,
                    "visual_role": _visual_role(section_label, zone, beat_index, section_beat_count),
                    "zone": zone,
                    "motif_family": motif,
                    "continuity_group": continuity_group,
                    "identity_core": brief["identity_core"],
                    "environment_family": _environment_family(motif),
                    "camera_distance_band": _camera_distance_band(zone, section_label),
                    "environment_anchor": environment_anchor,
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
        "Map each lyric beat into a zone progression and one object-or-space-led scene anchor."
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


def _environment_anchor(zone: str, motif: str, beat: dict) -> str:
    return _zone_environment_phrase(zone, motif)


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


def _camera_distance_band(zone: str, section_label: str) -> str:
    zone_key = zone.strip().lower()
    section = section_label.strip().lower()
    if "bridge" in section or zone_key == "compression":
        return "tight_medium"
    if "final chorus" in section:
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
        return "payoff_frame"
    if "bridge" in section or zone_key == "compression":
        return "pressure_frame"
    if beat_index >= beat_count:
        return "handoff_frame"
    return "continuity_frame"


def _motif_sequence_for_section(motifs: list[str], section_label: str) -> list[str]:
    motif_rows = [str(m).strip() for m in motifs if str(m).strip()]
    if not motif_rows:
        return ["world motif"]
    offset = zlib.crc32(section_label.encode("utf-8")) % len(motif_rows)
    return motif_rows[offset:] + motif_rows[:offset]
