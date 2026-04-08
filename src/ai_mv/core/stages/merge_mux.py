from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

from ai_mv.core.contracts.errors import StageFailure
from ai_mv.core.contracts.stage_io import StageInput, StageOutput
from ai_mv.core.state.state_store import runs_root
from ai_mv.core.stages.ffmpeg_muxer import run_ffmpeg_mux
from ai_mv.core.stages.media_resolver import build_merge_plan, resolve_audio_path, resolve_clip_paths, resolve_image_path
from ai_mv.utils.text_utils import parse_target
from ai_mv.utils.time_utils import ffprobe_duration


def run_merge_mux(stage_input: StageInput) -> StageOutput:
    run_dir = runs_root() / stage_input.run_id
    try:
        audio = resolve_audio_path(stage_input.payload["music_file"], stage_input.config)
        audio_duration_sec = ffprobe_duration(audio)
        merge = build_merge_plan(stage_input.payload, audio_duration_sec)
        clips = _materialize_merge_entries(merge["ordered"], stage_input.config, run_dir)
    except Exception as exc:
        raise StageFailure(f"merge inputs missing: {exc}") from exc
    final_video = run_dir / "final_mv.mp4"
    if not clips or not audio.exists():
        raise StageFailure("merge inputs missing: clips/audio")
    ok = run_ffmpeg_mux(clips, audio, final_video, stage_input.config)
    if not ok:
        raise StageFailure("ffmpeg merge failed")
    vdur = ffprobe_duration(final_video)
    adur = audio_duration_sec
    _validate_duration_alignment(vdur, adur, stage_input.config)
    payload = {"merge_plan": merge, "final_video": str(final_video), "merge_status": "done", "final_duration_sec": vdur,
               "audio_duration_sec": adur}
    return StageOutput("merge_mux", "done", payload, [str(final_video)])


def _validate_duration_alignment(video_sec: float, audio_sec: float, config: dict) -> None:
    if video_sec <= 0 or audio_sec <= 0:
        raise StageFailure(f"invalid durations: video={video_sec:.3f}s audio={audio_sec:.3f}s")
    fps = parse_target(str(config["video"]["target"]))[2]
    tol = max(0.25, 2.0 / float(max(1, fps)))
    drift = abs(video_sec - audio_sec)
    if drift > tol:
        raise StageFailure(f"duration mismatch: video={video_sec:.3f}s audio={audio_sec:.3f}s tol={tol:.3f}s")


def _materialize_merge_entries(entries: list[dict], config: dict, run_dir: Path) -> list[Path]:
    if not entries:
        return []
    video_names = [str(entry.get("path", "")).strip() for entry in entries if str(entry.get("kind", "")).strip() == "video"]
    resolved_videos = resolve_clip_paths(video_names, config, run_dir) if video_names else []
    video_iter = iter(resolved_videos)
    out: list[Path] = []
    still_dir = run_dir / "merge_stills"
    for index, entry in enumerate(entries, start=1):
        kind = str(entry.get("kind", "")).strip()
        if kind == "video":
            out.append(next(video_iter))
            continue
        if kind != "still":
            continue
        image = resolve_image_path(str(entry.get("image", "")).strip(), config)
        duration_sec = float(entry.get("duration_sec", 0.0) or 0.0)
        if duration_sec <= 0.01:
            continue
        still_dir.mkdir(parents=True, exist_ok=True)
        out_path = still_dir / f"{index:03d}_{str(entry.get('label', 'hold')).strip() or 'hold'}.mp4"
        _render_still_clip(image, duration_sec, out_path, config)
        out.append(out_path)
    return out


def _render_still_clip(image: Path, duration_sec: float, out_path: Path, config: dict) -> None:
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        raise RuntimeError("ffmpeg not found")
    video = config.get("video", {}) if isinstance(config, dict) else {}
    render = config.get("render", {}) if isinstance(config, dict) else {}
    w, h, _ = parse_target(str(video.get("target", "1920x1080@24")))
    try:
        fps = int(render.get("wan_fps", 16)) if isinstance(render, dict) else 16
    except Exception:
        fps = 16
    fps = max(1, fps)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        ffmpeg,
        "-y",
        "-loop",
        "1",
        "-i",
        str(image),
        "-t",
        f"{float(duration_sec):.3f}",
        "-vf",
        f"scale={w}:{h}",
        "-r",
        str(fps),
        "-c:v",
        "libx264",
        "-pix_fmt",
        "yuv420p",
        "-an",
        str(out_path),
    ]
    result = subprocess.run(cmd, check=False, capture_output=True, text=True)
    if result.returncode != 0 or not out_path.exists():
        detail = (result.stderr or "").strip() or (result.stdout or "").strip() or "ffmpeg still render failed"
        raise RuntimeError(f"ffmpeg still render failed: {detail}")
