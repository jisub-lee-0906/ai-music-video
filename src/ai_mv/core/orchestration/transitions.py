from __future__ import annotations

import base64
import json
import hashlib
from pathlib import Path

from ai_mv.core.contracts.errors import PipelineError
from ai_mv.infra.ollama_client import generate_structured
from ai_mv.utils.text_utils import ensure_16_9, parse_size, parse_target


def next_status(current: str, ok: bool) -> str:
    if current == "running" and ok:
        return "running"
    if current == "running" and not ok:
        return "failed"
    return current


def bootstrap_config(config: dict, run_dir: Path) -> dict:
    _apply_profile(config)
    _validate_sizes(config)
    _validate_templates(config)
    if bool(config.get("runtime", {}).get("bootstrap_missing_inputs", True)):
        _ensure_lyrics(config)
        _ensure_references(config)
    _ensure_run_style(config, run_dir)
    return config


def _validate_sizes(config: dict) -> None:
    w, h, _ = parse_target(config.get("video", {}).get("target", "1920x1080@24"))
    ensure_16_9(w, h)
    for key in ("tti_size", "uso_size", "wan_size"):
        rw, rh = parse_size(str(config.get("render", {}).get(key, "1024x576")))
        ensure_16_9(rw, rh)


def _validate_templates(config: dict) -> None:
    wf = Path(config.get("integrations", {}).get("workflows_dir", "workflows"))
    fixed = [
        "audio_ace_step_1_5_tta.api.json",
        "image_flux1_dev_tti.api.json",
        "image_flux1_dev_uso.api.json",
        "video_wan_2_2_flf2v.api.json",
    ]
    for name in fixed:
        if not (wf / name).exists():
            raise PipelineError(f"missing workflow template: {name}")
    hashes = config.get("runtime", {}).get("template_hashes", {})
    if not bool(config.get("runtime", {}).get("template_hash_lock", True)):
        return
    for name, expected in hashes.items():
        p = wf / name
        actual = hashlib.sha256(p.read_bytes()).hexdigest()
        if str(expected) and actual != str(expected):
            raise PipelineError(f"template hash mismatch: {name}")


def _apply_profile(config: dict) -> None:
    name = str(config.get("profile", "")).strip()
    if not name:
        return
    fname = name if name.endswith(".yaml") else f"{name}.yaml"
    path = Path("configs") / "profiles" / fname
    if not path.exists():
        raise PipelineError(f"missing profile config: {path.as_posix()}")
    import yaml

    profile = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    _deep_merge(config, profile)
    config["profile"] = name


def _deep_merge(base: dict, patch: dict) -> None:
    for key, val in patch.items():
        if isinstance(val, dict) and isinstance(base.get(key), dict):
            _deep_merge(base[key], val)
        else:
            base[key] = val


def _ensure_lyrics(config: dict) -> None:
    audio = config.setdefault("audio", {})
    path = Path(str(audio.get("lyrics_file", "lyrics.txt")))
    if path.exists() and path.read_text(encoding="utf-8").strip():
        return
    duration = int(audio.get("target_duration_sec", 160))
    tags = ", ".join([str(x) for x in audio.get("keywords", [])])
    style = str(config.get("style", {}).get("guidance", "")).strip()
    prompt = (
        "Create concise MV lyrics. Return JSON {\"lyrics\": \"...\"}. "
        f"Duration<= {duration}s, tags={tags}, style={style}."
    )
    schema = {"type": "object", "required": ["lyrics"], "properties": {"lyrics": {"type": "string"}}}
    out = generate_structured(config, prompt, schema)
    lyrics = str(out.get("lyrics", "Instrumental section with hook and chorus.")).strip()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(lyrics, encoding="utf-8")
    audio["lyrics_file"] = str(path)


def _ensure_references(config: dict) -> None:
    cons = config.setdefault("consistency", {})
    refs = [str(x) for x in cons.get("reference_images", []) if str(x).strip()]
    if refs:
        return
    base = Path("refs")
    names = ["subject_front.png", "subject_side.png", "subject_full.png"]
    refs = [str(base / n) for n in names]
    for ref in refs:
        _write_tiny_png(Path(ref))
    cons["reference_images"] = refs


def _write_tiny_png(path: Path) -> None:
    png = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO6p9xkAAAAASUVORK5CYII="
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(base64.b64decode(png))


def _ensure_run_style(config: dict, run_dir: Path) -> None:
    style_file = run_dir / "run_style.json"
    style = config.setdefault("style", {})
    if style_file.exists() and not str(style.get("guidance", "")).strip():
        data = json.loads(style_file.read_text(encoding="utf-8"))
        style["guidance"] = str(data.get("guidance", "")).strip()
        return
    if str(style.get("guidance", "")).strip():
        style_file.write_text(json.dumps({"guidance": style["guidance"]}, ensure_ascii=False, indent=2), encoding="utf-8")
        return
    profile = str(config.get("profile", "default"))
    tags = ", ".join([str(x) for x in config.get("audio", {}).get("keywords", [])])
    prompt = (
        "Return JSON {\"guidance\":\"...\"} for music video visual direction. "
        f"profile={profile}, keywords={tags}."
    )
    schema = {"type": "object", "required": ["guidance"], "properties": {"guidance": {"type": "string"}}}
    out = generate_structured(config, prompt, schema)
    guidance = str(out.get("guidance", "live-action music video, coherent identity, dynamic camera"))
    style["guidance"] = guidance
    style_file.write_text(json.dumps({"guidance": guidance}, ensure_ascii=False, indent=2), encoding="utf-8")
