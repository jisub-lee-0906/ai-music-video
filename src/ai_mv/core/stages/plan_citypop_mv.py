from __future__ import annotations

import math

from ai_mv.core.contracts.stage_io import StageInput, StageOutput

M1_TARGET_DURATION_MIN = 15.0
M1_TARGET_DURATION_MAX = 20.0
M1_MIN_SHOTS = 4
M1_MAX_SHOTS = 6


def run_plan_citypop_mv(stage_input: StageInput) -> StageOutput:
    payload = build_plan_preview_payload(stage_input.config, stage_input.payload)
    return StageOutput("plan_citypop_mv", "done", payload, [])


def build_plan_preview_payload(config: dict, payload: dict) -> dict:
    concept_text = str(payload.get("concept_text") or config.get("concept_text", "")).strip()
    audio_map = dict(payload.get("audio_map", {}))
    duration = float(audio_map.get("duration_sec", 16.0) or 16.0)
    citypop_bible = _citypop_bible()
    sections = _normalized_sections(audio_map, duration)
    shot_plan = _build_shot_plan(config, sections)
    render_plan = [_build_render_item(config, concept_text, citypop_bible, shot) for shot in shot_plan]
    return {
        "citypop_bible": citypop_bible,
        "shot_plan": shot_plan,
        "render_plan": render_plan,
        "workflow_inputs": {
            **dict(payload.get("workflow_inputs", {})),
            "plan": {
                "shot_count": len(shot_plan),
                "concept_text": concept_text,
                "section_count": len(sections),
                "music_section_count": len(sections),
            },
        },
    }


def _normalized_sections(audio_map: dict, duration_sec: float) -> list[dict]:
    rows = [row for row in audio_map.get("sections", []) if isinstance(row, dict)]
    normalized: list[dict] = []
    for idx, row in enumerate(rows, start=1):
        start_sec = max(0.0, min(_float(row.get("start_sec"), 0.0), float(duration_sec)))
        end_sec = max(start_sec, min(_float(row.get("end_sec"), 0.0), float(duration_sec)))
        if end_sec <= start_sec:
            continue
        section_type = _canonical_section_type(row)
        normalized.append(
            {
                "index": idx,
                "section_name": str(row.get("label") or row.get("name") or row.get("section_name") or section_type.upper()).strip(),
                "section_type": section_type,
                "start_sec": start_sec,
                "end_sec": end_sec,
                "duration_sec": round(end_sec - start_sec, 3),
            }
        )
    if not normalized:
        return _fallback_sections(duration_sec)
    normalized.sort(key=lambda row: (float(row["start_sec"]), float(row["end_sec"]), int(row["index"])))
    for idx, row in enumerate(normalized, start=1):
        row["index"] = idx
    return _compress_sections(normalized, duration_sec)


def _build_shot_plan(config: dict, sections: list[dict]) -> list[dict]:
    total_duration = sum(float(section.get("duration_sec", 0.0) or 0.0) for section in sections)
    shots: list[dict] = []
    for section in sections:
        for part in _split_section_into_shots(config, section):
            shots.append(
                {
                    "shot_id": "",
                    "section_name": section["section_name"],
                    "section_type": section["section_type"],
                    "start_sec": part["start_sec"],
                    "end_sec": part["end_sec"],
                    "duration_sec": round(part["end_sec"] - part["start_sec"], 3),
                    "shot_role": part["shot_role"],
                    "visual_mode": part["visual_mode"],
                    "energy": part["energy"],
                    "render_mode": part["render_mode"],
                    "source_section_index": section["index"],
                }
            )
    normalized = _renumber_shots(shots)
    if _use_m1_window(total_duration):
        normalized = _compress_shots_to_m1_window(normalized)
        normalized = _renumber_shots(normalized)
    return _apply_render_routing(config, normalized)


