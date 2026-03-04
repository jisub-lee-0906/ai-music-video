from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

from ai_mv.core.contracts.errors import StageFailure
from ai_mv.core.contracts.stage_io import StageInput, StageOutput
from ai_mv.core.state.state_store import runs_root
from ai_mv.engines.wan_2_2_flf2v.mapper import build_concat_plan
from ai_mv.utils.time_utils import ffprobe_duration


def run_merge_mux(stage_input: StageInput) -> StageOutput:
    merge = build_concat_plan(stage_input.config, stage_input.payload)
    run_dir = runs_root() / stage_input.run_id
    clips = _resolve_clip_paths(merge.get("ordered", []), stage_input.config, run_dir)
    audio = _resolve_audio_path(stage_input.payload.get("music_file", ""), stage_input.config)
    final_video = run_dir / "final_mv.mp4"
    strict = bool(stage_input.config.get("limits", {}).get("strict_failure", True))
    if not clips or not audio.exists():
        if strict:
            raise StageFailure("merge inputs missing: clips/audio")
        return StageOutput("merge_mux", "done", {"merge_status": "skipped", "final_video": str(final_video)}, [])
    ok = _run_ffmpeg(clips, audio, final_video, stage_input.config)
    if not ok:
        if strict:
            raise StageFailure("ffmpeg merge failed")
        return StageOutput("merge_mux", "done", {"merge_status": "skipped", "final_video": str(final_video)}, [])
    vdur = ffprobe_duration(final_video)
    adur = ffprobe_duration(audio)
    payload = {"merge_plan": merge, "final_video": str(final_video), "merge_status": "done", "final_duration_sec": vdur,
               "audio_duration_sec": adur}
    return StageOutput("merge_mux", "done", payload, [str(final_video)])


def _resolve_clip_paths(names: list[str], config: dict, run_dir: Path) -> list[Path]:
    roots = [Path("."), run_dir]
    comfy_out = str(config.get("integrations", {}).get("comfyui_output_dir", "")).strip()
    if comfy_out:
        roots.append(Path(comfy_out))
    out: list[Path] = []
    for name in names:
        p = Path(str(name))
        found = p if p.exists() else _search_roots(roots, p)
        if found:
            out.append(found)
    return out


def _search_roots(roots: list[Path], rel: Path) -> Path | None:
    for root in roots:
        cand = (root / rel).resolve()
        if cand.exists() and cand.suffix.lower() in {".mp4", ".mov", ".mkv"}:
            return cand
    return None


def _resolve_audio_path(music_file: str, config: dict) -> Path:
    candidate = Path(music_file) if music_file else Path(config.get("audio", {}).get("source_wav", "master.wav"))
    if candidate.exists():
        return candidate.resolve()
    comfy_out = str(config.get("integrations", {}).get("comfyui_output_dir", "")).strip()
    if comfy_out and (Path(comfy_out) / candidate).exists():
        return (Path(comfy_out) / candidate).resolve()
    return candidate


def _run_ffmpeg(clips: list[Path], audio: Path, out: Path, config: dict) -> bool:
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg or not clips or not audio.exists():
        return False
    out.parent.mkdir(parents=True, exist_ok=True)
    concat = out.parent / "concat.txt"
    concat.write_text("\n".join([f"file '{p.as_posix()}'" for p in clips]), encoding="utf-8")
    target = str(config.get("video", {}).get("target", "1920x1080@24"))
    dims, fps = target.split("@")
    w, h = dims.split("x")
    cmd = [ffmpeg, "-y", "-f", "concat", "-safe", "0", "-i", str(concat), "-i", str(audio), "-vf", f"scale={w}:{h}",
           "-r", str(int(fps)), "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac", "-shortest", str(out)]
    return subprocess.run(cmd, check=False).returncode == 0
