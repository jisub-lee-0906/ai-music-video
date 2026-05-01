from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

from ai_mv.core.contracts.stage_io import StageInput, StageOutput
from ai_mv.utils.path_utils import resolve_generated_file
from ai_mv.utils.time_utils import ffprobe_duration

_VIDEO_EXTS = {".mp4", ".mov", ".mkv", ".webm"}
_AUDIO_EXTS = {".wav", ".mp3", ".flac", ".m4a"}
_EXCESSIVE_CLONE_TAIL_RATIO = 0.25


def run_repair_audio_video_sync(stage_input: StageInput) -> StageOutput:
    payload = stage_input.payload if isinstance(stage_input.payload, dict) else {}
    final_video_ref = str(payload.get("final_video", "")).strip()
    music_file_ref = str(payload.get("music_file", "")).strip()
    passthrough = {
        "final_video": final_video_ref,
        "music_file": music_file_ref,
    }
    if not final_video_ref or not music_file_ref:
        return StageOutput("repair_audio_video_sync", "done", passthrough, [])

    try:
        final_video = Path(resolve_generated_file(stage_input.config, final_video_ref, _VIDEO_EXTS, "video"))
        music_file = Path(resolve_generated_file(stage_input.config, music_file_ref, _AUDIO_EXTS, "audio"))
    except Exception:
        return StageOutput("repair_audio_video_sync", "done", passthrough, [])

    video_duration = ffprobe_duration(final_video)
    audio_duration = ffprobe_duration(music_file)
    if video_duration <= 0 or audio_duration <= 0:
        return StageOutput("repair_audio_video_sync", "done", {"final_video": str(final_video), "music_file": str(music_file)}, [])

    repaired_video = final_video.with_name(f"{final_video.stem}_synced{final_video.suffix}")
    if not _repair_sync(final_video, music_file, repaired_video, video_duration=video_duration, audio_duration=audio_duration):
        return StageOutput("repair_audio_video_sync", "done", {"final_video": str(final_video), "music_file": str(music_file)}, [])
    sync_repair_summary = _sync_repair_summary(video_duration=video_duration, audio_duration=audio_duration)
    return StageOutput(
        "repair_audio_video_sync",
        "done",
        {
            "final_video": str(repaired_video),
            "music_file": str(music_file),
            "sync_repair_summary": sync_repair_summary,
        },
        [str(repaired_video)],
    )



def _sync_repair_summary(*, video_duration: float, audio_duration: float) -> dict:
    output_duration = max(audio_duration, 0.001)
    clone_tail_sec = max(audio_duration - video_duration, 0.0)
    clone_tail_ratio = clone_tail_sec / output_duration if output_duration > 0 else 0.0
    if clone_tail_sec > 0:
        repair_strategy = "clone_tail_pad"
    elif video_duration > audio_duration:
        repair_strategy = "trim_to_audio"
    else:
        repair_strategy = "remux_to_audio"
    return {
        "input_video_duration_sec": round(video_duration, 3),
        "audio_duration_sec": round(audio_duration, 3),
        "output_duration_sec": round(output_duration, 3),
        "clone_tail_sec": round(clone_tail_sec, 3),
        "clone_tail_ratio": round(clone_tail_ratio, 3),
        "clone_tail_excessive": clone_tail_ratio > _EXCESSIVE_CLONE_TAIL_RATIO,
        "repair_strategy": repair_strategy,
    }



def _repair_sync(final_video: Path, music_file: Path, output_video: Path, *, video_duration: float, audio_duration: float) -> bool:
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        return False
    output_video.parent.mkdir(parents=True, exist_ok=True)
    duration = max(audio_duration, 0.001)
    if video_duration < audio_duration:
        pad_duration = max(audio_duration - video_duration, 0.0)
        filter_graph = f"[0:v]tpad=stop_mode=clone:stop_duration={pad_duration:.3f},trim=duration={duration:.3f},setpts=PTS-STARTPTS[v]"
    else:
        filter_graph = f"[0:v]trim=duration={duration:.3f},setpts=PTS-STARTPTS[v]"
    cmd = [
        ffmpeg,
        "-y",
        "-i",
        str(final_video),
        "-i",
        str(music_file),
        "-filter_complex",
        filter_graph,
        "-map",
        "[v]",
        "-map",
        "1:a",
        "-c:v",
        "libx264",
        "-pix_fmt",
        "yuv420p",
        "-c:a",
        "aac",
        "-t",
        f"{duration:.3f}",
        str(output_video),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, check=False)
    return result.returncode == 0 and output_video.exists()
