from __future__ import annotations

from ai_mv.core.contracts.errors import ComfyRequestError


def pick_audio_file(files: list[str]) -> str:
    return _pick_single(files, {".wav", ".mp3", ".flac", ".m4a"}, "audio")


def pick_image_file(files: list[str], label: str) -> str:
    return _pick_single(files, {".png", ".jpg", ".jpeg", ".webp"}, label)


def pick_video_file(files: list[str], label: str) -> str:
    return _pick_single(files, {".mp4", ".mov", ".mkv", ".webm"}, label)


def _pick_single(files: list[str], exts: set[str], label: str) -> str:
    matches = [str(f) for f in files if _has_ext(f, exts)]
    if not matches:
        raise ComfyRequestError(f"{label} output file not found")
    if len(matches) != 1:
        raise ComfyRequestError(f"{label} output file count mismatch: {len(matches)}")
    return matches[0]


def _has_ext(path: str, exts: set[str]) -> bool:
    low = str(path).lower()
    return any(low.endswith(ext) for ext in exts)
