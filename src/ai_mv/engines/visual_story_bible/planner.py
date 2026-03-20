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
        "space_event should describe how the environment changes, opens, compresses, repeats, fragments, mirrors, or resolves through the beat. "
        "composition_shape should define the graphic layout in short renderable terms such as asymmetrical poster crop, editorial three-quarter turn, mid-step lane cut, low horizon silhouette, diagonal lane cut, floating object field, isolated small figure, sticker-cluster layout, offset silhouette crop, or single-profile reflection trace. "
        "palette_mode should define the beat color system in short direct terms such as bubblegum pink and aqua cyan with deep navy, mint green and hot pink with violet shadow, coral pink and lavender purple with blue-black, or aqua cyan and magenta with indigo. Avoid red-black editorial palettes and white-silver bloom. "
        "character_render_mode should define how the heroine is drawn in the beat, such as sharp almond eyes, silhouette-first body, flat fashion figure, long-limbed fashion figure, or secondary tiny figure. Avoid chibi or mascot-like render modes. "
        "Do not let all beats collapse into the same lane, crosswalk, or reflection treatment if the lyrics turn. "
        "Do not overuse split-screen, diptych, mirrored-face, doubled-subject, centered two-body, bilateral balance, centered low hero staging, or static cover-pose close crops across adjacent beats; reserve them for isolated impact beats rather than the default graphic solution. "
        "Avoid composition phrases that imply tight face crop, close heroine crop, near-face framing, stable-subject poster lock, emblematic badge-like portrait, balanced-around-her staging, anchor-point staging, or paired-figure default staging; favor one living character in space, a side turn, a walking line, or a small figure against graphic planes. "
        "Preserve recurring environment families, but rotate how they are used: threshold, passage, lane, reflection surface, curb edge, sheltered edge, or open crossing should not all be treated the same way. "
        "If reflection usage is selected_only, mirror, double, or reflection imagery may recur as a motif but should appear as isolated impact beats rather than dominating the default composition language. "
        "If motif families are provided, recur them across the timeline as small city-object anchors instead of inventing unrelated props every section. "
        "When sections repeat, keep continuity but escalate the treatment through clearer geography, stronger palette contrast, cleaner action intent, or a more decisive camera commitment. "
        "Use location_family, palette_hint, lighting_hint, camera_commitment, composition_shape, and palette_mode as real differentiators, not decorative synonyms. "
        "Favor concrete drawable phrases over poetic abstraction. symbolic_image may stay metaphorical, but composition_shape, motif_object, palette_mode, and character_render_mode must be visually direct and renderable. "
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
