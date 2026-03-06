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
        f"Song title={title}; Song description={desc}; Style guidance={guidance}; Lyrics excerpt={lyrics}; Sections={section_view}."
    )


def _normalize_shots(shots: list[dict], sections: list[dict], target_total: float) -> list[dict]:
    parsed = [normalize_tti_shot(s, i) for i, s in enumerate(shots) if isinstance(s, dict)]
    parsed = [s for s in parsed if _valid_prompt_pair(s)]
    if not parsed:
        raise RuntimeError("no valid shots from TTI planner")
    if not sections:
        raise RuntimeError("sections missing for TTI planner")
    keyed = _select_section_key_shots(parsed, len(sections))
    aligned = _assign_one_shot_per_section(keyed, sections)
    total = sum(float(x["duration_sec"]) for x in aligned)
    if total <= 0:
        raise RuntimeError("invalid total shot duration")
    _rescale_durations(aligned, max(0.001, float(target_total)))
    return aligned


def _select_section_key_shots(shots: list[dict], count: int) -> list[dict]:
    if count <= 0:
        raise RuntimeError("section count must be positive")
    if not shots:
        raise RuntimeError("shots must not be empty")
    if count == 1:
        return [dict(shots[0])]
    if len(shots) == 1:
        return [dict(shots[0]) for _ in range(count)]
    last = len(shots) - 1
    out: list[dict] = []
    for i in range(count):
        idx = int(round((i * last) / float(count - 1)))
        out.append(dict(shots[idx]))
    return out


def _assign_one_shot_per_section(shots: list[dict], sections: list[dict]) -> list[dict]:
    if len(shots) != len(sections):
        raise RuntimeError(f"section shot mismatch: shots={len(shots)} sections={len(sections)}")
    out: list[dict] = []
    for i, (row, sec) in enumerate(zip(shots, sections), start=1):
        sec_name = str(sec.get("name", "section"))
        sec_dur = max(0.001, _sec_end(sec) - _sec_start(sec))
        item = dict(row)
        item["shot_id"] = f"S{i:03d}"
        item["section_name"] = sec_name
        item["is_chorus"] = _is_chorus(sec_name)
        item["duration_sec"] = round(sec_dur, 3)
        out.append(item)
    return out


def _align_section_timing(shots: list[dict], sections: list[dict]) -> list[dict]:
    counts = _distribute_counts(len(shots), sections)
    out: list[dict] = []
    idx = 0
    for sec, cnt in zip(sections, counts):
        if cnt <= 0:
            continue
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
    if len(out) != len(shots):
        raise RuntimeError(f"section alignment mismatch: expected={len(shots)} actual={len(out)}")
    return out


def _distribute_counts(total_shots: int, sections: list[dict]) -> list[int]:
    if total_shots <= 0:
        raise RuntimeError("total_shots must be positive")
    if not sections:
        raise RuntimeError("sections must not be empty")
    weights = [_section_weight(s) for s in sections]
    mass = sum(weights)
    if mass <= 0:
        raw = [float(total_shots) / float(len(sections))] * len(sections)
    else:
        raw = [(w / mass) * total_shots for w in weights]
    base = [int(x) for x in raw]
    remain = total_shots - sum(base)
    frac_rank = sorted(range(len(raw)), key=lambda i: (raw[i] - base[i]), reverse=True)
    for i in range(remain):
        base[frac_rank[i % len(frac_rank)]] += 1
    if sum(base) != total_shots:
        raise RuntimeError("shot distribution mismatch")
    return base


def _rescale_durations(shots: list[dict], target_total: float) -> None:
    if not shots:
        raise RuntimeError("shots must not be empty")
    base = [max(0.001, float(s["duration_sec"])) for s in shots]
    n = len(base)
    min_dur = min(2.0, target_total / float(n))
    reserve = min_dur * n
    budget = max(0.0, target_total - reserve)
    mass = sum(base)
    if mass <= 0:
        vals = [target_total / float(n)] * n
    else:
        vals = [min_dur + (budget * (x / mass)) for x in base]
    rounded = [round(x, 3) for x in vals]
    drift = round(target_total - sum(rounded), 3)
    rounded[-1] = round(max(0.001, rounded[-1] + drift), 3)
    for shot, dur in zip(shots, rounded):
        shot["duration_sec"] = dur


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
    sec = str(name).strip().lower()
    return sec == "chorus" or sec.startswith("chorus_")


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
