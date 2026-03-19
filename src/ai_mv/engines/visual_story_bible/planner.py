from __future__ import annotations

from ai_mv.core.contracts.prompt_normalize import normalize_visual_story_bible
from ai_mv.core.contracts.prompt_schema import visual_story_bible_schema
from ai_mv.core.visual_pipeline import location_grammar_digest
from ai_mv.infra.codex_cli_client import generate_structured


def build_visual_story_bible(config: dict, payload: dict) -> dict:
    timeline = payload["lyrics_timeline"]
    raw = generate_structured(config, _planner_prompt(config, payload), visual_story_bible_schema())
    story = normalize_visual_story_bible(raw, list(_timeline_sections(timeline)))
    world = payload.get("profile_intent", {}).get("world_intent", {}) if isinstance(payload.get("profile_intent", {}), dict) else {}
    story["heroine_invariants"] = str(world.get("heroine_invariants", story.get("hero_identity_lock", ""))).strip()
    story["world_invariants"] = str(world.get("world_invariants", story.get("world_rules", ""))).strip()
    story["location_family_rules"] = list(world.get("location_families", story.get("recurring_location_families", [])))
    story["resolved_profile_policy"] = dict(payload.get("profile_intent", {}).get("resolved_profile_policy", {})) if isinstance(payload.get("profile_intent", {}), dict) else {}
    closeup = [
        str(world.get("closeup_policy", "")).strip(),
        str(world.get("payoff_closeup_policy", "")).strip(),
    ]
    story["closeup_rules"] = ". ".join(part for part in closeup if part) or "keep the heroine readable before close-up emphasis"
    return story


def build_visual_story_bible_preview_prompt(config: dict, payload: dict) -> str:
    return _planner_prompt(config, payload)


def _planner_prompt(config: dict, payload: dict) -> str:
    intent = payload.get("profile_intent", {})
    world = intent.get("world_intent", {}) if isinstance(intent, dict) else {}
    negative = intent.get("negative_intent", {}) if isinstance(intent, dict) else {}
    timeline = payload["lyrics_timeline"]
    return (
        "Write a lyric-first visual story bible for downstream image and video workflows. "
        "Return strict JSON only. No prose outside JSON. "
        "Required fields: hero_identity_lock,world_rules,recurring_location_families,forbidden_drift,lyric_beats,section_progression,repeat_escalation_rules. "
        "Follow the lyric timeline exactly. "
        "Create exactly one lyric_beats item for each lyric_timeline beat in the same order. "
        "Do not split, merge, invent, omit, or regroup beats. "
        "Reuse the provided beat_id values exactly once. "
        "NO TEXT, NO TYPOGRAPHY, NO WATERMARKS, NO LOGOS, NO SIGNAGE, NO UI OVERLAY. "
        "section_progression must cover every section in order. "
        "Differentiate sections clearly: verses should not read like choruses, bridges should interrupt or thin the flow, and the final chorus must feel like the visual peak. "
        "Differentiate adjacent lyric beats with a new image focus, action emphasis, framing commitment, palette shift, lighting shift, or location-family angle. "
        "Do not let all beats collapse into the same lane, crosswalk, or reflection treatment if the lyrics turn. "
        "Preserve recurring environment families, but rotate how they are used: threshold, passage, lane, reflection surface, curb edge, sheltered edge, or open crossing should not all be treated the same way. "
        "When sections repeat, keep continuity but escalate the treatment through clearer geography, stronger palette contrast, cleaner action intent, or a more decisive camera commitment. "
        "Use location_family, palette_hint, lighting_hint, and camera_commitment as real differentiators, not decorative synonyms. "
        f"World support={world.get('visual_intent', '')}; Story world={world.get('story_world', '')}; "
        f"Action vocabulary={world.get('action_vocabulary', '')}; Payoff support={world.get('payoff_style', '')}; "
        f"Heroine invariants={world.get('heroine_invariants', '')}; World invariants={world.get('world_invariants', '')}; "
        f"Close-up policy={world.get('closeup_policy', '')}; Motion policy={world.get('motion_policy', '')}; "
        f"Forbidden drift={negative.get('visual_negative', '')}; Avoid={negative.get('mv_avoid', '')}; "
        f"Location grammar={location_grammar_digest(config)}; "
        f"Lyric beat manifest={_timeline_beat_digest(timeline)}; "
        f"Lyric timeline={_timeline_digest(timeline)}."
    )


def _timeline_sections(timeline: dict) -> list[dict]:
    return [
        {
            "name": str(section.get("section_name", "")),
            "label": str(section.get("section_label", section.get("section_name", ""))),
        }
        for section in timeline.get("sections", [])
        if isinstance(section, dict)
    ]


def _timeline_digest(timeline: dict) -> str:
    rows: list[str] = []
    for section in timeline.get("sections", []):
        if not isinstance(section, dict):
            continue
        lines = [
            str(line.get("text", "")).strip()
            for line in section.get("lines", [])
            if isinstance(line, dict) and str(line.get("text", "")).strip()
        ]
        rows.append(
            f"{section.get('section_label', section.get('section_name', 'section'))}:"
            f"{' / '.join(lines[:4])}"
        )
    return " ; ".join(rows)


def _timeline_beat_digest(timeline: dict) -> str:
    rows: list[str] = []
    for section in timeline.get("sections", []):
        if not isinstance(section, dict):
            continue
        beats = []
        for beat in section.get("lyric_beats", []):
            if not isinstance(beat, dict):
                continue
            refs = ",".join(str(x) for x in beat.get("line_refs", []) if int(x) > 0)
            beats.append(f"{beat.get('beat_id', '')}[{refs}]")
        rows.append(
            f"{section.get('section_label', section.get('section_name', 'section'))}="
            + ",".join(part for part in beats if part)
        )
    return " ; ".join(row for row in rows if row)