def _split_section_into_shots(config: dict, section: dict) -> list[dict]:
    duration_sec = float(section["duration_sec"])
    section_type = str(section["section_type"])
    shot_specs = _section_shot_specs(section_type, duration_sec)
    start_sec = float(section["start_sec"])
    out: list[dict] = []
    cursor = start_sec
    for idx, spec in enumerate(shot_specs, start=1):
        is_last = idx == len(shot_specs)
        part_duration = duration_sec * spec["weight"]
        end_sec = float(section["end_sec"]) if is_last else round(cursor + part_duration, 3)
        out.append(
            {
                "start_sec": round(cursor, 3),
                "end_sec": round(end_sec, 3),
                "shot_role": spec["shot_role"],
                "visual_mode": spec["visual_mode"],
                "energy": spec["energy"],
                "render_mode": spec["render_mode"],
            }
        )
        cursor = end_sec
    return _apply_section_variants(section_type, _split_oversized_parts(config, section_type, out))


def _section_shot_specs(section_type: str, duration_sec: float) -> list[dict]:
    m1_mode = "i2v"
    if section_type == "intro":
        return [_spec("intro_mood", "profile_mood", "low", m1_mode, 1.0)]
    if section_type == "outro":
        return [_spec("outro_release", "memory_flash", "low", m1_mode, 1.0)]
    if section_type == "chorus":
        if duration_sec >= 7.0:
            return [
                _spec("chorus_arrive", "chorus_performance", "high", m1_mode, 0.5),
                _spec("chorus_hold", "neon_release", "high", m1_mode, 0.5),
            ]
        return [_spec("chorus_peak", "chorus_performance", "high", m1_mode, 1.0)]
    if section_type == "bridge":
        return [_spec("bridge_shift", "night_bridge", "medium", m1_mode, 1.0)]
    if section_type == "pre_chorus":
        return [_spec("prechorus_lift", "city_glance", "medium", m1_mode, 1.0)]
    if duration_sec >= 7.0:
        return [
            _spec("verse_setup", "night_drive", "medium", m1_mode, 0.5),
            _spec("verse_detail", "window_reflection", "medium", m1_mode, 0.5),
        ]
    return [_spec("verse_flow", "night_drive", "medium", m1_mode, 1.0)]


def _build_render_item(config: dict, concept_text: str, citypop_bible: dict, shot: dict) -> dict:
    prompt_seed = _prompt_seed(concept_text, citypop_bible, shot)
    prompt_draft = _prompt_draft(shot)
    prompt_polish = _prompt_polish(prompt_seed, prompt_draft)
    out = {
        "shot_id": shot["shot_id"],
        "render_mode": shot["render_mode"],
        "prompt_seed": prompt_seed,
        "prompt_draft": prompt_draft,
        "prompt_polish": prompt_polish,
        "still_a": "",
        "still_b": str(shot.get("bridge_to_shot_id", "")).strip(),
    }
    if str(shot.get("render_mode", "")) == "ia2v":
        out["audio_segment"] = {
            "start_sec": shot["start_sec"],
            "duration_sec": shot["duration_sec"],
        }
    return out


def _apply_render_routing(config: dict, shots: list[dict]) -> list[dict]:
    routed = _apply_ia2v_routing(config, shots)
    return _apply_flf2v_routing(config, routed)


def _apply_ia2v_routing(config: dict, shots: list[dict]) -> list[dict]:
    planning = config.get("planning", {}) if isinstance(config, dict) else {}
    enable_ia2v = bool(planning.get("enable_ia2v", False))
    if not enable_ia2v:
        return shots
    max_ia2v_shots = _int(planning.get("max_ia2v_shots"), 2, minimum=1)
    min_sec = _float(planning.get("ia2v_min_sec"), 4.0)
    max_sec = _float(planning.get("ia2v_max_sec"), 8.0)
    routed: list[dict] = []
    used_sections: set[int] = set()
    ia2v_count = 0
    for shot in shots:
        updated = dict(shot)
        if (
            ia2v_count < max_ia2v_shots
            and _eligible_for_ia2v(updated, min_sec, max_sec)
            and int(updated.get("source_section_index", 0) or 0) not in used_sections
        ):
            updated["render_mode"] = "ia2v"
            used_sections.add(int(updated.get("source_section_index", 0) or 0))
            ia2v_count += 1
        routed.append(updated)
    return routed


