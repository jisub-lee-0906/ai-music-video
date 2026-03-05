from __future__ import annotations

import shutil
from pathlib import Path

import requests

from ai_mv.core.contracts.errors import MediaValidationError

PROJECT_ROOT = Path(__file__).resolve().parents[3]


def abs_path(path: str) -> str:
    return str(Path(path).resolve())


def resolve_project_path(path: str) -> Path:
    p = Path(path)
    if p.is_absolute():
        return p
    return (PROJECT_ROOT / p).resolve()


def stage_image_for_comfy(config: dict, image_ref: str) -> str:
    ref = str(image_ref or "").strip()
    if not ref:
        raise MediaValidationError("image ref is empty")
    strict = bool(config.get("integrations", {}).get("strict_remote", False))
    if not strict:
        return Path(ref).as_posix()
    src = _resolve_image_source(config, ref)
    if not src:
        src = _fetch_from_comfy_output(config, ref)
    if not src:
        raise MediaValidationError(f"image source not found: {ref}")
    uploaded = _upload_to_comfy_input(config, src, ref)
    if uploaded:
        return uploaded
    dst = _resolve_comfy_input(config) / Path(ref)
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)
    if not dst.exists():
        raise MediaValidationError(f"failed to stage image: {dst.as_posix()}")
    return Path(ref).as_posix()


def _resolve_image_source(config: dict, ref: str) -> Path | None:
    p = Path(ref)
    if p.exists():
        return p.resolve()
    out = str(config.get("integrations", {}).get("comfyui_output_dir", "")).strip()
    if out and (Path(out) / p).exists():
        return (Path(out) / p).resolve()
    if out and (Path(out) / p.name).exists():
        return (Path(out) / p.name).resolve()
    return None


def _resolve_comfy_input(config: dict) -> Path:
    inp = str(config.get("integrations", {}).get("comfyui_input_dir", "")).strip()
    if inp:
        return Path(inp).resolve()
    return (PROJECT_ROOT / "input").resolve()


def _fetch_from_comfy_output(config: dict, ref: str) -> Path | None:
    base = str(config.get("integrations", {}).get("comfyui_base_url", "")).rstrip("/")
    if not base:
        return None
    rel = Path(ref).as_posix().strip("/")
    name = Path(rel).name
    sub = "" if "/" not in rel else rel.rsplit("/", 1)[0]
    out = _resolve_comfy_input(config) / "_staged_from_output"
    out.mkdir(parents=True, exist_ok=True)
    dst = out / name
    if _download_view(base, name, sub, dst):
        return dst
    if sub and _download_view(base, name, "", dst):
        return dst
    return None


def _download_view(base: str, filename: str, subfolder: str, dst: Path) -> bool:
    params = {"filename": filename, "subfolder": subfolder, "type": "output"}
    try:
        res = requests.get(f"{base}/view", params=params, timeout=20)
    except Exception:
        return False
    if res.status_code != 200 or not res.content:
        return False
    dst.write_bytes(res.content)
    return True


def _upload_to_comfy_input(config: dict, src: Path, ref: str) -> str:
    base = str(config.get("integrations", {}).get("comfyui_base_url", "")).rstrip("/")
    if not base:
        return ""
    sub = Path(ref).parent.as_posix()
    data = {"type": "input", "overwrite": "true"}
    if sub and sub != ".":
        data["subfolder"] = sub
    try:
        with src.open("rb") as fp:
            res = requests.post(
                f"{base}/upload/image",
                data=data,
                files={"image": (src.name, fp, "application/octet-stream")},
                timeout=30,
            )
        if res.status_code >= 400:
            return ""
        body = res.json() if res.content else {}
    except Exception:
        return ""
    name = str(body.get("name") or body.get("filename") or src.name).strip()
    folder = str(body.get("subfolder", "")).strip("/\\")
    return f"{folder}/{name}" if folder else name

