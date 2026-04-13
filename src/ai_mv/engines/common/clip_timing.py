from __future__ import annotations


def expand_anchor_clips(anchors: list[dict], fps: int, max_clip_sec: float | None) -> list[dict]:
    out: list[dict] = []
    for anchor in anchors:
        parts = _split_frames(float(anchor["duration_sec"]), fps, max_clip_sec, str(anchor.get("section_name", "")))
        if len(parts) == 1:
            out.append(_with_part(anchor, str(anchor["shot_id"]), parts[0], 1, len(parts), fps))
            continue
        for i, frames in enumerate(parts, start=1):
            out.append(_with_part(anchor, _clip_id(str(anchor["shot_id"]), i), frames, i, len(parts), fps))
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


def _with_part(anchor: dict, shot_id: str, frames: int, clip_index: int, clip_count: int, fps: int) -> dict:
    out = dict(anchor)
    out["shot_id"] = shot_id
    out["clip_index"] = clip_index
    out["clip_count"] = clip_count
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
    min_frames = _sec_to_frames(min(3.2, max_clip_sec), fps, floor)
    return _variable_split(total, target, min_frames, max_frames)


def _variable_split(total: int, target: int, min_frames: int, max_frames: int) -> list[int]:
    count = _split_count(total, min_frames, max_frames)
    base = total // count
    extra = total % count
    out = [base + (1 if i < extra else 0) for i in range(count)]
    return _nudge_toward_target(out, target, min_frames, max_frames)


def _split_count(total: int, min_frames: int, max_frames: int) -> int:
    min_count = max(1, (total + max_frames - 1) // max_frames)
    max_count = max(1, total // max(1, min_frames))
    if min_count > max_count:
        return min_count
    return min_count


def _nudge_toward_target(parts: list[int], target: int, min_frames: int, max_frames: int) -> list[int]:
    out = list(parts)
    for idx in range(len(out) - 1):
        cur = out[idx]
        nxt = out[idx + 1]
        if cur >= target or nxt <= target:
            continue
        shift = min(target - cur, nxt - target, max_frames - cur, nxt - min_frames)
        if shift > 0:
            out[idx] += shift
            out[idx + 1] -= shift
    return out


def _section_target_sec(section_name: str, max_clip_sec: float) -> float:
    sec = section_name.lower()
    if "chorus" in sec:
        base = 3.5
    elif "pre_chorus" in sec:
        base = 3.8
    elif "bridge" in sec or "outro" in sec:
        base = 5.0
    elif "intro" in sec:
        base = 4.0
    elif "verse" in sec:
        base = 4.2
    else:
        base = 4.0
    return min(max_clip_sec, base)


def _sec_to_frames(sec: float, fps: int, floor: int) -> int:
    return max(floor, int(round(sec * fps)))


def _frame_floor(fps: int) -> int:
    return max(1, int(round(max(1, fps) * 0.25)))


def _clip_id(shot_id: str, idx: int) -> str:
    return f"{shot_id}_C{idx:02d}"
