from __future__ import annotations

import json

from ai_mv.core.contracts.prompt_normalize import normalize_shot_timeline
from ai_mv.core.contracts.prompt_schema import KINETIC_INTENSITIES, KINETIC_TRANSITIONS, SHOT_TYPES, shot_timeline_schema
from ai_mv.core.profile_policy import resolve_profile_policy
from ai_mv.core.visual_pipeline import attach_tti_metadata
from ai_mv.infra.codex_cli_client import generate_structured


def build_tti_plan(config: dict, payload: dict) -> dict:
    story_bible = payload["visual_story_bible"]
    lyrics_timeline = payload["lyrics_timeline"]
    spec = _generate_tti_spec(config, payload, story_bible)
    plan = normalize_shot_timeline(spec, story_bible.get("lyric_beats", []))
    shots = _assign_story_metadata(plan["shots"], lyrics_timeline, story_bible)
    return {"master_anchor": plan["master_anchor"], "shots": shots}


def build_tti_preview_prompt(config: dict, payload: dict) -> str:
    return _planner_prompt(config, payload)


def _planner_prompt(config: dict, payload: dict) -> str:
    story_bible = payload["visual_story_bible"]
    timeline = payload["lyrics_timeline"]
    policy = story_bible.get("resolved_profile_policy", resolve_profile_policy(config)) if isinstance(story_bible, dict) else resolve_profile_policy(config)
    beat_manifest = _tti_beat_manifest(story_bible)
    beat_count = len(beat_manifest)
    beat_rows = _tti_beat_rows(story_bible)
    return (
        "Write a shot timeline for downstream Flux and video workflows. "
        "Return strict JSON only with shape {\"master_anchor\":{...},\"shots\":[...]}. No prose outside JSON. "
        "Create exactly one shot item for every lyric beat in order. "
        f"Exact shot count contract: return exactly {beat_count} shots. "
        "The shots array length must equal the lyric beat count exactly; do not add extra shots, do not omit shots. "
        "Use each lyric_beat_id exactly once and preserve the exact manifest order. "
        "Treat the source lyric beats as a locked one-to-one transform. "
        "Do not split a lyric beat into multiple shots. Do not merge beats. Do not invent extra shots. Do not omit shots. "
        "master_anchor prompt_text must be the final render-facing master character anchor prompt. "
        "master_anchor prompt_text must follow the same exact formula as shot prompt_text: [Base Style] + [Subject/Action] + [Background] + [Camera/Framing]. "
        "master_anchor prompt_text should be exactly four short sentences and should establish a definitive anime character anchor, not a photo-real portrait. "
        "master_anchor is not an event shot. It is a clean character master reference image for downstream ref generation. "
        "master_anchor should show the heroine as a clear full-body or strong three-quarter figure with a stable silhouette and a very readable character design. "
        "Prioritize a high-quality graphic anime character design with a strong silhouette, simplified facial features, thick clean outlines, and flat confident color blocking. "
        "Treat master_anchor like a poster-friendly symbolic character design, not a realistic anime portrait and not a plain model sheet. "
        "The heroine should read as cute, iconic, and immediately recognizable at first glance. "
        "Prefer a simplified charming face, large graphic eyes, a clean fringe or long ponytail silhouette, and one memorable outfit accent. "
        "Even though the pose is grounded and neutral, the character should still feel deliberately designed, slightly stylized, and strongly graphic rather than generic. "
        "Aim for a lovable symbolic anime mascot-poster heroine rather than a severe fashion illustration. "
        "Allow slightly stylized proportions such as a slightly larger head and a compact readable body if that helps the character feel cuter and more iconic. "
        "Avoid generic gymwear, blank hoodie-sweats silhouettes, plain mannequin posture, or a dull default station snapshot. "
        "Keep the pose grounded and neutral, usually full-body or strong three-quarter, and keep the background simple and supportive rather than dramatic. "
        "For master_anchor, strongly prefer a clean white or very pale off-white non-photographic backdrop with minimal floor shadow or a faint graphic grounding line. "
        "Do not use a realistic station, street, room, or environmental background in master_anchor. "
        "The background should feel like a clean graphic character presentation sheet, not a real photographed location. "
        "Do not let the master anchor become realistic, live-action, painterly, doll-like, or a chaotic action frame. "
        "Do not make the character too detailed, over-rendered, or fashion-editorial. "
        "Good master_anchor example: 'A 2D graphic anime character illustration with flat cel shading, thick clean outlines, and bold simple color blocks. The heroine stands in a clear full-body pose with a cute simplified face, large dark eyes, a long dark ponytail, and an orange-and-cream outfit with one strong black accent. The background is a clean white non-photographic backdrop with only a faint grounding shadow. Full-body graphic character reference shot.' "
        "Another good master_anchor example: 'A 2D symbolic anime character illustration with flat colors, chunky outlines, and a poster-like silhouette. The heroine holds a calm full-body pose with a rounded cute face, straight bangs, a long dark ponytail, and a simple memorable outfit built from two or three dominant colors. The background is a pale off-white presentation backdrop with no environmental scene detail. Full-body anchor shot.' "
        "Bad master_anchor example: 'A realistic young woman stands in a cinematic station portrait with soft skin and camera depth. The background is a real city at night. Moody portrait shot.' "
        "Another bad master_anchor example: 'A plain anime girl in generic dark sweats stands stiffly in front of a blank station wall. The background is empty and the design has no memorable accent. Full-body reference shot.' "
        "Every shot must include lyric_beat_id,shot_type,prompt_text,camera_language,pose_delta,emotion,scene_detail,motion_hint,workflow_motion_clause,space_relation,edit_role,continuity_lock,scene_change_level,anchor_strategy,continuity_basis,clip_count,start_frame,end_frame,kinetic_transition,lighting_fx,kinetic_intensity. "
        "prompt_text must be the final render-facing TTI prompt and must follow this exact formula: [Base Style] + [Subject/Action] + [Background] + [Camera/Framing]. "
        "Write prompt_text as natural English sentences only, never labels or plus signs. "
        "prompt_text should be exactly four short sentences in this order: "
        "a base-style sentence, then a subject or action sentence, then a background sentence, then a camera or framing sentence. "
        "The background sentence should begin with 'The background is'. "
        "The camera sentence should be a clean phrase like 'Extreme low-angle dynamic shot' or 'Tight close-up'. "
        "Do not use composition taxonomy words such as crop, tableau, composition, layout, or silhouette composition inside prompt_text. "
        "Make every prompt_text look like a direct image-generation prompt a human would type by hand. "
        "Prefer concrete subject nouns and physical actions over abstract descriptions. "
        "Avoid hedging words and weak modifiers such as slightly, somewhat, gently, calmly, softly, vaguely, or quietly unless the beat absolutely requires restraint. "
        "Even restrained beats should still feel visually intentional and image-worthy, not passive or half-described. "
        "Prefer sharper action verbs such as steps, presses, braces, turns, plants, lifts, reaches, slides, cuts, leans in, or snaps into place. "
        "Prefer strong camera phrases such as 'Extreme low-angle dynamic shot', 'Wide side-tracking shot', 'Tight close-up', 'Locked-off frontal close-up', or 'Off-center medium shot'. "
        "Prefer drawable background phrases such as 'The background is a non-photographic planar ticket gate with wet floor reflections' or 'The background is a flat train-window band with narrow streetlight streaks'. "
        "Do not write vague filler such as atmospheric presence, emotional energy, symbolic mood, visual treatment, or graphic feeling. "
        "Do not write compressed metadata fragments. Write complete natural-English sentences only. "
        "Good subject or action sentence example: 'The heroine steps through the ticket gate and turns her chin toward the platform lights.' "
        "Another good subject or action sentence example: 'The heroine presses one hand to the train window and lifts her gaze as light bands cross her face.' "
        "Bad subject or action sentence example: 'The heroine carries the emotional presence of the night.' "
        "Bad subject or action sentence example: 'The heroine leans slightly while the mood remains soft.' "
        "Good background sentence example: 'The background is a non-photographic planar ticket gate with wet floor reflections and narrow light bands.' "
        "Another good background sentence example: 'The background is a planar station curb with puddle rings, painted safety stripes, and narrow neon reflections.' "
        "Bad background sentence example: 'The background is a symbolic atmosphere of city emotion.' "
        "Good camera sentence example: 'Wide side-tracking shot.' "
        "Bad camera sentence example: 'Dynamic visual composition with cinematic energy.' "
        "When prompt_focus is object or space, still write a strong image prompt, but let the object or location event lead the scene instead of a generic heroine portrait. "
        "For object-led beats, prefer concrete props such as ticket stubs, umbrella tips, phone lights, puddle rings, gate arms, or vending cans. "
        "For space-led beats, prefer concrete motion events such as train windows sliding, gate arms opening, light bands crossing glass, curb reflections widening, or signs flickering. "
        "For graphic-led beats, prefer a bold visual hit such as crossing light bands, doubled shadows in glass, stacked sign strips, or split reflections. "
        "Good object-led prompt example: 'A 2D graphic anime illustration with flat cel shading and thick clean outlines. A folded note loosens in her hand while gate lights ripple across the wet floor. The background is a non-photographic planar concourse with reflected signal bands and rain-dark tiles. Tight hand detail shot.' "
        "Good space-led prompt example: 'A 2D graphic anime illustration with flat cel shading and thick clean outlines. Train window bands slide past and cut the platform reflection into thin strips. The background is a non-photographic planar station block with wet glass and narrow neon streaks. Wide side-tracking shot.' "
        "Good graphic-led prompt example: 'A 2D graphic anime illustration with flat cel shading and thick clean outlines. Stacked sign bands and crossing light strips lock into one reflected frame. The background is a non-photographic planar window wall with doubled neon bars and wet reflections. Tight reflective shot.' "
        "Keep neighboring shots sharply differentiated. If one shot is a walking beat, the next shot should usually shift to an object hit, a place event, a reflection event, or a different camera distance. "
        "Avoid returning to the same safe heroine coverage across adjacent beats. Do not repeat the same walking pose, same medium framing, or same window shot unless the source beat explicitly repeats it. "
        "For intro, bridge, transition, and outro material, default to WORLD_EVENT, SYMBOLIC_INSERT, GRAPHIC_EVENT, ENV_TRANSITION, DETAIL_INSERT, or TRANSITIONAL_ABSTRACT before choosing heroine coverage. "
        "For final payoff material, prefer WORLD_EVENT, GRAPHIC_EVENT, or SYMBOLIC_INSERT unless the beat explicitly demands a face payoff. "
        "In final-chorus and outro payoff material, a face-led shot should be rare; default instead to a world resolution, motif lockup, object hit, or graphic system peak. "
        "Good final payoff prompt example: 'A 2D graphic anime illustration with flat cel shading and thick clean outlines. Gate arms open in sequence while the heroine stays small beneath the lights. The background is a non-photographic planar concourse with stacked sign bands and rain-dark floor reflections. Wide elevated tracking shot.' "
        "Bad final payoff prompt example: 'A 2D graphic anime illustration with flat cel shading and thick clean outlines. The heroine looks into the camera and holds the final feeling. The background is a symbolic atmosphere of closure. Tight emotional close-up.' "
        "Avoid direct-face, centered close, straight-on portrait, and frontal beauty coverage unless the beat explicitly names a face reaction. "
        "Do not choose EMOTION_CLOSE or centered close coverage as a safe fallback. Prefer side profile, partial figure, reflected figure, hand detail, object interaction, or world response. "
        "If a beat can be expressed through a hand, a prop, a reflection, a gate, a window band, a sign strip, a puddle ring, or a floor light, write that beat instead of a face-led prompt. "
        "Good non-face prompt example: 'A 2D graphic anime illustration with flat cel shading and thick clean outlines. Her hand loosens on the folded note as gate lights ripple across the floor. The background is a non-photographic planar ticket concourse with wet tile reflections and thin signal bands. Tight hand detail shot.' "
        "Bad face-fallback prompt example: 'A 2D graphic anime illustration with flat cel shading and thick clean outlines. The heroine stares ahead in a centered close-up while the city feeling surrounds her. The background is a symbolic atmosphere of closure. Tight emotional close-up.' "
        "Avoid two-shot, shared center-line shot, and tight close-up as safe fallback solutions. "
        "If two figures appear, keep them small inside a broader world event instead of making a face-led two-shot the default. "
        "Bad two-shot fallback example: 'A 2D graphic anime illustration with flat cel shading and thick clean outlines. The heroine stands with the other person in a shared center-line shot. The background is a generic station atmosphere. Platform-edge two-shot.' "
        "Good world-led alternative example: 'A 2D graphic anime illustration with flat cel shading and thick clean outlines. Gate bars and passing window bands align while both figures stay small beneath the station lights. The background is a non-photographic planar concourse with stacked sign bands and wet floor reflections. Wide architectural shot.' "
        "If a beat can be told through gate bars, passing windows, sign bands, puddle rings, floor reflections, vending glow, or curb lines, choose those motifs before adding another heroine-led frame. "
        "Do not default object-led, space-led, or graphic-led beats to a centered heroine portrait unless the beat explicitly demands it. "
        "In this project, conventional heroine coverage is not the default. "
        "Only choose CHAR_MASTER, PERF_WIDE, or EMOTION_CLOSE when the beat clearly needs direct heroine readability or a specific payoff. "
        "Prefer WORLD_EVENT, SYMBOLIC_INSERT, GRAPHIC_EVENT, ENV_TRANSITION, DETAIL_INSERT, or TRANSITIONAL_ABSTRACT whenever the beat can be told through an object, a place event, or a graphic hit. "
        "When two shot choices seem equally plausible, choose WORLD_EVENT, SYMBOLIC_INSERT, or GRAPHIC_EVENT before choosing heroine coverage. "
        "For repeated chorus material, do not simply return to heroine coverage; escalate motif density, graphic impact, or world-system behavior instead. "
        "Treat repeated hooks and choruses as chances to increase world behavior, object recurrence, and graphic interference rather than adding more heroine readability. "
        "For final payoff beats, prefer a world-system peak, a repeating motif lockup, or a graphic event before choosing a face-driven payoff. "
        "Good object-led example: 'A 2D graphic anime illustration with flat cel shading and thick clean outlines. A ticket stub warms in her hand as she folds it once. The background is a non-photographic planar station wall with thin reflected light bands. Tight hand detail shot.' "
        "Good space-led example: 'A 2D graphic anime illustration with flat cel shading and thick clean outlines. Train window bands slide past while the heroine stays small near the platform edge. The background is a non-photographic planar station block with wet glass and narrow neon streaks. Wide side-tracking shot.' "
        "Good graphic-led example: 'A 2D graphic anime illustration with flat cel shading and thick clean outlines. Crossing light bands cut across her reflection as she turns into the glass. The background is a non-photographic planar window wall with doubled neon strips. Tight reflective close-up.' "
        "Another good world payoff example: 'A 2D graphic anime illustration with flat cel shading and thick clean outlines. Gate arms open in sequence while the heroine stays small beneath the lights. The background is a non-photographic planar concourse with stacked sign bands and rain-dark floor reflections. Wide elevated tracking shot.' "
        "Another good object-led insert example: 'A 2D graphic anime illustration with flat cel shading and thick clean outlines. A phone light shakes once and throws a bright wedge across the wet curb. The background is a non-photographic planar sidewalk strip with narrow reflected neon bands. Tight hand detail shot.' "
        "Example prompt_text: 'A 2D graphic anime illustration with flat cel shading and thick clean outlines. The heroine holds an electric guitar high above her head, ready to strike. The background is a non-photographic planar cyberpunk alley with flat neon signs. Extreme low-angle dynamic shot.' "
        "Another valid example: 'A 2D graphic anime illustration with flat cel shading and thick clean outlines. The heroine pauses over the wet reflection line as she steps past it. The background is a non-photographic planar ticket gate with rain-dark pavement and narrow light bands. Low reflective shot.' "
        "scene_change_level must be one of hold,evolve,shift,reset. "
        "anchor_strategy must be one of reuse_anchor,refine_anchor,new_anchor. "
        "continuity_basis must be one of heroine,motif,world,none. "
        "TTI creates new scene anchors and ref refines an existing anchor for continuity. "
        "Use anchor_strategy and continuity_basis seriously. "
        "If a beat is face-sensitive, profile-sensitive, reflection-overlap sensitive, gaze-exchange sensitive, or otherwise depends on the heroine's exact identity, choose anchor_strategy='refine_anchor' and continuity_basis='heroine'. "
        "If a beat shows a tight profile close-up, a reflected face overlap, an intimate two-figure exchange, or a direct heroine reaction that must preserve identity, do not choose new_anchor unless the world changes drastically. "
        "If a beat is primarily about an object recurrence or a world event, prefer continuity_basis='motif' or continuity_basis='world'. "
        "Use scene_change_level='hold' or 'evolve' for identity-sensitive continuity beats, not 'reset', unless the world genuinely resets. "
        "Good continuity-routing example: a reflected face overlap or a profile close-up should use refine_anchor with heroine continuity. "
        "Bad continuity-routing example: a face-sensitive profile beat marked as new_anchor with continuity_basis='none'. "
        "pose_delta should be the changed pose or action phrase that ref can reuse directly, for example 'fiercely smashing the guitar onto the ground, bending her knees'. "
        "workflow_motion_clause should be a full WAN action clause beginning with a finite verb phrase that fits after 'The girl', for example 'swings the guitar down with extreme force'. "
        "camera_language should be a clean camera or framing phrase such as 'Extreme low-angle dynamic shot'. "
        "scene_detail and space_relation should be plain drawable natural English. "
        "Use the story bible and lyric beat as the source of truth. "
        "Make nearby beats meaningfully different in framing, action, or visual state. "
        "Honor story-bible prompt_focus, edit_device, symbolic_image, motif_object, space_event, and composition_shape when deciding shot_type. "
        "If prompt_focus is object, space, or graphic, do not collapse back into a default heroine close-up. "
        "Use shot_type as a storytelling choice, not a default. "
        f"Allowed shot types={', '.join(SHOT_TYPES)}. "
        f"Allowed kinetic transitions={', '.join(KINETIC_TRANSITIONS)}. "
        f"Allowed kinetic intensities={', '.join(KINETIC_INTENSITIES)}. "
        "Honor the profile policy when choosing shot types and face exposure. "
        f"Profile policy={_policy_digest(policy)}. "
        f"Shot count manifest={'; '.join(beat_manifest)}. "
        f"Source beat JSON={json.dumps(beat_rows, ensure_ascii=True)}. "
        f"Story bible={_story_bible_digest(story_bible)}. "
        f"Lyric timeline={_timeline_digest(timeline)}."
    )


