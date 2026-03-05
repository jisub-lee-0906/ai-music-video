from __future__ import annotations

from ai_mv.core.contracts.errors import StageFailure
from ai_mv.core.contracts.stage_io import StageInput, StageOutput
from ai_mv.core.state.state_store import runs_root
from ai_mv.core.stages.ffmpeg_muxer import run_ffmpeg_mux
from ai_mv.core.stages.media_resolver import build_merge_plan, resolve_audio_path, resolve_clip_paths
from ai_mv.utils.time_utils import ffprobe_duration


def run_merge_mux(stage_input: StageInput) -> StageOutput:
    merge = build_merge_plan(stage_input.payload)
    run_dir = runs_root() / stage_input.run_id
    clips = resolve_clip_paths(merge.get("ordered", []), stage_input.config, run_dir)
    audio = resolve_audio_path(stage_input.payload.get("music_file", ""), stage_input.config)
    final_video = run_dir / "final_mv.mp4"
    strict = bool(stage_input.config.get("limits", {}).get("strict_failure", True))
    if not clips or not audio.exists():
        if strict:
            raise StageFailure("merge inputs missing: clips/audio")
        return StageOutput("merge_mux", "done", {"merge_status": "skipped", "final_video": str(final_video)}, [])
    ok = run_ffmpeg_mux(clips, audio, final_video, stage_input.config)
    if not ok:
        if strict:
            raise StageFailure("ffmpeg merge failed")
        return StageOutput("merge_mux", "done", {"merge_status": "skipped", "final_video": str(final_video)}, [])
    vdur = ffprobe_duration(final_video)
    adur = ffprobe_duration(audio)
    payload = {"merge_plan": merge, "final_video": str(final_video), "merge_status": "done", "final_duration_sec": vdur,
               "audio_duration_sec": adur}
    return StageOutput("merge_mux", "done", payload, [str(final_video)])