def _apply_flf2v_routing(config: dict, shots: list[dict]) -> list[dict]:
    planning = config.get("planning", {}) if isinstance(config, dict) else {}
    if not bool(planning.get("enable_flf2v", False)):
        return shots
    max_flf2v_shots = _int(planning.get("max_flf2v_shots"), 1, minimum=1)
    min_sec = _float(planning.get("flf2v_min_sec"), 3.0)
    max_sec = _float(planning.get("flf2v_max_sec"), 6.0)
    routed = [dict(shot) for shot in shots]
    flf2v_count = 0
    for idx, shot in enumerate(routed[:-1]):
        next_shot = routed[idx + 1]
        if flf2v_count >= max_flf2v_shots:
            break
        if _eligible_for_flf2v(shot, next_shot, min_sec, max_sec):
            shot["render_mode"] = "flf2v"
            shot["bridge_to_shot_id"] = next_shot["shot_id"]
            shot["shot_role"] = "bridge_transition"
            shot["visual_mode"] = "bridge_transition"
            flf2v_count += 1
    return routed


def _eligible_for_ia2v(shot: dict, min_sec: float, max_sec: float) -> bool:
    duration_sec = float(shot.get("duration_sec", 0.0) or 0.0)
    if str(shot.get("section_type", "")) != "chorus":
        return False
    if str(shot.get("visual_mode", "")) != "chorus_performance":
        return False
    return min_sec <= duration_sec <= max_sec


def _eligible_for_flf2v(shot: dict, next_shot: dict, min_sec: float, max_sec: float) -> bool:
    if str(shot.get("render_mode", "")) != "i2v":
        return False
    duration_sec = float(shot.get("duration_sec", 0.0) or 0.0)
    if not (min_sec <= duration_sec <= max_sec):
        return False
    section_type = str(shot.get("section_type", ""))
    next_section_type = str(next_shot.get("section_type", ""))
    if section_type in {"bridge", "pre_chorus"} and next_section_type != section_type:
        return True
    return section_type == "verse" and next_section_type == "chorus" and str(shot.get("visual_mode", "")) == "window_reflection"


def _prompt_seed(concept_text: str, citypop_bible: dict, shot: dict) -> str:
    concept = _concept_seed_phrase(concept_text)
    progression = _section_progression_hint(shot)
    scene_event = _shot_scene_detail(shot)
    subject = _qwen_subject_phrase(shot)
    location = _qwen_location_phrase(shot)
    palette = _qwen_palette_phrase(shot, citypop_bible)
    return ", ".join(
        part
        for part in [
            concept,
            f"progression: {progression}" if progression else "",
            f"scene event: {scene_event}" if scene_event else "",
            subject,
            location,
            palette,
            "clean cel shading",
            "bold graphic composition",
            "80s japanese city pop illustration",
            "film grain",
        ]
        if part
    )


def _concept_seed_phrase(concept_text: str) -> str:
    text = str(concept_text or "").strip()
    lower = text.lower()
    if "japanese" in lower and "city pop" in lower:
        return "Japanese 80s city pop music video"
    return text or "city pop music video"


def _prompt_draft(shot: dict) -> str:
    styling = _qwen_styling_phrase(shot)
    framing = _qwen_framing_phrase(shot)
    return ", ".join(
        part
        for part in [
            styling,
            framing,
            "clean cel shading",
            "bold graphic composition",
            "80s japanese city pop illustration",
            "film grain",
        ]
        if part
    )


def _prompt_polish(prompt_seed: str, prompt_draft: str) -> str:
    tokens: list[str] = []
    for block in (prompt_seed, prompt_draft):
        for token in [part.strip() for part in str(block).split(",") if part.strip()]:
            if token not in tokens:
                tokens.append(token)
    return ", ".join(tokens)


def _section_progression_hint(shot: dict) -> str:
    name = str(shot.get("section_name", "")).strip().lower()
    if "pre-chorus 2" in name or "pre_chorus 2" in name:
        return "tension rises faster, less hesitation"
    if "pre-chorus" in name or "pre_chorus" in name:
        return "anticipation tightens before the lift"
    if "final chorus" in name:
        return "last release before dawn, emotionally resolved"
    if "chorus 2" in name:
        return "hook returns brighter, more exposed"
    if "chorus" in name:
        return "first payoff, arrival of the hook"
    if "verse 2" in name:
        return "same night, changed perspective"
    if "bridge" in name:
        return "the night turns inward before the final return"
    if "outro" in name:
        return "afterglow and tail lights fading out"
    return "opening pass through the night"


