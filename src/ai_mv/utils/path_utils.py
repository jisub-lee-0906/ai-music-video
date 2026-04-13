from __future__ import annotations

import hashlib
import shutil
from pathlib import Path

from ai_mv.core.contracts.errors import MediaValidationError
from ai_mv.infra.comfy_local import comfy_input_dir, comfy_output_dir
from ai_mv.utils.project_root import project_root

PROJECT_ROOT = project_root(__file__)


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
    _validate_staging_ref(ref)
    src = _resolve_image_source(config, ref)
    if not src:
        raise MediaValidationError(f"image source not found: {ref}")
    rel = _comfy_stage_relpath(config, src, ref)
    dst = comfy_input_dir(config) / rel
    if _same_file(src, dst):
        return rel.as_posix()
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)
    if not dst.exists():
        raise MediaValidationError(f"failed to stage image: {dst.as_posix()}")
    return rel.as_posix()


def stage_audio_for_comfy(config: dict, audio_ref: str) -> str:
    ref = str(audio_ref or "").strip()
    if not ref:
        raise MediaValidationError("audio ref is empty")
    _validate_staging_ref(ref)
    src = _resolve_audio_source(config, ref)
    if not src:
        raise MediaValidationError(f"audio source not found: {ref}")
    rel = _comfy_stage_relpath(config, src, ref)
    dst = comfy_input_dir(config) / rel
    if _same_file(src, dst):
        return rel.as_posix()
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)
    if not dst.exists():
        raise MediaValidationError(f"failed to stage audio: {dst.as_posix()}")
    return rel.as_posix()


def resolve_generated_file(config: dict, ref: str, exts: set[str], label: str) -> Path:
    path = _resolve_generated_path(config, ref)
    if not path or path.suffix.lower() not in exts:
        raise MediaValidationError(f"{label} file not found: {ref}")
    return path


def _resolve_image_source(config: dict, ref: str) -> Path | None:
    p = Path(ref)
    if p.exists():
        return p.resolve()
    out = comfy_output_dir(config)
    if (out / p).exists():
        return (out / p).resolve()
    return None


def _resolve_audio_source(config: dict, ref: str) -> Path | None:
    p = Path(ref)
    if p.exists():
        return p.resolve()
    out = comfy_output_dir(config)
    if (out / p).exists():
        return (out / p).resolve()
    return None


def _comfy_stage_relpath(config: dict, src: Path, ref: str) -> Path:
    input_root = comfy_input_dir(config).resolve()
    try:
        return src.resolve().relative_to(input_root)
    except ValueError:
        pass
    path = Path(ref)
    if path.is_absolute():
        digest = hashlib.sha1(str(src.resolve()).encode("utf-8")).hexdigest()[:12]
        return Path("_staged") / f"{digest}_{path.name}"
    return path


def _validate_staging_ref(ref: str) -> None:
    path = Path(ref)
    if not path.is_absolute() and ".." in path.parts:
        raise MediaValidationError(f"image ref escapes comfy input dir: {ref}")


def _same_file(src: Path, dst: Path) -> bool:
    try:
        return src.resolve() == dst.resolve()
    except Exception:
        return False


def _resolve_generated_path(config: dict, ref: str) -> Path | None:
    raw = str(ref or "").strip()
    if not raw:
        return None
    path = Path(raw)
    if path.exists():
        return path.resolve()
    out = comfy_output_dir(config)
    for cand in (out / path,):
        if cand.exists():
            return cand.resolve()
    return None

