from __future__ import annotations

from ai_mv.core.workflow_prompt_contracts import compact_prompt_clause, workflow_negative_prompt
from ai_mv.engines.common.clip_timing import read_max_clip_sec
from ai_mv.engines.visual_story_bible.brief_views import compact_section_atoms, compact_world_atoms
from ai_mv.utils.text_utils import parse_target

def build_wan_plan(config: dict, payload: dict) -> dict:
    fps = parse_target(config["video"]["target"])[2]
    clips = [_route_to_clip(item, payload.get("flux2_ref_images", []), fps) for item in payload["clip_routes"]]
    clips = _chain_clip_starts(clips)
    if not clips:
        raise RuntimeError("WAN clips empty")
    _enforce_clip_cap(config, clips, fps)
    rendered = [_apply_prompt(clip, payload["visual_story_bible"]) for clip in clips]
    return {"clips": rendered}


def _planner_prompt(config: dict, payload: dict, clips: list[dict], carry: str) -> str:
    world = compact_world_atoms(payload["visual_story_bible"])
    clip_ids = _clip_ids(clips)
    summary = _clip_summary(clips)
    carry_clause = f"carry={carry}; " if carry else ""
    style = compact_prompt_clause(str(world.get("visual_style_contract", "")).strip(), 12)
    heroine = compact_prompt_clause(str(world.get("hero_identity", "")).strip(), 8)
    world_rules = compact_prompt_clause(str(world.get("world_rules", "")).strip(), 10)
    return (
        "deterministic wan composer; "
        "compose short motion-first prompts for the workflow positive and negative text fields; "
        f"{carry_clause}style={style}; hero={heroine}; world={world_rules}; clip_ids={clip_ids}; clips={summary}."
    )


def _route_to_clip(item: dict, ref_images: list[dict], fps: int) -> dict:
    ref_map = {_ref_chain_key(row): row for row in ref_images if isinstance(row, dict)}
    use_ref = bool(item.get("use_ref", False))
    ref_row = ref_map.get(_ref_chain_key(item))
    start = str(item["anchor"])
    end = str(item["anchor"])
    if use_ref:
        if ref_row is None:
            raise RuntimeError(f"WAN missing ref-assisted clip: {item['shot_id']}")
        start = str(ref_row["start"])
        end = str(ref_row["end"])
    frames = max(_frame_floor(fps), int(round(float(item["duration_sec"]) * fps)))
    return {
        "shot_id": str(item["shot_id"]),
        "start": start,
        "end": end,
        "fps": fps,
        "frames": int(frames),
        "section_name": str(item.get("section_name", "section")),
        "section_label": str(item.get("section_label", item.get("section_name", "section"))),
        "shot_type": str(item.get("shot_type", "CHAR_MASTER")),
        "is_chorus": bool(item.get("is_chorus", False)),
        "camera_language": str(item.get("camera_language", "")),
        "pose_delta": str(item.get("pose_delta", "")),
        "emotion": str(item.get("emotion", "")),
        "scene_detail": str(item.get("scene_detail", "")),
        "motion_hint": str(item.get("motion_hint", "")),
        "workflow_motion_clause": str(item.get("workflow_motion_clause", "")),
        "space_relation": str(item.get("space_relation", "")),
        "start_frame": dict(item.get("start_frame", {})),
        "end_frame": dict(item.get("end_frame", {})),
        "kinetic_transition": str(item.get("kinetic_transition", "")),
        "lighting_fx": str(item.get("lighting_fx", "")),
        "kinetic_intensity": str(item.get("kinetic_intensity", "")),
        "location_family": str(item.get("location_family", "")),
        "symbolic_image": str(item.get("symbolic_image", "")),
        "motif_object": str(item.get("motif_object", "")),
        "edit_device": str(item.get("edit_device", "")),
        "prompt_focus": str(item.get("prompt_focus", "")),
        "space_event": str(item.get("space_event", "")),
        "composition_shape": str(item.get("composition_shape", "")),
        "palette_mode": str(item.get("palette_mode", "")),
        "character_render_mode": str(item.get("character_render_mode", "")),
        "face_exposure_level": str(item.get("face_exposure_level", "")),
        "heroine_visibility": str(item.get("heroine_visibility", "")),
        "continuity_priority": str(item.get("continuity_priority", "")),
        "wardrobe_read": str(item.get("wardrobe_read", "")),
        "continuity_lock": str(item.get("continuity_lock", "")),
        "route_reason": str(item.get("route_reason", "")),
        "use_ref": use_ref,
        "clip_index": int(item.get("clip_index", 1)),
        "clip_count": int(item.get("clip_count", 1)),
        "timeline_index": int(item.get("timeline_index", 0)),
        "chain_key": _ref_chain_key(item),
    }


