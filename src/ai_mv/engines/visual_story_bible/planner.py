from __future__ import annotations

from ai_mv.core.contracts.prompt_normalize import normalize_visual_story_bible
from ai_mv.core.contracts.prompt_schema import visual_story_bible_schema
from ai_mv.core.visual_pipeline import location_grammar_digest
from ai_mv.infra.codex_cli_client import generate_structured


def build_visual_story_bible(config: dict, payload: dict) -> dict:
    timeline = payload["lyrics_timeline"]
    raw = generate_structured(config, _planner_prompt(config, payload), visual_story_bible_schema())
    return normalize_visual_story_bible(raw, list(_timeline_sections(timeline)))


def build_visual_story_bible_preview_prompt(config: dict, payload: dict) -> str:
    return _planner_prompt(config, payload)


def _planner_prompt(config: dict, payload: dict) -> str:
    intent = payload.get("profile_intent", {})
    world = intent.get("world_intent", {}) if isinstance(intent, dict) else {}
    negative = intent.get("negative_intent", {}) if isinstance(intent, dict) else {}
    timeline = payload["lyrics_timeline"]
    return (
        "You are a lyric-first music video story planner for kinetic live-action imagery. "
        "Return strict JSON only. No prose outside JSON. "
        "Required fields: hero_identity_lock,world_rules,recurring_location_families,forbidden_drift,lyric_beats,section_progression,repeat_escalation_rules. "
        "lyric_beats must preserve beat_id, section_name, section_label, and line_refs from the lyric timeline while translating the lyrics into visible screen action. "
        "The video must follow the final generated lyrics first. "
        "literal_image must stay close to what the lyric actually evokes. "
        "visible_action must be something the camera can directly see. "
        "Visible action should favor aggressive live-action tension over safe coverage: whip turns, snap advances, hard stops, impact holds, challenge stares, and match-cut body punctuation. "
        "emotional_turn must explain how this beat changes the feeling from the previous one. "
        "continuity_anchor must keep repeated locations and identity coherent across returns. "
        "payoff_role should describe entry, develop, release, hold, interrupt, or residue. "
        "Repeated hooks must not repeat the same exact action language. "
        "When the music lifts or pays off, plan beats that can justify whip pan, snap zoom, strobe burst, overexposed flash, hard neon contrast, or match-cut pose escalation downstream. "
        "Safe beauty coverage is forbidden when the beat calls for pressure or speed. "
        "NO TEXT, NO TYPOGRAPHY, NO WATERMARKS, NO LOGOS, NO SIGNAGE, NO UI OVERLAY. "
        "All frames must read as clean live-action imagery with zero rendered text elements. "
        "section_progression must cover every section in order. "
        f"World support={world.get('visual_intent', '')}; Story world={world.get('story_world', '')}; "
        f"Action vocabulary={world.get('action_vocabulary', '')}; Payoff support={world.get('payoff_style', '')}; "
        f"Forbidden drift={negative.get('visual_negative', '')}; Avoid={negative.get('mv_avoid', '')}; "
        f"Location grammar={location_grammar_digest(config)}; "
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
        beats = []
        for beat in section.get("lyric_beats", []):
            if not isinstance(beat, dict):
                continue
            beats.append(
                f"{beat.get('beat_id', '')}|lines={','.join(str(x) for x in beat.get('line_refs', []))}|"
                f"image={beat.get('literal_image', '')}|action={beat.get('visible_action', '')}|"
                f"turn={beat.get('emotional_turn', '')}|role={beat.get('payoff_role', '')}"
            )
        rows.append(
            f"{section.get('section_label', section.get('section_name', 'section'))}:"
            f"{' / '.join(beats)}"
        )
    return " ; ".join(rows)
