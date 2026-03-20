from __future__ import annotations

import json

from ai_mv.core.contracts.prompt_normalize import normalize_visual_story_bible
from ai_mv.core.contracts.prompt_schema import visual_story_bible_schema
from ai_mv.core.visual_pipeline import location_grammar_digest
from ai_mv.infra.codex_cli_client import generate_structured


def build_visual_story_bible(config: dict, payload: dict) -> dict:
    timeline = payload["lyrics_timeline"]
    prompt = _planner_prompt(config, payload)
    raw = generate_structured(config, prompt, visual_story_bible_schema())
    try:
        _validate_story_bible_contract(raw, timeline)
        _validate_story_bible_language_contract(raw)
    except RuntimeError as exc:
        retry_prompt = _planner_retry_prompt(config, payload, str(exc))
        raw = generate_structured(config, retry_prompt, visual_story_bible_schema())
        _validate_story_bible_contract(raw, timeline)
        _validate_story_bible_language_contract(raw)
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
    return (
        "Write a lyric-first visual story bible for downstream image and video workflows. "
        "Return strict JSON only. No prose outside JSON. "
        "Required fields: hero_identity_lock,world_rules,recurring_location_families,forbidden_drift,lyric_beats,section_progression,repeat_escalation_rules. "
        "Follow the lyric timeline exactly. "
        "Create exactly one lyric_beats item for each lyric_timeline beat in the same order. "
        "Do not split, merge, invent, omit, or regroup beats. "
        "Reuse the provided beat_id values exactly once. "
        "Do not rewrite beat_id. Do not append line refs, brackets, punctuation, or suffixes to beat_id. "
        "Every output beat_id must exactly equal the source lyric timeline beat_id string. "
        "NO TEXT, NO TYPOGRAPHY, NO WATERMARKS, NO LOGOS, NO SIGNAGE, NO UI OVERLAY. "
        "section_progression must cover every section in order. "
        "Every lyric_beats item must also include symbolic_image,motif_object,edit_device,prompt_focus,space_event,composition_shape,palette_mode,character_render_mode. "
        "Differentiate sections clearly: verses should not read like choruses, bridges should interrupt or thin the flow, and the final chorus must feel like the visual peak. "
        "Differentiate adjacent lyric beats with a new image focus, action emphasis, framing commitment, palette shift, lighting shift, or location-family angle. "
        "Do not reduce every beat to the heroine performing in front of camera. Some beats should be object-led, space-led, or graphic-led when the profile supports it. "
        "Backgrounds must stay graphic and planar rather than photographic; prefer flat architecture blocks, blank signage panels, cut-paper shadow shapes, and simplified poster depth over realistic station or street rendering. "
        "symbolic_image should be a higher-level metaphor or visual symbol derived from the lyric, not just a restatement of literal_image. "
        "motif_object should name one repeatable object, texture, symbol, or visual token that can recur across sections. "
        "edit_device should describe the visual event or editorial device that gives the beat MV energy, such as silhouette hold, match flash, rhythm cut, graphic smear, space drop-out, object reveal, offset crop jolt, icon hold, or reflection split. "
        "prompt_focus must choose the visual subject priority for the beat: heroine, object, space, or graphic. "
        "space_event must already be a short natural-English background-motion clause with a finite verb that can be reused in WAN, such as the corridor opens and snaps back, background neon lights flicker rapidly, the city lights streak past, or the window world folds inward. "
        "Do not write space_event as a noun phrase, taxonomy label, or abstract metadata fragment. "
        "composition_shape must already be a short natural-English framing phrase that can be copied directly into a render prompt, such as a small figure against stacked flat bands, a diagonal walking line, or an off-center silhouette near dark glass. Do not output taxonomy labels, shorthand tags, or internal category names. "
        "camera_commitment must already be a short natural-English camera phrase that can be copied directly into a render prompt, such as an extreme low-angle dynamic shot, a tight off-center close-up, or a wide off-center frame from the left. camera_commitment must describe camera or shot language and must not repeat composition_shape. Do not output labels or compressed metadata. "
        "palette_mode should define the beat color system in short direct natural-English terms such as bubblegum pink and aqua cyan with deep navy, mint green and hot pink with violet shadow, coral pink and lavender purple with blue-black, or aqua cyan and magenta with indigo. Avoid red-black editorial palettes and white-silver bloom. "
        "character_render_mode should define how the heroine is drawn in a direct natural-English phrase, such as sharp almond eyes with thick hair shapes, a long-limbed fashion figure, or a small full-body figure at the edge of frame. Avoid chibi or mascot-like render modes. "
        "Do not let all beats collapse into the same lane, crosswalk, or reflection treatment if the lyrics turn. "
        "Do not overuse split-screen, diptych, mirrored-face, doubled-subject, centered two-body, bilateral balance, centered low hero staging, or static cover-pose close crops across adjacent beats; reserve them for isolated impact beats rather than the default graphic solution. "
        "Avoid composition phrases that imply tight face crop, close heroine crop, near-face framing, stable-subject poster lock, emblematic badge-like portrait, balanced-around-her staging, anchor-point staging, centered sparse-negative-space staging, centered floating-object staging, or paired-figure default staging; favor one living character in space, a side turn, a walking line, or a small figure against graphic planes. "
        "Preserve recurring environment families, but rotate how they are used: threshold, passage, lane, reflection surface, curb edge, sheltered edge, or open crossing should not all be treated the same way. "
        "If reflection usage is selected_only, mirror, double, or reflection imagery may recur as a motif but should appear as isolated impact beats rather than dominating the default composition language. "
        "If motif families are provided, recur them across the timeline as small city-object anchors instead of inventing unrelated props every section. "
        "When sections repeat, keep continuity but escalate the treatment through clearer geography, stronger palette contrast, cleaner action intent, or a more decisive camera commitment. "
        "Use location_family, palette_hint, lighting_hint, camera_commitment, composition_shape, and palette_mode as real differentiators, not decorative synonyms. "
        "Favor concrete drawable phrases over poetic abstraction. symbolic_image may stay metaphorical, but composition_shape, camera_commitment, motif_object, palette_mode, and character_render_mode must be visually direct, natural English, and directly renderable. "
        "If the visual MV mode is symbolic_edit or bga_event, favor image-events that feel editable and rhythm-sensitive: silhouette changes, object recurrence, graphic overlays implied in composition, decisive spatial transformations, and repeatable visual hits timed to musical turns. "
        "Final chorus payoff should follow the profile visual payoff mode: not always a face close-up, sometimes a motif-system peak or world-system peak. For system-peak payoffs, avoid centered heroine framing, close-crop heroine phrasing, near-face phrasing, anchor-point staging, receding corridor language, and stable-subject locks; prefer off-center world pressure, moving figure language, stacked flat bands, or motif-system resolution. "
        f"Style contract={world.get('visual_style_contract', '')}; "
        f"World support={world.get('visual_intent', '')}; Story world={world.get('story_world', '')}; "
        f"Action vocabulary={world.get('action_vocabulary', '')}; Payoff support={world.get('payoff_style', '')}; "
        f"Heroine invariants={world.get('heroine_invariants', '')}; World invariants={world.get('world_invariants', '')}; "
        f"Close-up policy={world.get('closeup_policy', '')}; Motion policy={world.get('motion_policy', '')}; "
        f"Visual MV policy={_visual_mv_policy_digest(policy)}; "
        f"Forbidden drift={negative.get('visual_negative', '')}; Avoid={negative.get('mv_avoid', '')}; "
        f"Location grammar={location_grammar_digest(config)}; "
        f"Lyric beat manifest={_timeline_beat_digest(timeline)}; "
        f"Lyric timeline={_timeline_digest(timeline)}."
    )


