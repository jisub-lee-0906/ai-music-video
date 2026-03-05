from __future__ import annotations

from ai_mv.core.contracts.prompt_contract import normalize_tti_shot, tti_schema
from ai_mv.infra.ollama_client import generate_structured


SHOT_TYPES = ["CHAR_MASTER", "PERF_WIDE", "EMOTION_CLOSE", "DETAIL_INSERT", "ENV_TRANSITION"]


def build_tti_plan(config: dict, payload: dict) -> dict:
    audio_map = payload["audio_map"]
    sections = list(audio_map["sections"])
    total = float(audio_map["duration_sec"])
    shots = _plan_with_ollama(config, sections)
    return {"shots": _normalize_shots(shots, sections, total)}


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
    types = ", ".join(SHOT_TYPES)
    return (
        "You are a senior music-video visual director and FLUX prompt engineer. "
        "Return strict JSON only with shape {\"shots\":[...]}. No prose outside JSON. "
        "Never force any genre; infer visual language from style guidance and lyrics context. "
        "Each shot item must include: shot_id,prompt_clip_l,prompt_t5xxl,negative_prompt,duration_sec,seed,shot_type,is_chorus. "
        "prompt_clip_l must be 18-36 unique tags, comma+space separated, all lowercase natural phrases. "
        "prompt_t5xxl must be exactly 2 natural English sentences describing the same scene. "
        "Keep one consistent hero identity and outfit continuity across shots unless lyrics indicate transformation. "
        "negative_prompt must suppress defects: low quality, blurry, jpeg artifacts, extra fingers, bad hands, bad face, deformed anatomy, text watermark, logo, subtitle. "
        "Shot count must match section count intent and preserve section flow. "
        f"Use shot_type only from enum: {types}. "
        f"Song title={title}; Song description={desc}; Style guidance={guidance}; Lyrics excerpt={lyrics}; Sections={section_view}."
    )


def _normalize_shots(shots: list[dict], sections: list[dict], target_total: float) -> list[dict]:
    parsed = [normalize_tti_shot(s, i) for i, s in enumerate(shots) if isinstance(s, dict)]
    parsed = [s for s in parsed if _valid_prompt_pair(s)]
    if not parsed:
        raise RuntimeError("no valid shots from TTI planner")
    aligned = _align_section_timing(parsed, sections)
    total = sum(float(x["duration_sec"]) for x in aligned)
    if total <= 0:
        raise RuntimeError("invalid total shot duration")
    scale = target_total / total
    for shot in aligned:
        shot["duration_sec"] = max(2.0, round(float(shot["duration_sec"]) * scale, 3))
    return aligned


def _align_section_timing(shots: list[dict], sections: list[dict]) -> list[dict]:
    counts = _distribute_counts(len(shots), sections)
    out: list[dict] = []
    idx = 0
    for sec, cnt in zip(sections, counts):
        sec_name = str(sec.get("name", "section"))
        sec_dur = max(0.001, _sec_end(sec) - _sec_start(sec))
        dur = round(sec_dur / cnt, 3)
        for _ in range(cnt):
            row = dict(shots[min(idx, len(shots) - 1)])
            row["section_name"] = sec_name
            row["is_chorus"] = _is_chorus(sec_name)
            row["duration_sec"] = dur
            out.append(row)
            idx += 1
    return out[: len(shots)]


def _distribute_counts(total_shots: int, sections: list[dict]) -> list[int]:
    if total_shots <= 0:
        raise RuntimeError("total_shots must be positive")
    weights = [_section_weight(s) for s in sections]
    mass = sum(weights)
    raw = [(w / mass) * total_shots for w in weights]
    base = [max(1, int(x)) for x in raw]
    while sum(base) > total_shots:
        j = _argmax(base)
        if base[j] > 1:
            base[j] -= 1
        else:
            break
    while sum(base) < total_shots:
        j = _argmax(raw)
        base[j] += 1
    return base


def _section_weight(section: dict) -> float:
    name = str(section.get("name", "section"))
    dur = max(0.1, _sec_end(section) - _sec_start(section))
    mult = 1.0
    if "chorus" in name:
        mult = 1.4
    elif "verse" in name:
        mult = 0.85
    elif "bridge" in name:
        mult = 0.9
    elif "intro" in name or "outro" in name:
        mult = 0.75
    return dur * mult


def _argmax(vals: list[float]) -> int:
    best = 0
    for i, v in enumerate(vals):
        if v > vals[best]:
            best = i
    return best


def _valid_prompt_pair(shot: dict) -> bool:
    clip_l = str(shot["prompt_clip_l"]).strip()
    t5 = str(shot["prompt_t5xxl"]).strip()
    return bool(clip_l and t5 and clip_l.count(",") >= 12)


def _is_chorus(name: str) -> bool:
    return "chorus" in str(name).lower()


def _sec_start(row: dict) -> float:
    return float(row.get("start_sec", row.get("start", 0.0)))


def _sec_end(row: dict) -> float:
    return float(row.get("end_sec", row.get("end", 0.0)))


def _lyrics_excerpt(text: str) -> str:
    lines = [x.strip() for x in text.splitlines() if x.strip()]
    return " | ".join(lines[:12]) if lines else ""


def _section_summary(sections: list[dict]) -> str:
    out: list[str] = []
    for row in sections:
        name = str(row.get("name", "section")).strip()
        out.append(f"{name}:{round(_sec_start(row), 2)}-{round(_sec_end(row), 2)}")
    if not out:
        raise RuntimeError("sections missing for TTI prompt planner")
    return ", ".join(out)