def _chain_clip_starts(clips: list[dict]) -> list[dict]:
    out: list[dict] = []
    prev_end_path = ""
    prev_clip: dict | None = None
    for clip in clips:
        item = dict(clip)
        if prev_end_path and not _chain_break(item, prev_clip):
            item["start"] = prev_end_path
            item["start_source"] = "previous_end"
            item["prev_chain_key"] = str(prev_clip.get("chain_key", "")) if isinstance(prev_clip, dict) else ""
        else:
            item["start_source"] = "rendered_start"
            item["prev_chain_key"] = ""
        prev_end_path = str(item["end"])
        prev_clip = item
        out.append(item)
    return out


def _chain_break(clip: dict, prev_clip: dict | None) -> bool:
    if not isinstance(prev_clip, dict):
        return True
    if str(clip.get("kinetic_transition", "")).strip().lower() == "smash_reframe":
        return True
    if _starts_new_major_section(clip, prev_clip) and int(clip.get("clip_index", 1)) <= 1:
        return True
    return False


def _starts_new_major_section(clip: dict, prev_clip: dict) -> bool:
    current = _section_token(clip)
    previous = _section_token(prev_clip)
    if not current or current == previous:
        return False
    return _is_major_reset_section(current)


def _section_token(clip: dict) -> str:
    return str(clip.get("section_name", clip.get("section_label", ""))).strip().lower()


def _is_major_reset_section(section: str) -> bool:
    sec = str(section).strip().lower()
    return "verse" in sec or sec == "chorus"


def _ref_chain_key(row: dict) -> str:
    return f"{str(row.get('shot_id', '')).strip()}:{int(row.get('clip_index', 1))}"


def _enforce_clip_cap(config: dict, clips: list[dict], fps: int) -> None:
    sec = read_max_clip_sec(config)
    max_frames = max(_frame_floor(fps), int(round(sec * fps)))
    for clip in clips:
        frames = int(clip["frames"])
        if frames > max_frames:
            raise RuntimeError(f"WAN clip exceeds cap: {clip['shot_id']} frames={frames} cap={max_frames}")


def _wan_planner_batch_size(config: dict, count: int) -> int:
    render = config.get("render", {}) if isinstance(config, dict) else {}
    raw = render.get("wan_planner_batch_size", 20) if isinstance(render, dict) else 20
    try:
        n = int(raw)
    except Exception:
        n = 20
    return max(1, min(max(1, count), n))


def _carry_hint(rows: list[dict]) -> str:
    if not rows:
        return ""
    last = rows[-1]
    return " | ".join(
        part
        for part in (
            str(last.get("subject_motion", "")).strip(),
            str(last.get("camera_relation", "")).strip(),
            str(last.get("environment_detail", "")).strip(),
        )
        if part
    )[:120]


def _clip_ids(clips: list[dict]) -> str:
    ids = [str(clip["shot_id"]) for clip in clips]
    if not ids:
        raise RuntimeError("WAN clips missing for planner prompt")
    return ", ".join(ids)


def _clip_summary(clips: list[dict]) -> str:
    return ", ".join(_clip_summary_row(c) for c in clips)


def _clip_summary_row(clip: dict) -> str:
    sid = str(clip["shot_id"])
    relation = _normalize_wan_relation(str(clip.get("space_relation", "")).strip()) or "space stays stable"
    motion = str(clip.get("kinetic_transition", "")).strip() or str(clip.get("motion_hint", "")).strip() or "impact move"
    label = str(clip.get("section_label", clip.get("section_name", "section")))
    return f"{sid}({label}|{motion}|{relation})"


