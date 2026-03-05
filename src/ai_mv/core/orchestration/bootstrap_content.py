from __future__ import annotations

import base64
import json
from pathlib import Path

from ai_mv.infra.ollama_client import generate_structured
from ai_mv.utils.path_utils import resolve_project_path


def ensure_lyrics(config: dict) -> None:
    audio = config.setdefault("audio", {})
    path = resolve_project_path(str(audio.get("lyrics_file", "lyrics.txt")))
    audio["lyrics_file"] = path.as_posix()
    if path.exists() and path.read_text(encoding="utf-8").strip():
        return
    prompt = _lyrics_prompt(config)
    schema = {"type": "object", "required": ["lyrics"], "properties": {"lyrics": {"type": "string"}}}
    out = generate_structured(config, prompt, schema)
    lyrics = str(out.get("lyrics", "Instrumental section with hook and chorus.")).strip()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(lyrics, encoding="utf-8")


def ensure_references(config: dict) -> None:
    cons = config.setdefault("consistency", {})
    refs = [str(x) for x in cons.get("reference_images", []) if str(x).strip()]
    if refs:
        return
    base = resolve_project_path("refs")
    refs = [(base / n).as_posix() for n in ["subject_front.png", "subject_side.png", "subject_full.png"]]
    for ref in refs:
        _write_tiny_png(Path(ref))
    cons["reference_images"] = refs


def ensure_run_style(config: dict, run_dir: Path) -> None:
    style_file = run_dir / "run_style.json"
    style = config.setdefault("style", {})
    if style_file.exists() and not str(style.get("guidance", "")).strip():
        data = json.loads(style_file.read_text(encoding="utf-8"))
        style["guidance"] = str(data.get("guidance", "")).strip()
        return
    if str(style.get("guidance", "")).strip():
        _write_style(style_file, str(style["guidance"]))
        return
    out = generate_structured(config, _style_prompt(config), _style_schema())
    guidance = str(out.get("guidance", "live-action music video, coherent identity, dynamic camera"))
    style["guidance"] = guidance
    _write_style(style_file, guidance)


def _lyrics_prompt(config: dict) -> str:
    audio = config.get("audio", {})
    duration = int(audio.get("target_duration_sec", 160))
    tags = ", ".join([str(x) for x in audio.get("keywords", [])])
    style = str(config.get("style", {}).get("guidance", "")).strip()
    return f"Create concise MV lyrics JSON {{\"lyrics\":\"...\"}}. Duration<= {duration}s, tags={tags}, style={style}."


def _style_prompt(config: dict) -> str:
    profile = str(config.get("profile", "default"))
    tags = ", ".join([str(x) for x in config.get("audio", {}).get("keywords", [])])
    return f"Return JSON {{\"guidance\":\"...\"}} for MV visual direction. profile={profile}, keywords={tags}."


def _style_schema() -> dict:
    return {"type": "object", "required": ["guidance"], "properties": {"guidance": {"type": "string"}}}


def _write_style(path: Path, guidance: str) -> None:
    body = json.dumps({"guidance": guidance}, ensure_ascii=False, indent=2)
    path.write_text(body, encoding="utf-8")


def _write_tiny_png(path: Path) -> None:
    png = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO6p9xkAAAAASUVORK5CYII="
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(base64.b64decode(png))

