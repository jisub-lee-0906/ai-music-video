from __future__ import annotations

from ai_mv.core.contracts.prompt_contract import normalize_wan_clips, wan_schema
from ai_mv.infra.ollama_client import generate_structured
from ai_mv.utils.text_utils import parse_target


def build_wan_plan(config: dict, payload: dict) -> dict:
    fps = parse_target(config.get("video", {}).get("target", "1920x1080@24"))[2]
    guidance = str(config.get("style", {}).get("guidance", "music video")).strip() or "music video"
    clips: list[dict] = []
    for item in payload.get("uso_images", []):
        clips.extend(_item_to_clips(item, fps))
    spec = _plan_with_ollama(config, clips)
    prompts = normalize_wan_clips(spec.get("clips", []), clips, guidance)
    clips = [_apply_prompt(x, prompts.get(x["shot_id"], {}), guidance) for x in clips]
    return {"clips": clips}


def _plan_with_ollama(config: dict, clips: list[dict]) -> dict:
    prompt = (
        "Return JSON {'clips':[]} with shot_id,prompt,negative_prompt,energy. "
        f"ShotIds={[c.get('shot_id') for c in clips]}"
    )
    try:
        return generate_structured(config, prompt, wan_schema())
    except Exception:
        return {}


def _item_to_clips(item: dict, fps: int) -> list[dict]:
    duration = float(item.get("duration_sec", 4.0))
    total = max(24, int(round(duration * fps)))
    if item.get("keyframe_mode") != "triple" or "mid" not in item:
        return [_clip(item["shot_id"], item["start"], item["end"], fps, total)]
    first = max(12, total // 2)
    second = max(12, total - first)
    return [
        _clip(f"{item['shot_id']}__a", item["start"], item["mid"], fps, first),
        _clip(f"{item['shot_id']}__b", item["mid"], item["end"], fps, second),
    ]


def _clip(shot_id: str, start: str, end: str, fps: int, frames: int) -> dict:
    return {"shot_id": shot_id, "start": start, "end": end, "fps": fps, "frames": frames}


def _apply_prompt(clip: dict, row: dict, guidance: str) -> dict:
    out = dict(clip)
    out["prompt"] = str(row.get("prompt", f"{guidance}, motion for {clip['shot_id']}"))
    out["negative_prompt"] = str(row.get("negative_prompt", "flicker, low quality"))
    out["energy"] = str(row.get("energy", "mid"))
    return out