def _apply_prompt(clip: dict, brief: dict) -> dict:
    section = _beat_atoms(brief, clip)
    subject_motion = _subject_motion(clip, section)
    camera_relation = _camera_relation(clip, section)
    environment_detail = _environment_detail(clip, section, brief)
    row = {
        "subject_motion": subject_motion,
        "camera_relation": camera_relation,
        "environment_detail": environment_detail,
        "negative_prompt": _negative_prompt(clip, brief),
        "energy": _energy_policy(clip, _suggested_energy(clip, section)),
    }
    out = dict(clip)
    out["subject_motion"] = row["subject_motion"]
    out["camera_relation"] = row["camera_relation"]
    out["environment_detail"] = row["environment_detail"]
    out["positive_prompt"] = _compose_positive_prompt(row)
    out["negative_prompt"] = row["negative_prompt"]
    out["energy"] = row["energy"]
    return out


def _subject_motion(clip: dict, section: dict) -> str:
    phase = _clip_phase(clip)
    action = _planned_motion_clause(clip)
    focus = str(clip.get("prompt_focus", "")).strip().lower()
    motif = str(clip.get("motif_object", "")).strip()
    device = str(clip.get("edit_device", "")).strip()
    if focus == "object":
        prefix = {
            "establish": f"The {motif or 'motif object'} leads the move",
            "resolve": f"The {motif or 'motif object'} lands the move",
            "advance": f"The {motif or 'motif object'} carries the move",
        }.get(phase, f"The {motif or 'motif object'} holds the move")
        return _sentence_clause(_join_motion(prefix, action))
    if focus == "space":
        space_event = str(clip.get("space_event", "")).strip()
        prefix = {
            "establish": f"The space {space_event or 'opens'}",
            "resolve": f"The space {space_event or 'settles'}",
            "advance": f"The space {space_event or 'shifts'}",
        }.get(phase, f"The space {space_event or 'holds'}")
        return _sentence_clause(_join_motion(prefix, action))
    if focus == "graphic":
        prefix = {
            "establish": f"The {device or 'graphic hit'} triggers the move",
            "resolve": f"The {device or 'graphic hit'} lands the move",
            "advance": f"The {device or 'graphic hit'} carries the move",
        }.get(phase, f"The {device or 'graphic hit'} holds the move")
        return _sentence_clause(_join_motion(prefix, action))
    if phase == "establish":
        return _sentence_clause(_join_motion("She sets the move", action))
    if phase == "resolve":
        return _sentence_clause(_join_motion("She lands the move", action))
    if phase == "advance":
        return _sentence_clause(_join_motion("She carries the move", action))
    return _sentence_clause(_single_motion_sentence(action))


def _camera_relation(clip: dict, section: dict) -> str:
    camera = str(clip.get("camera_language", "")).strip()
    composition = str(clip.get("composition_shape", "")).strip()
    focus = str(clip.get("prompt_focus", "")).strip().lower()
    kinetic_transition = str(clip.get("kinetic_transition", "")).strip().lower()
    intensity = str(clip.get("kinetic_intensity", "")).strip().lower()
    escalation = str(section.get("escalation_level", "")).strip().lower()
    if focus in {"object", "space", "graphic"} and composition:
        return _motion_camera_phrase(_normalize_wan_composition(composition), camera)
    if camera:
        return _motion_camera_phrase(composition, camera)
    if kinetic_transition == "whip_pan_left":
        return "whips hard left across her line"
    if kinetic_transition == "whip_pan_right":
        return "whips hard right across her line"
    if kinetic_transition == "snap_zoom_in":
        return "snap zooms straight into her face"
    if kinetic_transition == "snap_zoom_out":
        return "snaps back out of the frame"
    if kinetic_transition == "crash_push_in":
        return "crashes straight toward her on impact"
    if kinetic_transition == "smash_reframe":
        return "smash reframes to a new axis mid-beat"
    if kinetic_transition == "strobe_jump":
        return "jumps forward through strobe hits"
    if kinetic_transition == "match_cut_pose":
        return "cuts on pose impact without easing"
    if intensity in {"high", "max"}:
        return "drives fast with no soft drift"
    if escalation == "interrupt":
        return "cuts sideways and locks on impact"
    if escalation == "residue":
        return "jerks back and leaves a hard after-image"
    return "stays aggressive and close to impact"


