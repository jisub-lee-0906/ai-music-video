from __future__ import annotations

from ai_mv.core.contracts.prompt_normalize import normalize_wan_clips
from ai_mv.core.contracts.prompt_schema import wan_schema
from ai_mv.engines.common.clip_timing import read_max_clip_sec
from ai_mv.engines.visual_story_bible.brief_views import compact_section_atoms
from ai_mv.infra.codex_cli_client import generate_structured
from ai_mv.utils.text_utils import parse_target


def build_wan_plan(config: dict, payload: dict) -> dict:
    fps = parse_target(config["video"]["target"])[2]
    clips = [_route_to_clip(item, payload.get("flux2_ref_images", []), fps) for item in payload["clip_routes"]]
    clips = _chain_clip_starts(clips)
    if not clips:
        raise RuntimeError("WAN clips empty")
    _enforce_clip_cap(config, clips, fps)
    spec = _generate_wan_spec(config, payload, clips)
    keyed = normalize_wan_clips(spec.get("clips", []), clips)
    rendered = [_apply_llm_prompt(clip, keyed[str(clip["shot_id"])]) for clip in clips]
    return {"clips": rendered}


def _planner_prompt(config: dict, payload: dict, clips: list[dict], carry: str) -> str:
    clip_ids = _clip_ids(clips)
    summary = _clip_summary(payload.get("visual_story_bible", {}), clips)
    return (
        "Write WAN FLF2V prompts for start and end frames that are already fixed. "
        "Return strict JSON only with shape {\"clips\":[...]}. No prose outside JSON. "
        f"Return exactly {len(clips)} clips, one for each shot_id in the manifest order. "
        "Each clip must contain shot_id,positive_prompt,negative_prompt,subject_motion,camera_relation,environment_detail,energy. "
        "positive_prompt must follow this exact formula: [Camera Movement] + [Action Verbs] + [Background Motion]. "
        "Do not mention visual style, rendering style, cel shading, outlines, colors, or background design style in the positive prompt. "
        "camera_relation should be the first sentence of positive_prompt and must begin with the word 'Camera'. "
        "subject_motion should be the second sentence of positive_prompt and must begin with the words 'The girl'. "
        "environment_detail should be the third sentence of positive_prompt and must begin with the word 'Background'. "
        "Do not start positive prompt sentences with 'The camera', 'A heroine', 'The heroine', 'The symbol', or abstract subject labels. "
        "Use concrete motion verbs and physical scene changes only. "
        "Prefer motion verbs such as shakes, crashes, glides, tracks, pans, pushes, whips, swings, turns, darts, slides, opens, closes, widens, pulses, flickers, or drifts. "
        "Avoid vague verbs such as carries the mood, holds the atmosphere, keeps the energy, or remains inside the feeling. "
        "The girl sentence should describe what her body or face physically does. "
        "The background sentence should describe what a concrete element does, such as a gate opening, lights flickering, window bands sliding, puddle rings widening, or signs rotating. "
        "The background sentence must read like natural English after the word 'Background'. "
        "Do not write ungrammatical fragments such as 'Background the clock ticks'. "
        "Write patterns such as 'Background clock hands tick while the wet reflection strip trembles' or 'Background neon lights flicker rapidly'. "
        "Good background sentence examples: 'Background neon lights flicker rapidly', 'Background window bands slide across the glass', 'Background puddle rings widen under each step', or 'Background gate arms snap back in sequence'. "
        "Bad background sentence examples: 'Background the skyline lightens', 'Background a sign glow drifts', or 'Background the platform lamps hold steady'. "
        "Prefer plural or mass nouns after 'Background' such as lights, bands, rings, signs, reflections, gate arms, puddle ripples, or window streaks. "
        "Keep neighboring clips motion-distinct. Vary camera verbs across nearby clips, for example glide, whip, push, hold, track, crash, pan, drift, or lock. "
        "Do not reuse the same camera verb more than twice in a row unless the source clip summary explicitly repeats the same motion. "
        "Keep the girl sentence physically specific. Prefer one strong body action such as leans, turns, steps, raises, drags, braces, darts, or holds still. "
        "Do not write generic filler such as keeps her posture, stays in the frame, or carries the feeling unless a more physical action is impossible. "
        "Keep the background sentence eventful and specific. Prefer window bands sliding, sign lights flickering, puddle rings widening, gate arms snapping back, reflection strips splitting, or UI rings rotating. "
        "If the source beat is low-energy, the background sentence should still describe a subtle physical change, such as light bands drifting, reflection strips trembling, or window streaks narrowing. "
        "negative_prompt must be a suppression list of 3D or realism anti-tags, morphing or anatomy error anti-tags, and unwanted motion anti-tags. "
        "Write negative_prompt as a single comma-separated list of short lowercase tags only, not as full sentences. "
        "Do not use pronouns, verbs, helper phrases, or sentence grammar inside negative_prompt. "
        "Write items like '3d render', 'photorealistic', 'cgi', 'warped hands', 'extra limbs', 'static', 'slow motion', or 'smooth transitions'. "
        "Do not write items like 'it looks like a 3d render' or 'motion slows to a crawl'. "
        "Use finite natural English clauses, not labels or metadata fragments. "
        "Energy must be one of low, normal, high. "
        "Example positive_prompt: 'Camera shakes violently on impact. The girl swings the guitar down with extreme force. Background neon lights flicker rapidly.' "
        "Another valid example: 'Camera is completely locked off and static. The girl darts her eyes sharply to the left. Background holographic UI rings rotate clockwise.' "
        "Example negative_prompt: '3d render, photorealistic, volumetric lighting, soft shading, morphing, melting guitar, warping limbs, static, slow motion, smooth transitions'. "
        f"Shot manifest={clip_ids}. "
        f"Clip summary={summary}."
    )


