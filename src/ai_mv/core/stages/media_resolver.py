from __future__ import annotations

from pathlib import Path

from ai_mv.utils.path_utils import resolve_generated_file


def build_merge_plan(payload: dict, audio_duration_sec: float | None = None) -> dict:
    clips = [row for row in payload.get("clips", []) if isinstance(row, dict)]
    if not clips:
        return {"ordered": []}
    clip_by_shot = {str(row.get("shot_id", "")).strip(): str(row.get("video", "")).strip() for row in clips}
    refs = {
        str(row.get("shot_id", "")).strip(): str(row.get("end", "")).strip()
        for row in payload.get("flux2_ref_images", [])
        if isinstance(row, dict)
    }
    shots = {
        str(row.get("shot_id", "")).strip(): row
        for row in payload.get("direction_plan", {}).get("shot_packages", [])
        if isinstance(row, dict)
    }
    chains = [row for row in payload.get("prompt_plan", {}).get("wan_items", []) if isinstance(row, dict)]
    if not chains:
        first_ref_id = next(iter(refs.keys()), "")
        first_ref = refs.get(first_ref_id, "")
        if not first_ref:
            return {"ordered": [path for path in clip_by_shot.values() if path]}
        total = max(0.0, float(audio_duration_sec or 0.0))
        return {
            "ordered": [
                {"kind": "still", "image": first_ref, "duration_sec": round(total, 3), "label": "full_hold"}
            ]
        }

    ordered: list[dict] = []
    first_chain = chains[0]
    first_ref_id = str(first_chain.get("start_ref_shot_id", "")).strip()
    first_ref = refs.get(first_ref_id, "")
    first_shot = shots.get(first_ref_id, {})
    head_gap = max(0.0, float(first_shot.get("start_sec", 0.0) or 0.0))
    first_hold = max(0.0, float(first_shot.get("duration_sec", 0.0) or 0.0))
    if first_ref and head_gap > 0.01:
        ordered.append({"kind": "still", "image": first_ref, "duration_sec": round(head_gap, 3), "label": "head_gap"})
    if first_ref and first_hold > 0.01:
        ordered.append({"kind": "still", "image": first_ref, "duration_sec": round(first_hold, 3), "label": "first_ref_hold"})

    for chain in chains:
        shot_id = str(chain.get("shot_id", "")).strip()
        video = clip_by_shot.get(shot_id, "")
        if video:
            ordered.append({"kind": "video", "path": video, "label": shot_id})

    last_chain = chains[-1]
    last_ref_id = str(last_chain.get("end_ref_shot_id", "")).strip()
    last_ref = refs.get(last_ref_id, "")
    last_shot = shots.get(last_ref_id, {})
    tail_start = float(last_shot.get("end_sec", 0.0) or 0.0)
    tail_gap = max(0.0, float(audio_duration_sec or 0.0) - tail_start)
    if last_ref and tail_gap > 0.01:
        ordered.append({"kind": "still", "image": last_ref, "duration_sec": round(tail_gap, 3), "label": "tail_gap"})
    return {"ordered": ordered}


def resolve_clip_paths(names: list[str], config: dict, run_dir: Path) -> list[Path]:
    roots = _clip_roots(config, run_dir)
    out: list[Path] = []
    missing: list[str] = []
    for name in names:
        found = _resolve_one_clip(name, roots)
        if found:
            out.append(found)
        else:
            missing.append(str(name))
    if missing:
        preview = ", ".join(missing[:5])
        more = f" (+{len(missing)-5} more)" if len(missing) > 5 else ""
        raise RuntimeError(f"clip files not found: {preview}{more}")
    if len(out) != len(names):
        raise RuntimeError(f"clip path count mismatch: expected={len(names)} actual={len(out)}")
    return out


def resolve_audio_path(music_file: str, config: dict) -> Path:
    return resolve_generated_file(config, music_file, {".wav", ".mp3", ".flac", ".m4a"}, "audio")


def resolve_image_path(name: str, config: dict) -> Path:
    return resolve_generated_file(config, name, {".png", ".jpg", ".jpeg", ".webp"}, "image")


def _search_roots(roots: list[Path], rel: Path) -> Path | None:
    for root in roots:
        cand = (root / rel).resolve()
        if cand.exists() and cand.suffix.lower() in {".mp4", ".mov", ".mkv", ".webm"}:
            return cand
    return None


def _clip_roots(config: dict, run_dir: Path) -> list[Path]:
    out = [run_dir.resolve()]
    raw = str(config["integrations"]["comfyui_output_dir"]).strip()
    if raw:
        out.append(Path(raw).resolve())
    return out


def _resolve_one_clip(name: str, roots: list[Path]) -> Path | None:
    p = Path(str(name))
    if p.is_absolute():
        return p.resolve() if _is_video_file(p) else None
    return _search_roots(roots, p)


def _is_video_file(path: Path) -> bool:
    return path.exists() and path.suffix.lower() in {".mp4", ".mov", ".mkv", ".webm"}