def _environment_detail(clip: dict, section: dict, brief: dict) -> str:
    palette = str(clip.get("palette_mode", "")).strip() or str(section.get("palette_hint", "")).strip()
    lighting = str(section.get("lighting_hint", "")).strip()
    location = (
        str(clip.get("location_family", "")).strip()
        or str(section.get("location_family", "")).strip()
        or str(section.get("location_anchor", "")).strip()
        or str(clip.get("scene_detail", "")).strip()
    )
    world = compact_world_atoms(brief)
    world_rules = str(world.get("world_rules", "")).strip()
    lighting_fx = str(clip.get("lighting_fx", "")).strip()
    composition = str(clip.get("composition_shape", "")).strip()
    render_mode = str(clip.get("character_render_mode", "")).strip()
    focus = str(clip.get("prompt_focus", "")).strip().lower()
    if focus in {"object", "space", "graphic"}:
        render_mode = ""
    location_text = _normalize_wan_location(location)
    mood = lighting_fx or lighting or world_rules
    if focus == "object":
        text = ", ".join(part for part in (f"{location_text} drift behind it", palette, mood) if part)
        return compact_prompt_clause(text, 12)
    if focus == "space":
        text = ", ".join(part for part in (f"{location_text} slide in flat layers", palette, mood) if part)
        return compact_prompt_clause(text, 12)
    if focus == "graphic":
        text = ", ".join(part for part in (f"{location_text} pulse behind the hit", palette, mood) if part)
        return compact_prompt_clause(text, 12)
    text = ", ".join(part for part in (f"{location_text} move behind her", palette, render_mode, mood) if part)
    return compact_prompt_clause(text, 14)


def _negative_prompt(clip: dict, brief: dict) -> str:
    world = compact_world_atoms(brief)
    relation = str(clip.get("space_relation", "")).strip().lower()
    extra: list[str] = []
    extra.extend(
        [
            "3d render",
            "photorealistic",
            "volumetric lighting",
            "soft shading",
            "morphing",
            "melting limbs",
            "warping limbs",
            "melted guitar shape",
            "slow motion",
            "smooth transitions",
        ]
    )
    if "glass" in relation:
        extra.append("warped reflections")
    if bool(clip.get("use_ref", False)):
        extra.append("identity drift")
    if str(clip.get("prompt_focus", "")).strip().lower() in {"object", "space", "graphic"}:
        extra.extend(
            [
                "generic live-action portrait",
                "photorealistic skin texture",
                "photographic background depth",
                "realistic architecture detail",
                "soft atmospheric bloom",
            ]
        )
    if str(clip.get("face_exposure_level", "")).strip().lower() in {"direct", "soft"}:
        extra.extend(["different person", "age drift", "hairstyle drift", "wardrobe swap", "duplicate subject"])
    if str(clip.get("camera_language", "")).strip().lower() in {"locked", "lockoff", "static"}:
        extra.extend(["camera movement", "zooming", "panning"])
    if "world_rules" in world and "night" in str(world.get("world_rules", "")).lower():
        extra.append("daylight mismatch")
    return workflow_negative_prompt(extra)


def _suggested_energy(clip: dict, section: dict) -> str:
    escalation = str(section.get("escalation_level", "")).strip().lower()
    if escalation == "payoff":
        return "high"
    if escalation in {"interrupt", "residue"}:
        return "low"
    return "normal"