def _generate_tti_spec(config: dict, payload: dict, story_bible: dict, attempts: int = 1) -> dict:
    prompt = _planner_prompt(config, payload)
    expected_ids = _expected_lyric_beat_ids(story_bible)
    try:
        spec = generate_structured(config, prompt, shot_timeline_schema(), attempts=1)
    except TypeError:
        spec = generate_structured(config, prompt, shot_timeline_schema())
    _validate_tti_spec_contract(spec, expected_ids)
    return spec


def _validate_tti_spec_contract(spec: dict, expected_ids: list[str]) -> None:
    shots = [row for row in spec.get("shots", []) if isinstance(row, dict)]
    actual_ids = [str(row.get("lyric_beat_id", "")).strip() for row in shots]
    if len(shots) != len(expected_ids):
        raise RuntimeError(f"shot count mismatch: expected={len(expected_ids)} actual={len(shots)}")
    if any(not beat_id for beat_id in actual_ids):
        raise RuntimeError("shot contract mismatch: blank lyric_beat_id present")
    if actual_ids != expected_ids:
        missing = [beat_id for beat_id in expected_ids if beat_id not in actual_ids]
        extra = [beat_id for beat_id in actual_ids if beat_id not in set(expected_ids)]
        detail = []
        if missing:
            detail.append(f"missing={','.join(missing[:6])}")
        if extra:
            detail.append(f"extra={','.join(extra[:6])}")
        if not detail:
            detail.append("order mismatch")
        raise RuntimeError("shot contract mismatch: " + "; ".join(detail))


