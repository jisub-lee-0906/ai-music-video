from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

from ai_mv.core.contracts.stage_io import StageInput, StageOutput
from ai_mv.core.state.state_store import runs_root
from ai_mv.engines.wan_2_2_flf2v.mapper import build_concat_plan


def run_merge_mux(stage_input: StageInput) -> StageOutput:
    merge = build_concat_plan(stage_input.config, stage_input.payload)
    run_dir = runs_root() / stage_input.run_id
    clips = _resolve_clip_paths(merge.get("ordered", []), stage_input.config, run_dir)
    audio = _resolve_audio_path(stage_input.payload.get("music_file", ""), stage_input.config)
    final_video = run_dir / "final_mv.mp4"
    ok = _run_ffmpeg(clips, audio, final_video, stage_input.config)
    payload = {"merge_plan": merge, "final_video": str(final_video), "merge_status": "done" if ok else "skipped"}
    return StageOutput("merge_mux", "done", payload, [str(final_video)] if ok else [])


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
