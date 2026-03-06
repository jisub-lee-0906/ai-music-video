from __future__ import annotations

from ai_mv.core.contracts.errors import StageFailure
from ai_mv.core.contracts.stage_io import StageInput, StageOutput
from ai_mv.core.state.state_store import runs_root
from ai_mv.core.stages.ffmpeg_muxer import run_ffmpeg_mux
from ai_mv.core.stages.media_resolver import build_merge_plan, resolve_audio_path, resolve_clip_paths
from ai_mv.utils.text_utils import parse_target
from ai_mv.utils.time_utils import ffprobe_duration


def run_merge_mux(stage_input: StageInput) -> StageOutput:
    merge = build_merge_plan(stage_input.payload)
    run_dir = runs_root() / stage_input.run_id
    try:
        clips = resolve_clip_paths(merge["ordered"], stage_input.config, run_dir)
        audio = resolve_audio_path(stage_input.payload["music_file"], stage_input.config)
    except Exception as exc:
        raise StageFailure(f"merge inputs missing: {exc}") from exc
    final_video = run_dir / "final_mv.mp4"
    if not clips or not audio.exists():
        raise StageFailure("merge inputs missing: clips/audio")
    ok = run_ffmpeg_mux(clips, audio, final_video, stage_input.config)
    if not ok:
        raise StageFailure("ffmpeg merge failed")
    vdur = ffprobe_duration(final_video)
    adur = ffprobe_duration(audio)
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