def _expected_lyric_beat_ids(story_bible: dict) -> list[str]:
    return [
        str(beat.get("beat_id", "")).strip()
        for beat in story_bible.get("lyric_beats", [])
        if isinstance(beat, dict) and str(beat.get("beat_id", "")).strip()
    ]


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


def _assign_story_metadata(shots: list[dict], timeline: dict, story_bible: dict) -> list[dict]:
    policy = story_bible.get("resolved_profile_policy", resolve_profile_policy({})) if isinstance(story_bible, dict) else resolve_profile_policy({})
    face_defaults = policy.get("face_exposure_defaults", {}) if isinstance(policy, dict) else {}
    beat_map = {
        str(beat.get("beat_id", "")).strip(): beat
        for beat in story_bible.get("lyric_beats", [])
        if isinstance(beat, dict)
    }
    section_bounds = _section_bounds(timeline)
    out: list[dict] = []
    for idx, shot in enumerate(shots, start=1):
        beat = beat_map[str(shot["lyric_beat_id"])]
        bounds = section_bounds.get(str(beat.get("beat_id", "")), {"start_sec": 0.0, "end_sec": 4.0})
        item = dict(shot)
        item["duration_sec"] = round(max(0.001, float(bounds["end_sec"]) - float(bounds["start_sec"])), 3)
        item["scene_detail"] = str(item.get("scene_detail", "")).strip()
        item["motion_hint"] = str(item.get("motion_hint", "")).strip()
        item["emotion"] = str(item.get("emotion", "")).strip()
        item["continuity_anchor"] = str(beat.get("continuity_anchor", "")).strip()
        item["scene_change_level"] = str(item.get("scene_change_level", "")).strip().lower()
        item["anchor_strategy"] = str(item.get("anchor_strategy", "")).strip().lower()
        item["continuity_basis"] = str(item.get("continuity_basis", "")).strip().lower()
        item["planner_edit_role"] = str(item.get("edit_role", "")).strip()
        item["edit_role"] = _canonical_edit_role(item.get("edit_role", ""), beat.get("payoff_role", ""))
        item["mv_function"] = _mv_function(item["edit_role"])
        item["transition_role"] = _transition_role(item["edit_role"])
        item["line_refs"] = list(beat.get("line_refs", []))
        item["literal_image"] = str(beat.get("literal_image", "")).strip()
        item["symbolic_image"] = str(beat.get("symbolic_image", "")).strip()
        item["motif_object"] = str(beat.get("motif_object", "")).strip()
        item["edit_device"] = str(beat.get("edit_device", "")).strip()
        item["prompt_focus"] = str(beat.get("prompt_focus", "heroine")).strip() or "heroine"
        item["space_event"] = str(beat.get("space_event", "")).strip()
        item["composition_shape"] = str(beat.get("composition_shape", "")).strip()
        item["palette_mode"] = str(beat.get("palette_mode", "")).strip()
        item["character_render_mode"] = str(beat.get("character_render_mode", "")).strip()
        item = attach_tti_metadata(item, item["section_name"], item["section_label"])
        item["location_family"] = str(beat.get("location_family", "")).strip()
        item["face_exposure_level"] = _face_exposure_level(item, face_defaults, policy)
        item["heroine_visibility"] = _heroine_visibility(item)
        item["continuity_priority"] = _continuity_priority(item, policy)
        item["wardrobe_read"] = _wardrobe_read(item, policy)
        item["prompt_text"] = str(item.get("prompt_text", "")).strip()
        item["seed"] = 10_000 + idx * 97 + int(item.get("hero_frame_score", 1)) * 13
        out.append(item)
    return out


