from __future__ import annotations

from pathlib import Path

from ai_mv.core.artifacts.paths import run_file
from ai_mv.core.contracts.stage_io import StageInput, StageOutput
from ai_mv.core.stages.ffmpeg_muxer import run_ffmpeg_mux
from ai_mv.utils.path_utils import resolve_generated_file


def run_assemble_mv(stage_input: StageInput) -> StageOutput:
    clips = _resolve_clip_results(stage_input.config, stage_input.payload)
    audio = Path(
        resolve_generated_file(
            stage_input.config,
            str(stage_input.payload.get("music_file", "")).strip(),
            {".wav", ".mp3", ".flac", ".m4a"},
            "audio",
        )
    )
    final_video = run_file(stage_input.run_id, "final/final_mv.mp4")
    ok = run_ffmpeg_mux(clips, audio, final_video, stage_input.config)
    if not ok:
        raise RuntimeError("ffmpeg assemble failed")
    return StageOutput(
        "assemble_mv",
        "done",
        {
            "final_video": str(final_video),
            "review_inputs": {
                "music_file": str(stage_input.payload.get("music_file", "")).strip(),
                "clip_results": list(stage_input.payload.get("clip_results", [])),
                "final_video": str(final_video),
            },
        },
        [str(final_video)],
    )


def _resolve_clip_results(config: dict, payload: dict) -> list[Path]:
    out: list[Path] = []
    for row in payload.get("clip_results", []):
        if not isinstance(row, dict):
            continue
        video = str(row.get("video", "")).strip()
        if not video:
            continue
        out.append(Path(resolve_generated_file(config, video, {".mp4", ".mov", ".mkv", ".webm"}, "video")))
    if not out:
        raise RuntimeError("assemble requires at least one rendered clip")
    return out