def _shot_scene_detail(shot: dict) -> str:
    visual_mode = str(shot.get("visual_mode", "")).strip()
    role = str(shot.get("shot_role", "")).strip()
    mapping = {
        "profile_mood": "solo lead portrait in a quiet city setting at blue hour with ambient glow on the face",
        "night_drive": "late-night city movement with reflected streetlights sliding across glass and metal surfaces",
        "window_reflection": "close-up with layered reflections across glass, cheek, or polished surfaces",
        "city_glance": "three-quarter glance toward passing signs, platform lights, or side streets",
        "chorus_performance": "intimate performance shot with the city opening behind the singer",
        "neon_release": "wide exterior pass through a lit boulevard or open night street",
        "night_bridge": "quiet transitional night crossing with sparse traffic and open dark space below",
        "memory_flash": "soft memory flash with film-grain warmth and moving air in the frame",
        "bridge_transition": "visual handoff from interior reflection to the next scene anchor",
    }
    detail = mapping.get(visual_mode, "city pop shot with one clear visual beat")
    if role.startswith("verse_detail"):
        return "close-up on hands, glass, fabric, and reflected city light in a quiet intimate moment"
    if role.startswith("chorus_hold"):
        return "held emotional release as the hook settles in and the city lights stretch behind the subject"
    if role.startswith("chorus_arrive"):
        return "the hook lands as the camera meets the singer head-on"
    if role.startswith("outro_tail"):
        return "the last light drifting away after the song resolves"
    return detail


def _shot_framing_and_motion(shot: dict) -> tuple[str, str]:
    visual_mode = str(shot.get("visual_mode", "")).strip()
    framing = {
        "profile_mood": "medium close-up portrait",
        "night_drive": "front-seat medium wide",
        "window_reflection": "tight reflection close-up",
        "city_glance": "three-quarter profile medium shot",
        "chorus_performance": "close-up performance framing",
        "neon_release": "wide moving exterior shot",
        "night_bridge": "wide bridge crossing shot",
        "memory_flash": "soft handheld memory close-up",
        "bridge_transition": "match-cut transition framing",
    }.get(visual_mode, "cinematic medium shot")
    motion = {
        "profile_mood": "slow dashboard-light drift",
        "night_drive": "steady forward glide",
        "window_reflection": "subtle lateral drift",
        "city_glance": "soft side-pan",
        "chorus_performance": "gentle forward push",
        "neon_release": "measured tracking move",
        "night_bridge": "slow bridge glide",
        "memory_flash": "soft drifting motion",
        "bridge_transition": "controlled transition move",
    }.get(visual_mode, "restrained motion")
    return framing, motion


def _qwen_subject_phrase(shot: dict) -> str:
    visual_mode = str(shot.get("visual_mode", "")).strip()
    role = str(shot.get("shot_role", "")).strip()
    if visual_mode == "profile_mood":
        return "a close-up of a woman with long dark hair under fluorescent station light"
    if visual_mode == "night_drive":
        return "a close-up of a singer in reflected night light with strong presence"
    if visual_mode == "window_reflection":
        return "a close-up of a singer through glass with reflected city lights"
    if visual_mode == "city_glance":
        return "a close-up of a woman turning toward the camera through city reflections"
    if visual_mode == "chorus_performance":
        return "a close-up of a singer facing the camera with neon reflections and vivid expression"
    if visual_mode == "neon_release":
        return "a close-up of a singer framed by neon reflections and moving city light"
    if visual_mode == "night_bridge":
        return "a close-up of a solitary woman with bridge lights behind her"
    if visual_mode == "memory_flash":
        return "a close-up portrait of a woman with soft reflected light and wind in her hair"
    if visual_mode == "bridge_transition":
        return "a close-up of a woman shifting from reflection to open night air"
    if role.startswith("chorus"):
        return "a close-up of a singer in a reflective city-pop portrait"
    return "a close-up of a stylish woman in an 80s city pop scene"


