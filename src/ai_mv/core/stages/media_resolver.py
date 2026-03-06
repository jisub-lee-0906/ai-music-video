from __future__ import annotations

from pathlib import Path

from ai_mv.utils.path_utils import resolve_generated_file


def build_merge_plan(payload: dict) -> dict:
    clips = payload["clips"]
    return {"ordered": [x["video"] for x in clips]}


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