def _normalize_wan_composition(composition: str) -> str:
    text = str(composition).strip()
    if not text:
        return text
    lowered = text.lower()
    replacements = (
        ("centered", "off-center"),
        ("near face", "near upper-body turn"),
        ("close heroine crop", "off-center upper-body turn"),
        ("stable subject", "moving figure"),
        ("balanced around her", "off-center around city planes"),
        ("runway", "moving"),
        ("poster crop", "moving poster crop"),
        ("low horizon silhouette", "off-center low horizon moving figure"),
        ("isolated small figure", "small moving figure in open negative space"),
        ("offset silhouette crop", "off-center moving silhouette"),
        ("floating object field", "floating object field with off-center figure"),
    )
    out = text
    for old, new in replacements:
        if old in lowered:
            out = out.replace(old, new).replace(old.title(), new)
            lowered = out.lower()
    return out


def _normalize_wan_location(location: str) -> str:
    text = str(location).strip()
    if not text:
        return text
    replacements = (
        ("street", "street blocks"),
        ("corridor", "passage blocks"),
        ("lane", "lane blocks"),
    )
    out = text
    lowered = out.lower()
    for old, new in replacements:
        if old in lowered:
            out = out.replace(old, new).replace(old.title(), new)
            lowered = out.lower()
    return out


def _normalize_wan_relation(relation: str) -> str:
    text = str(relation).strip()
    if not text:
        return text
    replacements = (
        ("receding toward the center", "stacked in flat layers"),
        ("receding in layers", "stacked in flat layers"),
        ("deep center", "stacked bands"),
        ("converge toward center", "stack in flat bands"),
        ("receding city planes", "stacked city planes"),
        ("receding city plane blocks", "stacked city plane blocks"),
        ("small heroine centered low against broad moving city bands", "small heroine off-center against broad moving city bands"),
        ("heroine centered in a widened street corridor", "heroine off-center in a widened street corridor"),
        ("heroine centered in a widened street compressed passage blocks", "heroine off-center in widened street passage blocks"),
        ("near face with the world condensed behind her", "near upper-body turn with the world compressed into flat bands"),
        ("close heroine crop against a layered blue field and receding city plane blocks", "off-center upper-body turn against a layered blue field and stacked city plane blocks"),
        ("close heroine crop against a layered blue field and receding city planes", "off-center upper-body turn against a layered blue field and stacked city planes"),
        ("close heroine crop against a shallow field of night geometry", "off-center upper-body turn against a shallow field of night geometry"),
        ("curving exterior ribbon enclosing a stable subject", "curving exterior ribbon crossing a moving figure"),
        ("fully embedded in the city grid with the frame balanced around her", "fully embedded in the city grid with off-center city pressure around her"),
        ("tiny circle centered in open negative space", "tiny circle off-center in open negative space"),
        ("lights arranged around center, block feels complete", "lights arranged across the block, the block feels complete"),
        ("two figures aligned across the crossing, city receding", "one figure crossing with an offset echo, city stacked behind"),
        ("city receding", "city stacked behind"),
        ("graphic corridor receding behind a single red point near center", "graphic corridor stacked in flat bands behind an off-center red point"),
        ("broad city space with the heroine reduced to a small anchored point", "broad city space with the heroine reduced to a small off-center figure"),
        ("dense layered field where the motifs converge around a small anchor point", "dense layered field where the motifs converge around a small off-center figure"),
        ("object-led foreground window with the route receding behind it", "object-led foreground window with the route stacked behind it"),
        ("small anchored point", "small off-center figure"),
        ("small anchor point", "small off-center figure"),
        ("near center", "off-center"),
        ("foreground dominant", "foreground left"),
        ("occupying most of the frame edge", "touching the frame edge"),
        ("street plane", "flat street plane"),
    )
    out = text
    lowered = out.lower()
    for old, new in replacements:
        if old in lowered:
            out = out.replace(old, new).replace(old.title(), new)
            lowered = out.lower()
    return out


def _compose_positive_prompt(row: dict) -> str:
    subject_motion = _sentence(_clause(row.get("subject_motion", "")))
    second_sentence = _compose_second_sentence(
        _clause(row.get("camera_relation", "")),
        _clause(row.get("environment_detail", "")),
    )
    if not subject_motion or not second_sentence:
        raise RuntimeError("empty composed WAN prompt")
    return f"{subject_motion} {second_sentence}".strip()


def _clause(text: object) -> str:
    return " ".join(str(text).strip().rstrip(". ").split())


