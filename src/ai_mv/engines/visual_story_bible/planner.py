from __future__ import annotations

import json

from ai_mv.core.contracts.prompt_normalize import normalize_visual_story_bible
from ai_mv.core.contracts.prompt_schema import visual_story_bible_schema
from ai_mv.core.visual_pipeline import location_grammar_digest
from ai_mv.infra.codex_cli_client import generate_structured


def build_visual_story_bible(config: dict, payload: dict) -> dict:
    timeline = payload["lyrics_timeline"]
    prompt = _planner_prompt(config, payload)
    raw = generate_structured(config, prompt, visual_story_bible_schema(), attempts=1)
    _validate_story_bible_contract(raw, timeline)
    story = normalize_visual_story_bible(raw, list(_timeline_sections(timeline)))
    world = payload.get("profile_intent", {}).get("world_intent", {}) if isinstance(payload.get("profile_intent", {}), dict) else {}
    story["heroine_invariants"] = str(world.get("heroine_invariants", story.get("hero_identity_lock", ""))).strip()
    story["world_invariants"] = str(world.get("world_invariants", story.get("world_rules", ""))).strip()
    story["visual_style_contract"] = str(world.get("visual_style_contract", "")).strip()
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
    policy = payload.get("profile_intent", {}).get("resolved_profile_policy", {}) if isinstance(payload.get("profile_intent", {}), dict) else {}
    beat_rows = _timeline_beats(timeline)
    beat_count = len(beat_rows)
    return (
        "Write a lyric-first visual story bible for downstream image and video workflows. "
        "Return strict JSON only. No prose outside JSON. "
        f"Create exactly {beat_count} lyric_beats items, no more and no fewer. "
        "Create exactly one lyric_beats item for each lyric_timeline beat in the same order and preserve every source beat_id exactly. "
        "Treat the source lyric beats as a locked one-to-one transform. "
        "Do not split, merge, invent, omit, or rewrite beat ids. "
        "Do not split a source beat into multiple beats. Do not merge beats. Do not invent beats. Do not omit beats. Do not rewrite beat ids. "
        "Copy section_name, section_label, and line_refs directly from the matching source beat. "
        "Required top-level fields: hero_identity_lock, world_rules, recurring_location_families, forbidden_drift, lyric_beats, section_progression, repeat_escalation_rules. "
        "Required beat fields: beat_id, section_name, section_label, line_refs, literal_image, visible_action, emotional_turn, continuity_anchor, payoff_role, repeat_variant_of, location_family, palette_hint, lighting_hint, camera_commitment, symbolic_image, motif_object, edit_device, prompt_focus, space_event, composition_shape, palette_mode, character_render_mode. "
        "Write render-facing natural English. "
        "camera_commitment should be a clean camera or framing phrase. "
        "composition_shape should be a clean framing phrase. "
        "space_event should be a background-motion clause with a finite verb. "
        "Keep beats visually differentiated and editable. "
        "Do not reduce every beat to the heroine facing camera. "
        "Keep backgrounds graphic and planar rather than photographic. "
        "When sections repeat, preserve continuity but escalate image treatment. "
        f"Style contract={world.get('visual_style_contract', '')}; "
        f"World support={world.get('visual_intent', '')}; Story world={world.get('story_world', '')}; "
        f"Action vocabulary={world.get('action_vocabulary', '')}; Payoff support={world.get('payoff_style', '')}; "
        f"Heroine invariants={world.get('heroine_invariants', '')}; World invariants={world.get('world_invariants', '')}; "
        f"Close-up policy={world.get('closeup_policy', '')}; Motion policy={world.get('motion_policy', '')}; "
        f"Visual MV policy={_visual_mv_policy_digest(policy)}; "
        f"Forbidden drift={negative.get('visual_negative', '')}; Avoid={negative.get('mv_avoid', '')}; "
        f"Location grammar={location_grammar_digest(config)}; "
        f"Lyric beat manifest={_timeline_beat_digest(timeline)}; "
        f"Source lyric beats JSON={json.dumps(beat_rows, ensure_ascii=True)}; "
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


def _timeline_beats(timeline: dict) -> list[dict]:
    rows: list[dict] = []
    for section in timeline.get("sections", []):
        if not isinstance(section, dict):
            continue
        section_name = str(section.get("section_name", "")).strip()
        section_label = str(section.get("section_label", section_name)).strip()
        for beat in section.get("lyric_beats", []):
            if not isinstance(beat, dict):
                continue
            beat_id = str(beat.get("beat_id", "")).strip()
            if not beat_id:
                continue
            rows.append(
                {
                    "beat_id": beat_id,
                    "section_name": section_name,
                    "section_label": section_label,
                    "line_refs": [int(x) for x in beat.get("line_refs", []) if int(x) > 0],
                    "literal_image": str(beat.get("literal_image", "")).strip(),
                    "visible_action": str(beat.get("visible_action", "")).strip(),
                    "emotional_turn": str(beat.get("emotional_turn", "")).strip(),
                    "continuity_anchor": str(beat.get("continuity_anchor", "")).strip(),
                    "payoff_role": str(beat.get("payoff_role", "")).strip(),
                    "repeat_variant_of": str(beat.get("repeat_variant_of", "")).strip(),
                }
            )
    return rows


def _expected_timeline_beat_ids(timeline: dict) -> list[str]:
    out: list[str] = []
    for section in timeline.get("sections", []):
        if not isinstance(section, dict):
            continue
        for beat in section.get("lyric_beats", []):
            if not isinstance(beat, dict):
                continue
            beat_id = str(beat.get("beat_id", "")).strip()
            if beat_id:
                out.append(beat_id)
    return out


def _validate_story_bible_contract(raw: dict, timeline: dict) -> None:
    beats = [row for row in raw.get("lyric_beats", []) if isinstance(row, dict)]
    actual_ids = [str(row.get("beat_id", "")).strip() for row in beats]
    expected_ids = _expected_timeline_beat_ids(timeline)
    if len(actual_ids) != len(expected_ids):
        raise RuntimeError(f"story bible beat count mismatch: expected={len(expected_ids)} actual={len(actual_ids)}")
    if any(not beat_id for beat_id in actual_ids):
        raise RuntimeError("story bible beat contract mismatch: blank beat_id present")
    if actual_ids != expected_ids:
        raise RuntimeError(
            "story bible beat contract mismatch: expected ids must match lyric timeline exactly; "
            f"expected={','.join(expected_ids[:8])}; actual={','.join(actual_ids[:8])}"
        )


def _visual_mv_policy_digest(policy: dict) -> str:
    if not isinstance(policy, dict):
        return ""
    return (
        f"visual_mv_mode={policy.get('visual_mv_mode', '')}; "
        f"subject_exposure={policy.get('subject_exposure', '')}; "
        f"motif_density={policy.get('motif_density', '')}; "
        f"graphic_event_density={policy.get('graphic_event_density', '')}; "
        f"environment_event_density={policy.get('environment_event_density', '')}; "
        f"visual_payoff_mode={policy.get('visual_payoff_mode', '')}; "
        f"reflection_usage={policy.get('reflection_usage', '')}; "
        f"palette_bias={policy.get('palette_bias', '')}; "
        f"motif_families={','.join(str(x).strip() for x in policy.get('motif_families', []) if str(x).strip())}; "
        f"preferred_compositions={','.join(str(x).strip() for x in policy.get('preferred_composition_families', []) if str(x).strip())}; "
        f"disfavored_compositions={','.join(str(x).strip() for x in policy.get('disfavored_composition_families', []) if str(x).strip())}"
    )
