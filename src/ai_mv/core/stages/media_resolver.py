from __future__ import annotations

from pathlib import Path


def build_merge_plan(payload: dict) -> dict:
    clips = payload.get("clips", [])
    return {"ordered": [x["video"] for x in clips]}


def resolve_clip_paths(names: list[str], config: dict, run_dir: Path) -> list[Path]:
    roots = [Path("."), run_dir]
    comfy_out = str(config.get("integrations", {}).get("comfyui_output_dir", "")).strip()
    if comfy_out:
        roots.append(Path(comfy_out))
    out: list[Path] = []
    for name in names:
        p = Path(str(name))
        found = p if p.exists() else _search_roots(roots, p)
        if found:
            out.append(found)
    return out


def resolve_audio_path(music_file: str, config: dict) -> Path:
    candidate = Path(music_file) if music_file else Path(config.get("audio", {}).get("source_wav", "master.wav"))
    if candidate.exists():
        return candidate.resolve()
    comfy_out = str(config.get("integrations", {}).get("comfyui_output_dir", "")).strip()
    if comfy_out and (Path(comfy_out) / candidate).exists():
        return (Path(comfy_out) / candidate).resolve()
    return candidate


def _search_roots(roots: list[Path], rel: Path) -> Path | None:
    for root in roots:
        cand = (root / rel).resolve()
        if cand.exists() and cand.suffix.lower() in {".mp4", ".mov", ".mkv"}:
            return cand
    return None

