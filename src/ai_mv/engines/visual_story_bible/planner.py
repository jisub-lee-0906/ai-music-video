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
        "Prefer concrete drawable nouns such as ticket gate, train window, curb line, puddle ring, vending machine, umbrella tip, lane paint, phone light, or sign glow. "
        "Prefer visible physical actions such as steps, turns, lifts, glances, taps, drags, opens, closes, widens, flickers, pulses, slides, or gathers. "
        "Avoid abstract filler such as presence, atmosphere, mood, energy, feeling, visual treatment, or symbolic essence when a concrete image can be named instead. "
        "camera_commitment should read like a shot instruction, for example 'Extreme low-angle dynamic shot', 'Tight close-up', 'Wide side-tracking shot', or 'Locked-off frontal close-up'. "
        "composition_shape should read like a simple framing idea, for example 'Off-center walking frame', 'Diagonal street composition', or 'Tight reflective close-up'. "
        "space_event should read like a drawable motion statement, for example 'The gate opens and snaps back', 'Narrow window reflections slide across the glass', or 'The puddle rings widen with each step'. "
        "Good visible_action example: 'She steps through the ticket gate and turns her chin toward the platform lights'. "
        "Bad visible_action example: 'Her presence deepens the emotional atmosphere of the city'. "
        "Good literal_image example: 'A blue train window streak crosses the glass and cuts her reflection in half'. "
        "Bad literal_image example: 'A symbolic feeling of distance appears in the night'. "
        "Good camera_commitment example: 'Wide side-tracking shot'. Bad camera_commitment example: 'Dynamic visual treatment with tension'. "
        "Good composition_shape example: 'Off-center walking frame'. Bad composition_shape example: 'Graphic layout of emotional contrast'. "
        "Good space_event example: 'Background gate arms open and snap back'. Bad space_event example: 'The environment becomes more intense'. "
        "For object-led beats, prefer a concrete prop and a concrete interaction, for example a ticket stub warming in her hand, an umbrella tip drawing a circle, or a phone light shaking in the dark. "
        "For space-led beats, prefer an actual place event, for example a train window sliding past, gate arms opening, puddle rings widening, sign glow flickering, or curb reflections stretching. "
        "For graphic-led beats, prefer a concrete visual hit, for example crossing reflected light, doubled shadows, stacked sign glow, or a split reflection across glass. "
        "Good object-led beat example: 'A folded note loosens in her hand while gate lights ripple across the wet floor'. "
        "Good space-led beat example: 'Train window reflections slide past and cut the platform reflection into narrow slices'. "
        "Good graphic-led beat example: 'Stacked sign glow and crossing reflected light lock into one mirrored frame'. "
        "Keep adjacent beats visibly different in at least two of these axes: subject, action, location event, camera distance, or motif object. "
        "If two nearby beats both mention the heroine, make one beat body-led and the other world-led or object-led so the sequence does not flatten into repeated heroine coverage. "
        "For repeated hooks, write a new visible action or world event every time instead of repeating the same walking or looking beat. "
        "In intro, bridge, transition, and outro sections, default to object-led, space-led, or graphic-led beats unless a lyric explicitly demands heroine coverage. "
        "Avoid defaulting every beat to heroine face, heroine walking, or heroine standing unless the lyric beat clearly demands that coverage. "
        "In this project, heroine-led beats are the minority and should be used only when the lyric beat clearly needs face, body, or a specific gesture. "
        "Most beats should instead be object-led, space-led, or graphic-led, especially in intros, transitions, repeated hooks, bridges, and final-system payoffs. "
        "When two candidate beat ideas feel equally valid, choose the object-led, space-led, or graphic-led option over the heroine-led option. "
        "Final payoff beats should prefer a world-system peak, a motif lockup, or a graphic event over a simple heroine close-up unless the lyric explicitly demands a face payoff. "
        "In final-chorus and outro payoff beats, face-led coverage should be exceptional and only used if the lyric explicitly names eyes, face, or a direct confession. "
        "For final payoff beats, prefer concrete world or object resolutions such as gate arms opening in sequence, train windows clearing, sign glow aligning, puddle rings merging, or a final reflected light narrowing into dark. "
        "Good final payoff example: 'Gate arms open in sequence while the heroine stays small beneath the station lights'. "
        "Bad final payoff example: 'She looks into the camera and holds the feeling of the ending'. "
        "Avoid direct-face, centered close, straight-on portrait, and frontal beauty coverage unless the lyric explicitly demands a face reaction. "
        "Avoid identity-sensitive heroine coverage as a default. Prefer profile, partial figure, reflected figure, small figure, object interaction, or world-response imagery instead. "
        "If a beat can be told through a hand, a prop, a reflection, a gate, a window, a sign band, or a floor reflection, choose that instead of a face-led beat. "
        "Good non-face beat example: 'Her hand loosens on the folded note while gate lights ripple across the wet floor'. "
        "Bad face-led fallback example: 'She stares ahead in a centered close-up while the city feeling surrounds her'. "
        "Avoid defaulting to a two-shot, a shared center-line shot, or a tight close-up when a world event, object hit, or graphic reflection can carry the same beat. "
        "Bad two-shot fallback example: 'She stands with the other person in a shared center-line two-shot'. "
        "Good world-led alternative example: 'Gate bars and passing window bands align while both figures stay small beneath the station lights'. "
        "If a section can be expressed through gate bars, passing windows, sign glow, puddle rings, floor reflections, vending glow, or curb edges, choose those motifs before adding new heroine coverage. "
        "Repeated hooks and choruses should be treated as opportunities for stronger world behavior, denser motif recurrence, and more graphic interference, not as opportunities for more heroine coverage. "
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