def _face_exposure_level(shot: dict, defaults: dict[str, str], policy: dict) -> str:
    shot_type = str(shot.get("shot_type", "")).strip().upper()
    mv_function = str(shot.get("mv_function", "")).strip().lower()
    label = str(shot.get("section_label", shot.get("section_name", ""))).strip()
    focus = str(shot.get("prompt_focus", "")).strip().lower()
    direct_face_sections = {str(x).strip() for x in policy.get("direct_face_sections", [])} if isinstance(policy, dict) else set()
    if shot_type in defaults:
        base = str(defaults.get(shot_type, "")).strip().lower()
        if shot_type == "EMOTION_CLOSE" and mv_function == "payoff" and label in direct_face_sections:
            return "direct"
        if base:
            return base
    if shot_type in {"DETAIL_INSERT", "SYMBOLIC_INSERT", "RHYTHM_DETAIL"} or focus == "object":
        return "hidden"
    if shot_type in {"ENV_TRANSITION", "WORLD_EVENT", "TRANSITIONAL_ABSTRACT"} or focus == "space":
        return "partial"
    if shot_type == "GRAPHIC_EVENT" or focus == "graphic":
        return "partial"
    if shot_type == "EMOTION_CLOSE":
        return "direct" if mv_function == "payoff" else "soft"
    if shot_type == "CHAR_MASTER":
        return "soft"
    return "partial"


