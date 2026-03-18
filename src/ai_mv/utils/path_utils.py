from __future__ import annotations

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
    src = _resolve_image_source(config, ref)
    if not src:
        raise MediaValidationError(f"image source not found: {ref}")
    rel = _comfy_stage_relpath(ref)
    dst = comfy_input_dir(config) / rel
    if _same_file(src, dst):
        return rel.as_posix()
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)
    if not dst.exists():
        raise MediaValidationError(f"failed to stage image: {dst.as_posix()}")
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
    if (out / p.name).exists():
        return (out / p.name).resolve()
    return None


def _comfy_stage_relpath(ref: str) -> Path:
    path = Path(ref)
    if path.is_absolute():
        return Path(path.name)
    if ".." in path.parts:
        raise MediaValidationError(f"image ref escapes comfy input dir: {ref}")
    return path


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
    for cand in ((out / path), (out / path.name)):
        if cand.exists():
            return cand.resolve()
    return None

