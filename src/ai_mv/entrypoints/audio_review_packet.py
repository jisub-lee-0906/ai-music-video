from __future__ import annotations

import json

from ai_mv.analysis.audio_review_packet import write_audio_review_packet


def run_audio_review_packet(music_file: str, output_dir: str, sections_json: str = "[]", audio_plan_json: str = "{}") -> int:
    sections = _load_json_list(sections_json)
    audio_plan = _load_json_dict(audio_plan_json)
    written = write_audio_review_packet(
        music_path=music_file,
        output_dir=output_dir,
        sections=sections,
        audio_plan=audio_plan,
    )
    print(f"music_file={music_file}")
    print(written["manifest_path"])
    print(written["rubric_path"])
    print(written["reviewer_notes_path"])
    return 0


def _load_json_list(raw: str) -> list[dict]:
    parsed = json.loads(str(raw or "[]"))
    if not isinstance(parsed, list):
        raise RuntimeError("sections_json must decode to a list")
    return [row for row in parsed if isinstance(row, dict)]


def _load_json_dict(raw: str) -> dict:
    parsed = json.loads(str(raw or "{}"))
    if not isinstance(parsed, dict):
        raise RuntimeError("audio_plan_json must decode to a dict")
    return parsed