def _heroine_visibility(shot: dict) -> str:
    shot_type = str(shot.get("shot_type", "")).strip().upper()
    focus = str(shot.get("prompt_focus", "")).strip().lower()
    if shot_type in {"DETAIL_INSERT", "SYMBOLIC_INSERT", "RHYTHM_DETAIL"} or focus == "object":
        return "implied"
    if shot_type in {"ENV_TRANSITION", "WORLD_EVENT", "TRANSITIONAL_ABSTRACT", "GRAPHIC_EVENT"} or focus in {"space", "graphic"}:
        return "partial"
    return "clear"


def _continuity_priority(shot: dict, policy: dict) -> str:
    continuity_mode = str(policy.get("continuity_mode", "")).strip().lower() if isinstance(policy, dict) else ""
    if continuity_mode == "same_heroine" and str(shot.get("face_exposure_level", "")).strip().lower() in {"direct", "soft"}:
        return "high"
    if str(shot.get("consistency_need", "")).strip().lower() == "high":
        return "high"
    if str(shot.get("shot_priority", "")).strip().lower() == "hero":
        return "high"
    if str(shot.get("mv_function", "")).strip().lower() in {"payoff", "interrupt", "establish"}:
        return "medium"
    return "low"


def _wardrobe_read(shot: dict, policy: dict) -> str:
    shot_type = str(shot.get("shot_type", "")).strip().upper()
    focus = str(shot.get("prompt_focus", "")).strip().lower()
    visual_mode = str(policy.get("visual_mode", "")).strip().lower() if isinstance(policy, dict) else ""
    if visual_mode == "environment_first" and shot_type != "CHAR_MASTER":
        return "low"
    if focus in {"object", "space", "graphic"}:
        return "low"
    if shot_type in {"CHAR_MASTER", "PERF_WIDE"}:
        return "high"
    if shot_type == "EMOTION_CLOSE":
        return "medium"
    return "low"


