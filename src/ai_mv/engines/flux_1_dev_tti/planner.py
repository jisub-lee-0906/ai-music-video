from __future__ import annotations

from ai_mv.engines.flux_1_dev_tti.planner_parts.fallbacks import default_shots
from ai_mv.infra.ollama_client import generate_json


def build_tti_plan(config: dict, payload: dict) -> dict:
    audio_map = payload.get("audio_map", {})
    sections = audio_map.get("sections", [])
    shots = _plan_with_ollama(config, sections)
    if not shots:
        shots = default_shots(sections, config.get("style", {}).get("guidance", "cinematic"))
    return {"shots": shots}


def _plan_with_ollama(config: dict, sections: list[dict]) -> list[dict]:
    guidance = config.get("style", {}).get("guidance", "cinematic")
    prompt = _planner_prompt(guidance, sections)
    try:
        out = generate_json(config, prompt)
    except Exception:
        return []
    shots = out.get("shots", []) if isinstance(out, dict) else []
    return _normalize_shots(shots)


def _planner_prompt(guidance: str, sections: list[dict]) -> str:
    return (
        "Create strict JSON with key 'shots' only. "
        "Each shot must include shot_id,prompt,negative_prompt,duration_sec,seed. "
        f"Guidance: {guidance}. Sections: {sections}"
    )


def _normalize_shots(shots: list[dict]) -> list[dict]:
    out: list[dict] = []
    for idx, shot in enumerate(shots or []):
        if not isinstance(shot, dict):
            continue
        sid = str(shot.get("shot_id", f"verse_{idx:03d}"))
        prompt = str(shot.get("prompt", "")).strip()
        if not prompt:
            continue
        out.append(
            {
                "shot_id": sid,
                "prompt": prompt,
                "negative_prompt": str(shot.get("negative_prompt", "lowres, blur, artifacts")),
                "duration_sec": float(shot.get("duration_sec", 5.0)),
                "seed": int(shot.get("seed", 1000 + idx)),
            }
        )
    return out
