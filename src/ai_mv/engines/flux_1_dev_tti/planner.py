from __future__ import annotations

from ai_mv.core.contracts.prompt_contract import normalize_tti_shot, tti_schema
from ai_mv.engines.flux_1_dev_tti.planner_parts.fallbacks import default_shots
from ai_mv.infra.ollama_client import generate_structured

SHOT_TYPES = ["CHAR_MASTER", "PERF_WIDE", "EMOTION_CLOSE", "DETAIL_INSERT", "ENV_TRANSITION"]


def build_tti_plan(config: dict, payload: dict) -> dict:
    audio_map = payload.get("audio_map", {})
    sections = audio_map.get("sections", [])
    total = float(audio_map.get("duration_sec", 160.0))
    shots = _plan_with_ollama(config, sections)
    if not shots:
        shots = _fallback_from_sections(sections, config)
    return {"shots": _normalize_shots(shots, total)}


def _plan_with_ollama(config: dict, sections: list[dict]) -> list[dict]:
    guidance = config.get("style", {}).get("guidance", "cinematic")
    try:
        out = generate_structured(config, _planner_prompt(guidance, sections), tti_schema())
    except Exception:
        return []
    return out.get("shots", []) if isinstance(out, dict) else []


def _planner_prompt(guidance: str, sections: list[dict]) -> str:
    return (
        "Return strict JSON: {'shots':[]}. Each shot has "
        "shot_id,prompt,negative_prompt,duration_sec,seed,shot_type,is_chorus. "
        f"Guidance={guidance}; Sections={sections}"
    )


def _fallback_from_sections(sections: list[dict], config: dict) -> list[dict]:
    guidance = config.get("style", {}).get("guidance", "cinematic")
    base = default_shots(sections, guidance)
    out: list[dict] = []
    for idx, shot in enumerate(base):
        sec = shot["shot_id"].split("_")[0]
        sec_dur = _section_duration(sections, sec) or 8.0
        count = max(1, int(round(sec_dur / 4.0)))
        out.extend(_split_section_shots(shot, count, idx * 100))
    return out


def _split_section_shots(shot: dict, count: int, seed_off: int) -> list[dict]:
    name = shot["shot_id"].split("_")[0]
    return [
        {
            **shot,
            "shot_id": f"{name}_{i:03d}",
            "duration_sec": 4.0,
            "seed": int(shot["seed"]) + seed_off + i,
            "shot_type": SHOT_TYPES[i % len(SHOT_TYPES)],
            "is_chorus": name == "chorus",
        }
        for i in range(count)
    ]


def _normalize_shots(shots: list[dict], target_total: float) -> list[dict]:
    parsed = [normalize_tti_shot(s, i) for i, s in enumerate(shots or []) if isinstance(s, dict)]
    parsed = [s for s in parsed if s and str(s.get("prompt", "")).strip()]
    if not parsed:
        return []
    total = sum(float(s["duration_sec"]) for s in parsed) or 1.0
    scale = target_total / total
    for shot in parsed:
        shot["duration_sec"] = max(2.0, round(float(shot["duration_sec"]) * scale, 3))
    return parsed


def _section_duration(sections: list[dict], name: str) -> float:
    for sec in sections or []:
        if str(sec.get("name")) == name:
            return float(sec.get("end_sec", 0.0)) - float(sec.get("start_sec", 0.0))
    return 0.0