def _section_bounds(timeline: dict) -> dict[str, dict]:
    out: dict[str, dict] = {}
    for section in timeline.get("sections", []):
        for beat in section.get("lyric_beats", []):
            out[str(beat.get("beat_id", ""))] = {
                "start_sec": float(beat.get("start_sec", section.get("start_sec", 0.0))),
                "end_sec": float(beat.get("end_sec", section.get("end_sec", 0.0))),
            }
    return out


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


def _mv_function(edit_role: str) -> str:
    role = str(edit_role).strip().lower()
    mapping = {
        "entry": "establish",
        "develop": "coverage",
        "release": "payoff",
        "hold": "lift",
        "interrupt": "interrupt",
        "residue": "residue",
    }
    return mapping.get(role, "coverage")


def _transition_role(edit_role: str) -> str:
    role = str(edit_role).strip().lower()
    if role in {"entry", "interrupt", "residue"}:
        return role
    if role == "release":
        return "arrival"
    if role == "hold":
        return "build"
    return "carry"


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


def _canonical_edit_role(raw_edit_role: object, payoff_role: object) -> str:
    payoff = str(payoff_role).strip().lower()
    if payoff in {"entry", "interrupt", "residue", "develop", "hold", "release"}:
        return payoff
    if payoff in {"peak", "payoff", "arrival"}:
        return "release"
    text = str(raw_edit_role).strip().lower()
    if not text:
        return "develop"
    if any(token in text for token in ("climax", "release", "payoff", "arrives", "arrival")):
        return "release"
    if any(token in text for token in ("entry", "opening", "introduce", "sets the atmosphere", "introduce the emotional premise")):
        return "entry"
    if any(token in text for token in ("interrupt", "break", "rupture")):
        return "interrupt"
    if any(token in text for token in ("residue", "outro", "after-image", "linger", "resolve out")):
        return "residue"
    if any(token in text for token in ("hold", "lift", "build", "sustain")):
        return "hold"
    return "develop"
