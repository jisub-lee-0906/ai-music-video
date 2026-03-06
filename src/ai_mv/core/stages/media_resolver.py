from __future__ import annotations

from pathlib import Path


def build_merge_plan(payload: dict) -> dict:
    clips = payload["clips"]
    return {"ordered": [x["video"] for x in clips]}


def resolve_clip_paths(names: list[str], config: dict, run_dir: Path) -> list[Path]:
    roots = [Path("."), run_dir]
    roots.append(Path(str(config["integrations"]["comfyui_output_dir"]).strip()))
    out: list[Path] = []
    missing: list[str] = []
    for name in names:
        p = Path(str(name))
        found = p if p.exists() else _search_roots(roots, p)
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
    if not music_file:
        raise RuntimeError("music_file is required")
    candidate = Path(music_file)
    if candidate.exists():
        return candidate.resolve()
    comfy_out = Path(str(config["integrations"]["comfyui_output_dir"]).strip())
    staged = (comfy_out / candidate)
    if staged.exists():
        return staged.resolve()
    raise RuntimeError(f"audio file not found: {music_file}")


def _search_roots(roots: list[Path], rel: Path) -> Path | None:
    for root in roots:
        cand = (root / rel).resolve()
        if cand.exists() and cand.suffix.lower() in {".mp4", ".mov", ".mkv", ".webm"}:
            return cand
    return None
