from __future__ import annotations

from ai_mv.core.contracts.prompt_contract import normalize_tti_shot, tti_schema
from ai_mv.infra.ollama_client import generate_structured


def build_tti_plan(config: dict, payload: dict) -> dict:
    audio_map = payload["audio_map"]
    sections = audio_map["sections"]
    total = float(audio_map["duration_sec"])
    shots = _plan_with_ollama(config, sections)
    return {"shots": _normalize_shots(shots, total)}


def _plan_with_ollama(config: dict, sections: list[dict]) -> list[dict]:
    guidance = str(config["style"]["guidance"])
    out = generate_structured(config, _planner_prompt(guidance, sections), tti_schema())
    if not isinstance(out, dict) or not isinstance(out.get("shots"), list):
        raise RuntimeError("invalid TTI planner output")
    return out["shots"]


def _planner_prompt(guidance: str, sections: list[dict]) -> str:
    return (
        "Return strict JSON: {'shots':[]}. Each shot has "
        "shot_id,prompt_clip_l,prompt_t5xxl,negative_prompt,duration_sec,seed,shot_type,is_chorus. "
        "prompt_clip_l must be vivid keyword-dense cinematic visual prompt. "
        "prompt_t5xxl must be natural sentence-style descriptive prompt for same scene. "
        f"Guidance={guidance}; Sections={sections}"
    )


def _normalize_shots(shots: list[dict], target_total: float) -> list[dict]:
    if not isinstance(shots, list):
        raise RuntimeError("shots must be list")
    parsed = [normalize_tti_shot(s, i) for i, s in enumerate(shots) if isinstance(s, dict)]
    parsed = [s for s in parsed if s and str(s["prompt_clip_l"]).strip() and str(s["prompt_t5xxl"]).strip()]
    if not parsed:
        raise RuntimeError("no valid shots from TTI planner")
    total = sum(float(s["duration_sec"]) for s in parsed)
    if total <= 0:
        raise RuntimeError("invalid total shot duration")
    scale = target_total / total
    for shot in parsed:
        shot["duration_sec"] = max(2.0, round(float(shot["duration_sec"]) * scale, 3))
    return parsed