def _planner_retry_prompt(config: dict, payload: dict, error: str) -> str:
    timeline = payload["lyrics_timeline"]
    base = _planner_prompt(config, payload)
    return (
        f"{base} "
        "Retry the visual story bible. "
        f"Validation error={error}. "
        "Fix the JSON by preserving the lyric timeline beat ids exactly. "
        "Do not append bracketed line refs or any extra characters to beat_id. "
        "composition_shape and camera_commitment must be plain natural-English prompt phrases, not taxonomy labels or shorthand tags. camera_commitment must describe camera or shot language and must not repeat composition_shape. "
        f"Expected beat ids JSON={json.dumps(_expected_timeline_beat_ids(timeline), ensure_ascii=False, separators=(',', ':'))}."
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


_BANNED_STORY_LABELS = {
    "asymmetrical poster crop",
    "editorial three-quarter turn",
    "mid-step lane cut",
    "low horizon silhouette",
    "diagonal lane cut",
    "floating object field",
    "isolated small figure",
    "sticker-cluster layout",
    "offset silhouette crop",
    "single-profile reflection trace",
}


def _validate_story_bible_language_contract(raw: dict) -> None:
    beats = [row for row in raw.get("lyric_beats", []) if isinstance(row, dict)]
    for idx, row in enumerate(beats, start=1):
        for field in ("composition_shape", "camera_commitment", "palette_mode", "character_render_mode", "space_event"):
            text = str(row.get(field, "")).strip()
            if not text:
                raise RuntimeError(f"story bible language contract mismatch: blank {field} at beat {idx}")
            low = text.lower()
            if low in _BANNED_STORY_LABELS:
                raise RuntimeError(f"story bible language contract mismatch: {field} is still a taxonomy label at beat {idx}: {text}")
            if any(mark in text for mark in ("[", "]", "|", ";")):
                raise RuntimeError(f"story bible language contract mismatch: {field} contains metadata punctuation at beat {idx}: {text}")
        camera = str(row.get("camera_commitment", "")).strip().lower()
        composition = str(row.get("composition_shape", "")).strip().lower()
        if camera == composition:
            raise RuntimeError(f"story bible language contract mismatch: camera_commitment duplicates composition_shape at beat {idx}: {camera}")
        if not any(token in camera for token in ("shot", "angle", "frame", "close-up", "close up", "wide", "profile", "low-angle", "low angle", "dutch", "overhead")):
            raise RuntimeError(f"story bible language contract mismatch: camera_commitment is not camera language at beat {idx}: {camera}")
        space = str(row.get("space_event", "")).strip().lower()
        if space.split(" ", 1)[0].endswith("ing"):
            raise RuntimeError(f"story bible language contract mismatch: space_event is still gerund-led at beat {idx}: {space}")


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
