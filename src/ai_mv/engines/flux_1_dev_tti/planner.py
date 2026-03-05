from __future__ import annotations

from ai_mv.core.contracts.prompt_contract import normalize_tti_shot, tti_schema
from ai_mv.infra.ollama_client import generate_structured


SHOT_TYPES = ["CHAR_MASTER", "PERF_WIDE", "EMOTION_CLOSE", "DETAIL_INSERT", "ENV_TRANSITION"]


def build_tti_plan(config: dict, payload: dict) -> dict:
    audio_map = payload["audio_map"]
    sections = audio_map["sections"]
    total = float(audio_map["duration_sec"])
    shots = _plan_with_ollama(config, sections)
    return {"shots": _normalize_shots(shots, total)}


def _plan_with_ollama(config: dict, sections: list[dict]) -> list[dict]:
    out = generate_structured(config, _planner_prompt(config, sections), tti_schema())
    if not isinstance(out, dict) or not isinstance(out.get("shots"), list):
        raise RuntimeError("invalid TTI planner output")
    return out["shots"]


def _planner_prompt(config: dict, sections: list[dict]) -> str:
    audio = config["audio"]
    guidance = str(config["style"]["guidance"]).strip()
    title = str(audio["song_title"]).strip()
    desc = str(audio["song_description"]).strip()
    lyrics = _lyrics_excerpt(str(audio["lyrics"]))
    section_view = _section_summary(sections)
    keywords = _keywords(config)
    types = ", ".join(SHOT_TYPES)
    return (
        "You are a senior music-video visual director and FLUX prompt engineer. "
        "Return strict JSON only with shape {\"shots\":[...]}. No prose outside JSON. "
        "Never force any genre; infer visual language from style guidance, profile keywords, and lyrics context. "
        "Each shot item must include: shot_id,prompt_clip_l,prompt_t5xxl,negative_prompt,duration_sec,seed,shot_type,is_chorus. "
        "prompt_clip_l must be 18-36 unique tags, comma+space separated, all lowercase natural phrases. "
        "No snake_case, no brackets, no markdown, no full sentence. "
        "Required slot order in clip_l: subject identity, face traits, hair, eyes, wardrobe, fabric/material, pose/action, "
        "foreground prop, background set, lighting style, lens/camera language, mood, color palette, cinematic quality. "
        "Quality mandate for clip_l: include at least one texture token, one optical token, one light token, one atmosphere token. "
        "prompt_t5xxl must be exactly 2 natural English sentences about the same scene as clip_l. "
        "Sentence 1 = subject + environment + key prop with concrete visual detail. "
        "Sentence 2 = camera + lighting + emotion + motion cue with cinematic language. "
        "Keep one consistent hero identity and outfit continuity across shots unless lyrics explicitly indicate transformation. "
        "Avoid vague words: beautiful, nice, good, amazing. Prefer precise nouns and adjectives. "
        "negative_prompt must suppress defects: low quality, blurry, jpeg artifacts, extra fingers, bad hands, bad face, "
        "deformed anatomy, text watermark, logo, subtitle. "
        "Reduce repetition: do not repeat exact 3-word phrase from previous shot unless chorus callback is intentional. "
        "Shot count must match section count exactly. "
        f"Use shot_type only from enum: {types}. "
        f"Song title={title}; Song description={desc}; Style guidance={guidance}; "
        f"Profile keywords={keywords}; Lyrics excerpt={lyrics}; Sections={section_view}."
    )


def _normalize_shots(shots: list[dict], target_total: float) -> list[dict]:
    if not isinstance(shots, list):
        raise RuntimeError("shots must be list")
    parsed = [normalize_tti_shot(s, i) for i, s in enumerate(shots) if isinstance(s, dict)]
    parsed = [s for s in parsed if _valid_prompt_pair(s)]
    if not parsed:
        raise RuntimeError("no valid shots from TTI planner")
    total = sum(float(s["duration_sec"]) for s in parsed)
    if total <= 0:
        raise RuntimeError("invalid total shot duration")
    scale = target_total / total
    for shot in parsed:
        shot["duration_sec"] = max(2.0, round(float(shot["duration_sec"]) * scale, 3))
    return parsed


def _valid_prompt_pair(shot: dict) -> bool:
    clip_l = str(shot["prompt_clip_l"]).strip()
    t5 = str(shot["prompt_t5xxl"]).strip()
    if not clip_l or not t5:
        return False
    return clip_l.count(",") >= 12


def _keywords(config: dict) -> str:
    arr = [str(x).strip() for x in config["audio"]["keywords"] if str(x).strip()]
    return ", ".join(arr)


def _lyrics_excerpt(text: str) -> str:
    lines = [x.strip() for x in text.splitlines() if x.strip()]
    if not lines:
        return ""
    keep = lines[:12]
    return " | ".join(keep)


def _section_summary(sections: list[dict]) -> str:
    out: list[str] = []
    for row in sections:
        if not isinstance(row, dict):
            continue
        name = str(row.get("name", "section")).strip()
        start = float(row.get("start", 0.0))
        end = float(row.get("end", 0.0))
        out.append(f"{name}:{round(start, 2)}-{round(end, 2)}")
    if not out:
        raise RuntimeError("sections missing for TTI prompt planner")
    return ", ".join(out)
