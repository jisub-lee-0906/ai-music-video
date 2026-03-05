from __future__ import annotations

from ai_mv.utils.text_utils import ensure_16_9, parse_size


def map_wan_workflow(config: dict, clip: dict) -> dict:
    w, h = _wan_size(config, clip)
    idx = _shot_index(clip.get("shot_id", "0"))
    seed = 3000 + idx + int(clip.get("seed_offset", 0))
    steps = _steps_for_energy(str(clip.get("energy", "mid")))
    guidance = str(config.get("style", {}).get("guidance", "music video")).strip() or "music video"
    return {
        "shot.prompt": str(clip.get("prompt", f"{guidance}, motion for {clip['shot_id']}")),
        "shot.negative_prompt": str(clip.get("negative_prompt", "flicker, low quality")),
        "shot.seed": seed,
        "shot.start_image": clip["start"],
        "shot.end_image": clip["end"],
        "shot.length_frames": int(clip.get("frames", 96)),
        "shot.steps": steps,
        "video.width": w,
        "video.height": h,
        "video.fps": clip["fps"],
        "video.filename_prefix": clip.get("filename_prefix", "video/ComfyUI"),
    }


def build_concat_plan(config: dict, payload: dict) -> dict:
    clips = payload.get("clips", [])
    return {"ordered": [x["video"] for x in clips]}


def _shot_index(shot_id: str) -> int:
    token = str(shot_id).split("_")[-1]
    digits = "".join(ch for ch in token if ch.isdigit())
    return int(digits) if digits else 0


def _wan_size(config: dict, clip: dict) -> tuple[int, int]:
    size = str(clip.get("wan_size", config.get("render", {}).get("wan_size", "640x360")))
    w, h = parse_size(size)
    ensure_16_9(w, h)
    return w, h


def wan_required_inputs() -> dict[str, list[str]]:
    return {
        "LoadImage": ["image"],
        "CLIPTextEncode": ["text"],
        "WanFirstLastFrameToVideo": ["width", "height", "length", "start_image", "end_image"],
        "KSamplerAdvanced": ["noise_seed", "steps"],
        "CreateVideo": ["fps"],
        "SaveVideo": ["filename_prefix"],
    }


def _steps_for_energy(energy: str) -> int:
    if energy == "low":
        return 14
    if energy == "high":
        return 22
    return 18