def _qwen_location_phrase(shot: dict) -> str:
    visual_mode = str(shot.get("visual_mode", "")).strip()
    mapping = {
        "profile_mood": "night station interior with dark glass panels",
        "night_drive": "night interior, passing street light, and reflected city glow",
        "window_reflection": "glass reflection close-up with city light spill",
        "city_glance": "night city glass reflection with passing shop lights",
        "chorus_performance": "glowing city light reflections with a nightlife backdrop",
        "neon_release": "night boulevard light reflected across glass and polished surfaces",
        "night_bridge": "bridge lights in soft focus behind the subject",
        "memory_flash": "soft city skyline or room-light reflection at dusk",
        "bridge_transition": "neon-lit transition between street light and glass reflection",
    }
    return mapping.get(visual_mode, "night city reflections")


def _qwen_palette_phrase(shot: dict, citypop_bible: dict) -> str:
    visual_mode = str(shot.get("visual_mode", "")).strip()
    if visual_mode in {"night_drive", "window_reflection", "night_bridge", "chorus_performance"}:
        return "deep blue and neon magenta palette"
    if visual_mode in {"memory_flash", "profile_mood"}:
        return "soft dusk violet and cool pink palette"
    if visual_mode in {"neon_release", "city_glance"}:
        return "deep blue and warm amber night palette"
    palette = [str(x).strip() for x in citypop_bible.get("palette", []) if str(x).strip()]
    return ", ".join(palette[:2])


def _qwen_styling_phrase(shot: dict) -> str:
    visual_mode = str(shot.get("visual_mode", "")).strip()
    if visual_mode in {"neon_release", "window_reflection", "night_drive", "chorus_performance", "city_glance"}:
        return "graphic reflective close-up styling"
    if visual_mode == "memory_flash":
        return "soft nostalgic reflective portrait styling"
    if visual_mode == "profile_mood":
        return "elegant station reflection styling"
    return "clean reflective city-pop styling"


def _qwen_framing_phrase(shot: dict) -> str:
    visual_mode = str(shot.get("visual_mode", "")).strip()
    mapping = {
        "profile_mood": "tight portrait close-up",
        "night_drive": "tight close-up with reflected night light",
        "window_reflection": "tight close-up through reflective glass",
        "city_glance": "three-quarter reflective close-up",
        "chorus_performance": "bold front-facing close-up",
        "neon_release": "medium close-up with neon framing",
        "night_bridge": "close-up with bridge lights in the background",
        "memory_flash": "soft portrait close-up",
        "bridge_transition": "graphic reflective close-up",
    }
    return mapping.get(visual_mode, "graphic close-up framing")


def _compress_sections(sections: list[dict], duration_sec: float) -> list[dict]:
    rows = [dict(row) for row in sections]
    if not _use_m1_window(duration_sec):
        return rows
    if len(rows) < M1_MIN_SHOTS:
        return _expand_sparse_sections(rows, duration_sec)
    if len(rows) > M1_MAX_SHOTS:
        return _merge_shortest_adjacent(rows)
    return rows


def _compress_shots_to_m1_window(shots: list[dict]) -> list[dict]:
    rows = [dict(row) for row in shots]
    if len(rows) <= M1_MAX_SHOTS:
        return rows
    while len(rows) > M1_MAX_SHOTS:
        best_index = 0
        best_cost = None
        for idx in range(len(rows) - 1):
            left = rows[idx]
            right = rows[idx + 1]
            cost = float(left["duration_sec"]) + float(right["duration_sec"])
            if str(left.get("section_type", "")) != str(right.get("section_type", "")):
                cost += 1000.0
            if best_cost is None or cost < best_cost:
                best_cost = cost
                best_index = idx
        left = rows[best_index]
        right = rows[best_index + 1]
        merged = {
            **left,
            "section_name": _merged_section_name(left, right),
            "section_type": _merged_shot_section_type(left, right),
            "end_sec": right["end_sec"],
            "duration_sec": round(float(right["end_sec"]) - float(left["start_sec"]), 3),
            "shot_role": f"{left['shot_role']}+{right['shot_role']}",
            "visual_mode": right["visual_mode"] if str(right.get("section_type", "")) == "chorus" else left["visual_mode"],
            "render_mode": "i2v",
            "source_section_index": _merged_source_section_index(left, right),
        }
        rows = rows[:best_index] + [merged] + rows[best_index + 2 :]
    return rows


