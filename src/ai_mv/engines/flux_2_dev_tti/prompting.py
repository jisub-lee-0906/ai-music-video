from __future__ import annotations

from ai_mv.core.contracts.prompt_schema import SHOT_TYPES


def _tti_beat_manifest(story_bible: dict) -> list[str]:
    out: list[str] = []
    for beat in story_bible.get("lyric_beats", []):
        if not isinstance(beat, dict):
            continue
        beat_id = str(beat.get("beat_id", "")).strip()
        if not beat_id:
            continue
        section = str(beat.get("section_label", beat.get("section_name", ""))).strip()
        payoff = str(beat.get("payoff_role", "")).strip()
        out.append(f"{beat_id}|{section}|{payoff}")
    return out


def _tti_beat_rows(story_bible: dict) -> list[dict]:
    rows: list[dict] = []
    for beat in story_bible.get("lyric_beats", []):
        if not isinstance(beat, dict):
            continue
        beat_id = str(beat.get("beat_id", "")).strip()
        if not beat_id:
            continue
        rows.append(
            {
                "beat_id": beat_id,
                "section_name": str(beat.get("section_name", "")).strip(),
                "section_label": str(beat.get("section_label", beat.get("section_name", ""))).strip(),
                "literal_image": str(beat.get("literal_image", "")).strip(),
                "visible_action": str(beat.get("visible_action", "")).strip(),
                "payoff_role": str(beat.get("payoff_role", "")).strip(),
                "prompt_focus": str(beat.get("prompt_focus", "")).strip(),
                "space_event": str(beat.get("space_event", "")).strip(),
                "composition_shape": str(beat.get("composition_shape", "")).strip(),
            }
        )
    return rows


def _story_bible_digest(story_bible: dict) -> str:
    beats = story_bible.get("lyric_beats", [])
    return (
        f"hero={story_bible.get('hero_identity_lock', '')}; world={story_bible.get('world_rules', '')}; "
        + "beats="
        + ", ".join(
            f"{beat.get('beat_id', '')}|{beat.get('section_label', beat.get('section_name', ''))}|"
            f"{beat.get('literal_image', '')}|{beat.get('symbolic_image', '')}|{beat.get('prompt_focus', '')}|{beat.get('edit_device', '')}|{beat.get('composition_shape', '')}|{beat.get('palette_mode', '')}|{beat.get('payoff_role', '')}"
            for beat in beats
            if isinstance(beat, dict)
        )
    )


def _timeline_digest(timeline: dict) -> str:
    rows: list[str] = []
    for section in timeline.get("sections", []):
        if not isinstance(section, dict):
            continue
        rows.append(
            f"{section.get('section_label', section.get('section_name', 'section'))}="
            + ",".join(str(beat.get("beat_id", "")) for beat in section.get("lyric_beats", []) if isinstance(beat, dict))
        )
    return "; ".join(rows)


def _policy_digest(policy: dict) -> str:
    if not isinstance(policy, dict):
        return ""
    distribution = policy.get("shot_distribution", {})
    mix = ",".join(f"{key}:{distribution[key]:.2f}" for key in SHOT_TYPES if key in distribution)
    direct_sections = ",".join(str(x).strip() for x in policy.get("direct_face_sections", []) if str(x).strip())
    return (
        f"visual_mode={policy.get('visual_mode', '')}; "
        f"visual_mv_mode={policy.get('visual_mv_mode', '')}; "
        f"continuity_mode={policy.get('continuity_mode', '')}; "
        f"face_policy={policy.get('face_policy', '')}; "
        f"shot_bias={policy.get('shot_bias', '')}; "
        f"subject_exposure={policy.get('subject_exposure', '')}; "
        f"motif_density={policy.get('motif_density', '')}; "
        f"graphic_event_density={policy.get('graphic_event_density', '')}; "
        f"environment_event_density={policy.get('environment_event_density', '')}; "
        f"visual_payoff_mode={policy.get('visual_payoff_mode', '')}; "
        f"ref_policy={policy.get('ref_policy', '')}; "
        f"shot_mix={mix}; "
        f"direct_face_sections={direct_sections}"
    )