def _sentence(text: str) -> str:
    cleaned = str(text).strip().rstrip(". ")
    if not cleaned:
        return ""
    return f"{_capitalize_first(cleaned)}."


def _sentence_clause(text: str) -> str:
    cleaned = " ".join(str(text).strip().split())
    if cleaned.lower().startswith("she she "):
        cleaned = cleaned[4:]
    return cleaned


def _compose_second_sentence(camera_relation: str, environment_detail: str) -> str:
    if environment_detail and _camera_relation_is_weak(camera_relation):
        return _sentence(environment_detail)
    if not camera_relation:
        return ""
    relation = _clean_relation(camera_relation)
    if environment_detail:
        return _sentence(f"{relation}, while {_lowercase_first(environment_detail)}")
    return _sentence(relation)


def _clean_relation(text: str) -> str:
    cleaned = str(text).strip()
    if not cleaned:
        return ""
    cleaned = _naturalize_relation(cleaned)
    low = cleaned.lower()
    if low.startswith("the camera "):
        return cleaned
    if low.startswith("camera "):
        return cleaned
    return _capitalize_first(cleaned)


def _capitalize_first(text: str) -> str:
    cleaned = str(text)
    if not cleaned:
        return ""
    return cleaned[:1].upper() + cleaned[1:]


def _lowercase_first(text: str) -> str:
    cleaned = str(text).strip()
    if not cleaned:
        return ""
    return cleaned[:1].lower() + cleaned[1:]


def _camera_relation_is_weak(text: str) -> bool:
    low = str(text).strip().lower()
    if not low:
        return True
    technical_subjects = (
        "the frame ",
        "the track ",
        "the side track ",
        "the follow ",
    )
    if low.startswith(technical_subjects):
        return True
    dynamic = ("whip", "snap", "crash", "slam", "smash", "jump", "track", "tracks", "push", "pushes", "pull", "pulls", "glide", "glides")
    if not any(word in low for word in dynamic):
        return True
    weak_starts = ("a gentle retreat", "a steady retreat", "the glide", "the backward tracking", "the arc")
    return low.startswith(weak_starts)


def _motion_camera_phrase(composition: str, camera: str) -> str:
    comp = compact_prompt_clause(_normalize_wan_composition(composition), 8)
    cam = compact_prompt_clause(camera, 8)
    combined = ", ".join(part for part in (comp, cam) if part)
    low = combined.lower()
    replacements = (
        ("off-center moving silhouette", "camera tracks an off-center silhouette"),
        ("off-center low horizon moving figure", "camera skims a low off-center figure"),
        ("small moving figure in open negative space", "camera keeps a small figure drifting through open space"),
        ("floating object field with off-center figure", "camera moves through a floating object field past an off-center figure"),
        ("moving poster crop", "camera pushes through a moving poster crop"),
        ("off-center", "camera stays off-center"),
    )
    out = combined
    for source, target in replacements:
        if source in low:
            out = out.replace(source, target).replace(source.title(), target)
            low = out.lower()
    return compact_prompt_clause(out, 14)


def _naturalize_relation(text: str) -> str:
    cleaned = " ".join(str(text).strip().split())
    replacements = (
        ("keeps her centered", "stays centered on her"),
        ("keeps close to her", "stays close to her"),
        ("keeps her aligned", "stays aligned with her"),
        ("gives her space", "gives her a little space"),
        ("stays before her", "stays just ahead of her"),
        ("stays before her.", "stays just ahead of her."),
    )
    out = cleaned
    low = out.lower()
    for source, target in replacements:
        src_low = source.lower()
        if src_low in low:
            idx = low.index(src_low)
            out = out[:idx] + target + out[idx + len(source) :]
            low = out.lower()
    return out


def _energy_policy(clip: dict, suggested: str) -> str:
    sec = _section_token(clip)
    label = _section_label(clip)
    if "final chorus" in label:
        return "high"
    if "chorus 2" in label:
        return "high" if suggested == "high" else "normal"
    if sec == "chorus" or sec.startswith("chorus_"):
        return "high" if suggested == "high" else "normal"
    if sec in {"bridge", "outro"}:
        return "low" if suggested == "low" else "normal"
    if suggested in {"low", "normal", "high"}:
        return suggested
    return "normal"