def _generate_wan_spec(config: dict, payload: dict, clips: list[dict], attempts: int = 3) -> dict:
    prompt = _planner_prompt(config, payload, clips, "")
    expected_ids = [str(clip["shot_id"]) for clip in clips]
    current_prompt = prompt
    last_exc: Exception | None = None
    for attempt in range(1, max(1, int(attempts)) + 1):
        spec = generate_structured(config, current_prompt, wan_schema(), attempts=1)
        try:
            keyed = normalize_wan_clips(spec.get("clips", []), clips)
            for shot_id in expected_ids:
                row = keyed[shot_id]
                if row["positive_prompt"] != _compose_positive_prompt(
                    {
                        "camera_relation": row["camera_relation"],
                        "subject_motion": row["subject_motion"],
                        "environment_detail": row["environment_detail"],
                    }
                ):
                    raise RuntimeError(f"positive_prompt formula mismatch: {shot_id}")
            return spec
        except RuntimeError as exc:
            last_exc = exc
            if attempt >= attempts:
                raise
            actual_ids = [
                str(row.get("shot_id", "")).strip()
                for row in spec.get("clips", [])
                if isinstance(row, dict) and str(row.get("shot_id", "")).strip()
            ]
            current_prompt = (
                f"{prompt}\n\n"
                "Previous output failed validation. "
                f"Failure={exc}. "
                f"Expected shot_id order={', '.join(expected_ids)}. "
                f"Previous shot_id order={', '.join(actual_ids)}. "
                "Rewrite the JSON only and follow the exact positive prompt formula."
            )
    if last_exc is not None:
        raise last_exc
    raise RuntimeError("wan planner failed without validation error")


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


def _clip_ids(clips: list[dict]) -> str:
    ids = [str(clip["shot_id"]) for clip in clips]
    if not ids:
        raise RuntimeError("WAN clips missing for planner prompt")
    return ", ".join(ids)


def _clip_summary(brief: dict, clips: list[dict]) -> str:
    return ", ".join(_clip_summary_row(brief, c) for c in clips)


def _clip_summary_row(brief: dict, clip: dict) -> str:
    sid = str(clip["shot_id"])
    focus = str(clip.get("prompt_focus", "")).strip().lower() or "heroine"
    motion = str(clip.get("workflow_motion_clause", "")).strip() or "action move"
    camera = str(clip.get("camera_language", "")).strip() or "camera move"
    section = _beat_atoms(brief, clip)
    background = str(section.get("space_event", "")).strip() or str(clip.get("scene_detail", "")).strip() or "background motion"
    return f"{sid}({focus}|{motion}|{camera}|{background})"


def _apply_llm_prompt(clip: dict, row: dict) -> dict:
    out = dict(clip)
    out["subject_motion"] = str(row["subject_motion"])
    out["camera_relation"] = str(row["camera_relation"])
    out["environment_detail"] = str(row["environment_detail"])
    out["positive_prompt"] = str(row["positive_prompt"])
    out["negative_prompt"] = str(row["negative_prompt"])
    out["energy"] = str(row["energy"])
    return out


def _compose_positive_prompt(row: dict) -> str:
    parts = [
        _sentence(str(row.get("camera_relation", "")).strip()),
        _sentence(str(row.get("subject_motion", "")).strip()),
        _sentence(str(row.get("environment_detail", "")).strip()),
    ]
    text = " ".join(part for part in parts if part).strip()
    if not text:
        raise RuntimeError("empty composed WAN prompt")
    return text


def _sentence(text: str) -> str:
    cleaned = " ".join(str(text).strip().rstrip(". ").split())
    if not cleaned:
        return ""
    return f"{cleaned[:1].upper() + cleaned[1:]}."


def _frame_floor(fps: int) -> int:
    return max(1, int(round(max(1, fps) * 0.25)))


def _beat_atoms(brief: dict, clip: dict) -> dict:
    beat_id = str(clip.get("lyric_beat_id", "")).strip()
    if beat_id:
        for beat in brief.get("lyric_beats", []):
            if not isinstance(beat, dict):
                continue
            if str(beat.get("beat_id", "")).strip() == beat_id:
                return dict(beat)
    return compact_section_atoms(brief, str(clip.get("section_name", "")), beat_id)
