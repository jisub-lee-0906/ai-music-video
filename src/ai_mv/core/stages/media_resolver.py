from __future__ import annotations

from pathlib import Path

from ai_mv.utils.path_utils import resolve_generated_file


def build_merge_plan(payload: dict, audio_duration_sec: float | None = None) -> dict:
    clips = [row for row in payload.get("clips", []) if isinstance(row, dict)]
    clip_by_shot = {str(row.get("shot_id", "")).strip(): str(row.get("video", "")).strip() for row in clips}
    refs = {
        str(row.get("shot_id", "")).strip(): str(row.get("end", "")).strip()
        for row in payload.get("flux2_ref_images", [])
        if isinstance(row, dict)
    }
    ref_items = [
        row
        for row in payload.get("prompt_plan", {}).get("ref_items", [])
        if isinstance(row, dict) and str(row.get("shot_id", "")).strip()
    ]
    shots = {
        str(row.get("shot_id", "")).strip(): row
        for row in ref_items
    }
    chains = [row for row in payload.get("prompt_plan", {}).get("wan_items", []) if isinstance(row, dict)]
    if not ref_items:
        return {"ordered": []}
    if not chains:
        first_ref_id = str(ref_items[0].get("shot_id", "")).strip()
        first_ref = refs.get(first_ref_id, "")
        if not first_ref:
            return {"ordered": []}
        total = max(0.0, float(audio_duration_sec or 0.0))
        return {
            "ordered": [
                {"kind": "still", "image": first_ref, "duration_sec": round(total, 3), "label": "full_hold"}
            ]
        }

    ordered: list[dict] = []
    first_ref_id = str(ref_items[0].get("shot_id", "")).strip()
    first_ref = refs.get(first_ref_id, "")
    first_shot = shots.get(first_ref_id, {})
    head_hold = max(0.0, float(first_shot.get("start_sec", 0.0) or 0.0))
    if first_ref and head_hold > 0.01:
        ordered.append({"kind": "still", "image": first_ref, "duration_sec": round(head_hold, 3), "label": "head_hold"})

    for chain in chains:
        shot_id = str(chain.get("shot_id", "")).strip()
        video = clip_by_shot.get(shot_id, "")
        if video:
            ordered.append({"kind": "video", "path": video, "label": shot_id})

    last_ref_id = str(ref_items[-1].get("shot_id", "")).strip()
    last_ref = refs.get(last_ref_id, "")
    last_shot = shots.get(last_ref_id, {})
    tail_start = float(last_shot.get("start_sec", 0.0) or 0.0)
    tail_hold = max(0.0, float(audio_duration_sec or 0.0) - tail_start)
    if last_ref and tail_hold > 0.01:
        ordered.append({"kind": "still", "image": last_ref, "duration_sec": round(tail_hold, 3), "label": "tail_hold"})
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