def _section_token(clip: dict) -> str:
    return str(clip.get("section_name", "")).strip().lower()


def _section_label(clip: dict) -> str:
    return str(clip.get("section_label", clip.get("section_name", ""))).strip().lower()


def _clip_phase_from_id(shot_id: str) -> str:
    if "_C" not in shot_id:
        return "single"
    try:
        suffix = int(shot_id.rsplit("_C", 1)[1])
    except Exception:
        return "single"
    if suffix <= 1:
        return "establish"
    return "advance"


def _clip_phase(clip: dict) -> str:
    count = int(clip.get("clip_count", 1))
    index = int(clip.get("clip_index", 1))
    if count <= 1:
        return "single"
    if index <= 1:
        return "establish"
    if index >= count:
        return "resolve"
    return "advance"


def _frame_floor(fps: int) -> int:
    return max(1, int(round(max(1, fps) * 0.25)))


def _trim_words(text: str, max_words: int) -> str:
    words = [word for word in str(text).replace(",", " ,").split() if word]
    return " ".join(words[: max_words]).replace(" ,", ",").strip(" ,")


def _beat_atoms(brief: dict, clip: dict) -> dict:
    beat_id = str(clip.get("lyric_beat_id", "")).strip()
    if beat_id:
        for beat in brief.get("lyric_beats", []):
            if not isinstance(beat, dict):
                continue
            if str(beat.get("beat_id", "")).strip() == beat_id:
                return dict(beat)
    return compact_section_atoms(brief, str(clip.get("section_name", "")), beat_id)


def _workflow_axis(section: dict, clip: dict) -> str:
    raw = compact_prompt_clause(section.get("motion_axis", ""), 4)
    if raw and "," not in raw and "." not in raw:
        return raw
    return _kinetic_axis(clip)


def _kinetic_axis(clip: dict) -> str:
    raw = compact_prompt_clause(str(clip.get("motion_hint", "")), 4)
    if raw and "," not in raw and "." not in raw:
        return raw
    raw = compact_prompt_clause(str(clip.get("scene_detail", "")), 4)
    if raw and "," not in raw and "." not in raw:
        return raw
    raw = compact_prompt_clause(str(clip.get("space_relation", "")), 6)
    if raw:
        return raw
    return "impact move"


def _join_motion(prefix: str, action: str) -> str:
    text = str(action).strip()
    if not text:
        return str(prefix).strip()
    first = text.split(" ", 1)[0].lower()
    if first in {"staying", "holding", "remaining", "keeping"}:
        linker = "while"
    elif first.endswith("ing"):
        linker = "by"
    elif first in {"under", "over", "through", "into", "across", "inside", "between", "before", "after", "while", "as"}:
        linker = "as"
    elif first in {"a", "an", "the"}:
        linker = "through"
    else:
        linker = "with"
    return f"{str(prefix).strip()} {linker} {text}".strip()


def _single_motion_sentence(action: str) -> str:
    text = str(action).strip()
    if not text:
        return "She holds the beat"
    first = text.split(" ", 1)[0].lower()
    if first in {"staying", "holding", "remaining", "keeping"}:
        lead_map = {
            "staying": "stays",
            "holding": "holds",
            "remaining": "remains",
            "keeping": "keeps",
        }
        rest = text.split(" ", 1)[1] if " " in text else ""
        return f"She {lead_map.get(first, first)} {rest}".strip()
    if first.endswith("ing"):
        return f"She follows through by {text}"
    if first in {"a", "an", "the"}:
        return f"She hits through {text}"
    return f"She {text}"


def _planned_motion_clause(clip: dict) -> str:
    text = " ".join(str(clip.get("workflow_motion_clause", "")).strip().rstrip(". ").split())
    if not text:
        raise RuntimeError(f"workflow_motion_clause missing for wan shot: {clip.get('shot_id', '')}")
    if text.lower().startswith("she "):
        text = text[4:].strip()
    return text