def _expand_sparse_sections(sections: list[dict], duration_sec: float) -> list[dict]:
    if len(sections) >= M1_MIN_SHOTS:
        return sections
    expanded = [dict(row) for row in sections]
    while len(expanded) < M1_MIN_SHOTS:
        target_index = max(range(len(expanded)), key=lambda idx: float(expanded[idx]["duration_sec"]))
        target = expanded.pop(target_index)
        midpoint = round((float(target["start_sec"]) + float(target["end_sec"])) / 2.0, 3)
        if midpoint <= float(target["start_sec"]) or midpoint >= float(target["end_sec"]):
            break
        expanded.insert(
            target_index,
            {
                **target,
                "end_sec": midpoint,
                "duration_sec": round(midpoint - float(target["start_sec"]), 3),
            },
        )
        expanded.insert(
            target_index + 1,
            {
                **target,
                "start_sec": midpoint,
                "duration_sec": round(float(target["end_sec"]) - midpoint, 3),
            },
        )
    return expanded


def _merge_shortest_adjacent(sections: list[dict]) -> list[dict]:
    rows = [dict(row) for row in sections]
    while len(rows) > M1_MAX_SHOTS:
        best_index = 0
        best_cost = None
        for idx in range(len(rows) - 1):
            cost = float(rows[idx]["duration_sec"]) + float(rows[idx + 1]["duration_sec"])
            if best_cost is None or cost < best_cost:
                best_cost = cost
                best_index = idx
        left = rows[best_index]
        right = rows[best_index + 1]
        merged = {
            **left,
            "section_name": _merged_section_name(left, right),
            "section_type": _merged_shot_section_type(left, right),
            "end_sec": right["end_sec"],
            "duration_sec": round(float(right["end_sec"]) - float(left["start_sec"]), 3),
        }
        rows = rows[:best_index] + [merged] + rows[best_index + 2 :]
    return rows


def _fallback_sections(duration_sec: float) -> list[dict]:
    safe_duration = max(M1_TARGET_DURATION_MIN, min(duration_sec, M1_TARGET_DURATION_MAX))
    section_types = ["intro", "verse", "chorus", "outro"] if safe_duration < 18.0 else ["intro", "verse", "verse", "chorus", "outro"]
    section_len = round(safe_duration / len(section_types), 3)
    out: list[dict] = []
    for idx, section_type in enumerate(section_types, start=1):
        start_sec = round((idx - 1) * section_len, 3)
        end_sec = round(safe_duration if idx == len(section_types) else idx * section_len, 3)
        out.append(
            {
                "index": idx,
                "section_name": section_type.upper(),
                "section_type": section_type,
                "start_sec": start_sec,
                "end_sec": end_sec,
                "duration_sec": round(end_sec - start_sec, 3),
            }
        )
    return out


def _split_oversized_parts(config: dict, section_type: str, parts: list[dict]) -> list[dict]:
    max_shot_sec = _max_shot_sec(config)
    if max_shot_sec <= 0:
        return parts
    expanded: list[dict] = []
    for part in parts:
        duration_sec = float(part.get("end_sec", 0.0) or 0.0) - float(part.get("start_sec", 0.0) or 0.0)
        split_count = max(1, int(math.ceil(duration_sec / max_shot_sec)))
        if split_count == 1:
            expanded.append(part)
            continue
        start_sec = float(part["start_sec"])
        step = duration_sec / float(split_count)
        for idx in range(split_count):
            sub_start = round(start_sec + (step * idx), 3)
            sub_end = round(float(part["end_sec"]) if idx == split_count - 1 else start_sec + (step * (idx + 1)), 3)
            expanded.append(
                {
                    **part,
                    "start_sec": sub_start,
                    "end_sec": sub_end,
                }
            )
    return expanded


def _apply_section_variants(section_type: str, parts: list[dict]) -> list[dict]:
    if not parts:
        return []
    out: list[dict] = []
    split_count = len(parts)
    for idx, part in enumerate(parts):
        role, visual = _shot_variant(section_type, idx, split_count, str(part.get("shot_role", "")), str(part.get("visual_mode", "")))
        out.append(
            {
                **part,
                "shot_role": role,
                "visual_mode": visual,
            }
        )
    return out


