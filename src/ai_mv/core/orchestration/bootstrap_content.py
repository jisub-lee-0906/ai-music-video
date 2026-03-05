from __future__ import annotations

import json
from pathlib import Path

from ai_mv.infra.ollama_client import generate_structured


def ensure_lyrics(config: dict) -> None:
    audio = config["audio"]
    if str(audio["lyrics"]).strip():
        return
    out = generate_structured(config, _lyrics_prompt(config), _lyrics_schema())
    audio["lyrics"] = _render_lyrics_text(out)
    audio["song_title"] = str(out["title"]).strip()
    audio["song_description"] = str(out["description"]).strip()
    audio["lyrics_structured"] = out


def ensure_run_style(config: dict, run_dir: Path) -> None:
    style_file = run_dir / "run_style.json"
    style = config["style"]
    if style_file.exists() and not str(style["guidance"]).strip():
        data = json.loads(style_file.read_text(encoding="utf-8"))
        style["guidance"] = str(data["guidance"]).strip()
        return
    if str(style["guidance"]).strip():
        _write_style(style_file, str(style["guidance"]))
        return
    out = generate_structured(config, _style_prompt(config), _style_schema())
    guidance = str(out["guidance"])
    style["guidance"] = guidance
    _write_style(style_file, guidance)


def _lyrics_prompt(config: dict) -> str:
    audio = config["audio"]
    duration = int(audio["target_duration_sec"])
    tags = ", ".join([str(x) for x in audio["keywords"]])
    style = str(config["style"]["guidance"]).strip()
    return (
        "Return strict JSON with title, description, lyrics_blocks[]. "
        "Each block has section,label,lines[]. "
        "Allowed sections: intro,verse,pre_chorus,chorus,bridge,outro. "
        f"Duration<= {duration}s, tags={tags}, style={style}."
    )


def _lyrics_schema() -> dict:
    block = {
        "type": "object",
        "required": ["section", "label", "lines"],
        "properties": {
            "section": {"type": "string", "enum": ["intro", "verse", "pre_chorus", "chorus", "bridge", "outro"]},
            "label": {"type": "string"},
            "lines": {"type": "array", "items": {"type": "string"}},
        },
    }
    return {
        "type": "object",
        "required": ["title", "description", "lyrics_blocks"],
        "properties": {
            "title": {"type": "string"},
            "description": {"type": "string"},
            "lyrics_blocks": {"type": "array", "items": block},
        },
    }


def _style_prompt(config: dict) -> str:
    profile = str(config["profile"])
    tags = ", ".join([str(x) for x in config["audio"]["keywords"]])
    return f"Return JSON {{\"guidance\":\"...\"}} for MV visual direction. profile={profile}, keywords={tags}."


def _style_schema() -> dict:
    return {"type": "object", "required": ["guidance"], "properties": {"guidance": {"type": "string"}}}


def _write_style(path: Path, guidance: str) -> None:
    body = json.dumps({"guidance": guidance}, ensure_ascii=False, indent=2)
    path.write_text(body, encoding="utf-8")


def _render_lyrics_text(out: dict) -> str:
    blocks = out["lyrics_blocks"]
    if not isinstance(blocks, list) or not blocks:
        raise RuntimeError("lyrics_blocks is empty")
    lines: list[str] = []
    for row in blocks:
        if not isinstance(row, dict):
            raise RuntimeError("invalid lyrics block")
        label = str(row["label"]).strip()
        arr = [str(x).strip() for x in row["lines"] if str(x).strip()]
        if not arr:
            raise RuntimeError(f"empty lyrics lines: {label}")
        lines.append(f"[{label}]")
        lines.extend(arr)
        lines.append("")
    text = "\n".join(lines).strip()
    if not text:
        raise RuntimeError("lyrics text empty")
    return text
