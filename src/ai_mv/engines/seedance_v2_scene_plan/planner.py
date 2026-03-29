from __future__ import annotations

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
        for beat_index, beat in enumerate(section.get("lyric_beats", []), start=1):
            if not isinstance(beat, dict):
                continue
            beat_id = str(beat.get("beat_id", "")).strip()
            if not beat_id:
                continue
            motif = motifs[(len(shot_packages)) % len(motifs)]
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
                    "zone": zone,
                    "motif_family": motif,
                    "continuity_group": continuity_group,
                    "identity_core": brief["identity_core"],
                    "environment_anchor": environment_anchor,
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
    zone_phrase = _zone_environment_phrase(zone, motif)
    return zone_phrase


def _zone_environment_phrase(zone: str, motif: str) -> str:
    motif_text = motif.strip() or "city detail"
    phrases = {
        "threshold": f"a threshold space held by {motif_text}",
        "edge": f"an edge-of-decision space around {motif_text}",
        "compression": f"a compressed pocket of the city around {motif_text}",
        "open_world": f"a wider city opening around {motif_text}",
        "open_world_peak": f"the brightest open-world release around {motif_text}",
        "residue": f"a lingering after-image around {motif_text}",
        "narrow_world": f"a close city pocket around {motif_text}",
        "transit_lane": f"a moving transit lane around {motif_text}",
    }
    return phrases.get(zone.strip().lower(), f"a city space around {motif_text}")