def _shot_variant(section_type: str, idx: int, split_count: int, shot_role: str, visual_mode: str) -> tuple[str, str]:
    sequences = {
        "intro": [("intro_mood", "profile_mood"), ("intro_drive", "night_drive")],
        "verse": [("verse_setup", "night_drive"), ("verse_detail", "window_reflection"), ("verse_flow", "night_drive"), ("verse_glow", "city_glance")],
        "pre_chorus": [("prechorus_lift", "city_glance"), ("prechorus_tension", "window_reflection")],
        "chorus": [("chorus_arrive", "chorus_performance"), ("chorus_hold", "neon_release"), ("chorus_sweep", "chorus_performance"), ("chorus_afterglow", "neon_release")],
        "bridge": [("bridge_shift", "night_bridge"), ("bridge_drift", "window_reflection")],
        "outro": [("outro_release", "memory_flash"), ("outro_tail", "memory_flash")],
    }
    options = sequences.get(section_type, [(shot_role, visual_mode)])
    role, visual = options[min(idx, len(options) - 1)]
    if split_count <= len(options):
        return role, visual
    return (f"{role}_{idx + 1}", visual)


def _renumber_shots(shots: list[dict]) -> list[dict]:
    out: list[dict] = []
    for idx, shot in enumerate(shots, start=1):
        row = dict(shot)
        row["shot_id"] = f"S{idx:03d}"
        out.append(row)
    return out


def _use_m1_window(duration_sec: float) -> bool:
    return float(duration_sec) <= (M1_TARGET_DURATION_MAX + 2.0)


def _max_shot_sec(config: dict) -> float:
    planning = config.get("planning", {}) if isinstance(config, dict) else {}
    return max(1.0, _float(planning.get("max_shot_sec"), 8.0))


def _canonical_section_type(row: dict) -> str:
    raw = str(row.get("section") or row.get("name") or row.get("section_name") or row.get("label") or "").strip().lower()
    if "pre" in raw and "chorus" in raw:
        return "pre_chorus"
    if "chorus" in raw:
        return "chorus"
    if "bridge" in raw:
        return "bridge"
    if "outro" in raw:
        return "outro"
    if "intro" in raw:
        return "intro"
    return "verse"


def _citypop_bible() -> dict:
    return {
        "style": "japanese_citypop_80s_90s",
        "palette": ["sunset amber", "ocean blue", "neon cyan", "sodium-vapor night"],
        "motifs": ["city lights", "glass reflections", "summer air", "film grain", "late train", "cassette glow", "quiet boulevard", "rooftop dusk"],
        "wardrobe_rules": ["light summer jacket", "retro blouse", "silver accessories", "soft silhouette"],
        "camera_rules": ["restrained dolly", "soft lateral drift", "no aggressive handheld", "no hyper-cutting"],
        "negative_rules": ["k-pop look", "hard cyberpunk", "crowded multi-character shot", "club performance stage", "modern influencer aesthetic"],
    }


def _spec(shot_role: str, visual_mode: str, energy: str, render_mode: str, weight: float) -> dict:
    return {
        "shot_role": shot_role,
        "visual_mode": visual_mode,
        "energy": energy,
        "render_mode": render_mode,
        "weight": weight,
    }


def _merged_section_name(left: dict, right: dict) -> str:
    left_name = str(left.get("section_name", "")).strip()
    right_name = str(right.get("section_name", "")).strip()
    return left_name if left_name == right_name else f"{left_name}->{right_name}"


def _merged_shot_section_type(left: dict, right: dict) -> str:
    left_type = str(left.get("section_type", "")).strip()
    right_type = str(right.get("section_type", "")).strip()
    if left_type == right_type:
        return left_type
    priority = {"outro": 5, "chorus": 4, "bridge": 3, "pre_chorus": 2, "verse": 1, "intro": 0}
    return right_type if priority.get(right_type, -1) >= priority.get(left_type, -1) else left_type


def _merged_source_section_index(left: dict, right: dict) -> int:
    left_index = _int(left.get("source_section_index"), 0)
    right_index = _int(right.get("source_section_index"), 0)
    if str(left.get("section_type", "")).strip() == str(right.get("section_type", "")).strip():
        return left_index
    return right_index or left_index


def _float(value: object, default: float) -> float:
    try:
        return float(value)
    except Exception:
        return default


def _int(value: object, default: int, *, minimum: int = 0) -> int:
    try:
        parsed = int(value)
    except Exception:
        return default
    return max(minimum, parsed)
