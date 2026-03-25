from __future__ import annotations

from ai_mv.engines.visual_story_bible.brief_views import compact_section_atoms


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
        "Do not begin the third sentence with 'Background the' or 'Background a'. Start with a plural or mass noun phrase instead, such as 'Background neon lights...', 'Background window bands...', 'Background puddle rings...', or 'Background reflection strips...'. "
        "Write patterns such as 'Background clock hands tick while the wet reflection strip trembles' or 'Background neon lights flicker rapidly'. "
        "Good background sentence examples: 'Background neon lights flicker rapidly', 'Background window bands slide across the glass', 'Background puddle rings widen under each step', or 'Background gate arms snap back in sequence'. "
        "Bad background sentence examples: 'Background the skyline lightens', 'Background a sign glow drifts', or 'Background the platform lamps hold steady'. "
        "Prefer plural or mass nouns after 'Background' such as lights, bands, rings, signs, reflections, gate arms, puddle ripples, or window streaks. "
        "Keep neighboring clips motion-distinct. Vary camera verbs across nearby clips, for example glide, whip, push, hold, track, crash, pan, drift, or lock. "
        "Do not reuse the same camera verb more than twice in a row unless the source clip summary explicitly repeats the same motion. "
        "Keep the girl sentence physically specific. Prefer one strong body action such as leans, turns, steps, raises, drags, braces, darts, or holds still. "
        "Do not write generic filler such as keeps her posture, stays in the frame, or carries the feeling unless a more physical action is impossible. "
        "Avoid weak girl sentences such as 'The girl remains still' unless a small but visible action follows, for example 'The girl remains still and lifts her eyes to the passing lights'. "
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


def _chain_break(clip: dict, prev_clip: dict | None) -> bool:
    if not isinstance(prev_clip, dict):
        return True
    if str(clip.get("kinetic_transition", "")).strip().lower() == "smash_reframe":
        return True
    if str(clip.get("scene_change_level", "")).strip().lower() == "reset":
        return True
    return False


def _ref_chain_key(row: dict) -> str:
    return f"{str(row.get('shot_id', '')).strip()}:{int(row.get('clip_index', 1))}"


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


def _beat_atoms(brief: dict, clip: dict) -> dict:
    beat_id = str(clip.get("lyric_beat_id", "")).strip()
    if beat_id:
        for beat in brief.get("lyric_beats", []):
            if not isinstance(beat, dict):
                continue
            if str(beat.get("beat_id", "")).strip() == beat_id:
                return dict(beat)
    return compact_section_atoms(brief, str(clip.get("section_name", "")), beat_id)
