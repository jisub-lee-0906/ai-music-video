from __future__ import annotations


def expand_anchor_clips(anchors: list[dict], fps: int, max_clip_sec: float | None) -> list[dict]:
    out: list[dict] = []
    for anchor in anchors:
        parts = _split_frames(float(anchor["duration_sec"]), fps, max_clip_sec, str(anchor.get("section_name", "")))
        if len(parts) == 1:
            out.append(_with_part(anchor, str(anchor["shot_id"]), parts[0], 1, fps))
            continue
        for i, frames in enumerate(parts, start=1):
            out.append(_with_part(anchor, _clip_id(str(anchor["shot_id"]), i), frames, i, fps))
    return out


def read_max_clip_sec(config: dict) -> float:
    render = config.get("render", {}) if isinstance(config, dict) else {}
    if not isinstance(render, dict):
        return 5.0
    if "wan_max_clip_sec" not in render:
        return 5.0
    try:
        val = float(render.get("wan_max_clip_sec"))
    except Exception:
        return 5.0
    return max(0.5, min(5.0, val))


def _with_part(anchor: dict, shot_id: str, frames: int, clip_index: int, fps: int) -> dict:
    out = dict(anchor)
    out["shot_id"] = shot_id
    out["clip_index"] = clip_index
    out["duration_sec"] = round(frames / float(max(1, fps)), 3)
    return out


def _split_frames(duration_sec: float, fps: int, max_clip_sec: float | None, section_name: str) -> list[int]:
    floor = _frame_floor(fps)
    total = max(floor, int(round(max(0.01, duration_sec) * fps)))
    if max_clip_sec is None:
        return [total]
    max_frames = _sec_to_frames(max_clip_sec, fps, floor)
    if total <= max_frames:
        return [total]
    target = _sec_to_frames(_section_target_sec(section_name, max_clip_sec), fps, floor)
    min_frames = _sec_to_frames(min(1.8, max_clip_sec), fps, floor)
    return _variable_split(total, target, min_frames, max_frames)


def _variable_split(total: int, target: int, min_frames: int, max_frames: int) -> list[int]:
    out: list[int] = []
    remain = total
    pattern = (0.8, 1.0, 1.2, 0.9, 1.1)
    idx = 0
    while remain > 0:
        if remain <= max_frames:
            out.append(remain)
            break
        frames = int(round(target * pattern[idx % len(pattern)]))
        frames = max(min_frames, min(max_frames, frames))
        if 0 < (remain - frames) < min_frames:
            frames = max(min_frames, remain - min_frames)
        out.append(frames)
        remain -= frames
        idx += 1
    return out


def _section_target_sec(section_name: str, max_clip_sec: float) -> float:
    sec = section_name.lower()
    if "chorus" in sec:
        base = 2.6
    elif "bridge" in sec or "outro" in sec:
        base = 3.8
    elif "intro" in sec:
        base = 2.8
    elif "verse" in sec:
        base = 3.4
    else:
        base = 3.0
    return min(max_clip_sec, base)


def _sec_to_frames(sec: float, fps: int, floor: int) -> int:
    return max(floor, int(round(sec * fps)))


def _frame_floor(fps: int) -> int:
    return max(1, int(round(max(1, fps) * 0.25)))


def _clip_id(shot_id: str, idx: int) -> str:
    return f"{shot_id}_C{idx:02d}"
