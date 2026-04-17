import pytest

from ai_mv.core.artifacts import manifest as manifest_module
from ai_mv.core.contracts.errors import StageFailure
from ai_mv.core.orchestration.input_gate import validate_stage_input
from ai_mv.core.orchestration.stage_runs import merge_stage_payload


def test_gate_accepts_generic_style_bible_for_stills():
    validate_stage_input(
        "stills",
        {
            "shot_plan": [{"shot_id": "S001"}],
            "render_plan": [{"shot_id": "S001", "render_mode": "i2v"}],
            "style_bible": {"style": "synthwave"},
        },
    )


def test_gate_accepts_legacy_citypop_bible_for_stills_during_transition():
    validate_stage_input(
        "stills",
        {
            "shot_plan": [{"shot_id": "S001"}],
            "render_plan": [{"shot_id": "S001", "render_mode": "i2v"}],
            "citypop_bible": {"style": "japanese_citypop_80s_90s"},
        },
    )


def test_merge_stage_payload_protects_generic_style_bible():
    with pytest.raises(StageFailure):
        merge_stage_payload(
            {"style_bible": {"style": "citypop"}},
            {"style_bible": {"style": "synthwave"}},
            "plan",
        )


def test_merge_stage_payload_preserves_style_bible_without_citypop_alias():
    payload = {}

    merge_stage_payload(
        payload,
        {"style_bible": {"style": "retro_synthwave_nightdrive_80s"}},
        "plan",
    )

    assert payload["style_bible"] == {"style": "retro_synthwave_nightdrive_80s"}
    assert "citypop_bible" not in payload


def test_merge_stage_payload_normalizes_legacy_citypop_bible_patch_to_style_bible():
    payload = {}

    merge_stage_payload(
        payload,
        {"citypop_bible": {"style": "japanese_citypop_80s_90s"}},
        "plan",
    )

    assert payload["style_bible"] == {"style": "japanese_citypop_80s_90s"}
    assert "citypop_bible" not in payload


def test_write_manifest_emits_generic_style_fields(monkeypatch, tmp_path):
    writes: list[tuple[str, dict]] = []

    monkeypatch.setattr(manifest_module, "run_file", lambda run_id, name, scope="run": tmp_path / scope / run_id / name)
    monkeypatch.setattr(manifest_module, "latest_file", lambda name, scope="run": tmp_path / scope / "latest" / name)
    monkeypatch.setattr(manifest_module, "latest_success_file", lambda name, scope="run": tmp_path / scope / "latest_success" / name)
    monkeypatch.setattr(manifest_module, "write_json", lambda path, data: writes.append((str(path), data)))

    manifest_module.write_manifest(
        {"run_id": "run-123", "status": "done", "failure_reason": "", "scope": "run"},
        {
            "concept_text": "dreamy synthwave neon highway night drive",
            "style_name": "synthwave",
            "style_bible": {"style": "retro_synthwave_nightdrive_80s"},
            "workflow_inputs": {},
            "workflow_inputs_preview": {},
            "render_inputs": {},
            "planner_prompts": {},
            "audio_plan": {},
            "audio_map": {},
            "shot_plan": [],
            "render_plan": [],
            "still_results": [],
            "clip_results": [],
            "review_report": {},
            "final_video": "final.mp4",
            "music_file": "music.mp3",
        },
    )

    assert writes
    manifest = writes[0][1]
    assert manifest["style_name"] == "synthwave"
    assert manifest["style_bible"] == {"style": "retro_synthwave_nightdrive_80s"}
    assert "citypop_bible" not in manifest


def test_write_manifest_backfills_style_bible_from_legacy_citypop_bible(monkeypatch, tmp_path):
    writes: list[tuple[str, dict]] = []

    monkeypatch.setattr(manifest_module, "run_file", lambda run_id, name, scope="run": tmp_path / scope / run_id / name)
    monkeypatch.setattr(manifest_module, "latest_file", lambda name, scope="run": tmp_path / scope / "latest" / name)
    monkeypatch.setattr(manifest_module, "latest_success_file", lambda name, scope="run": tmp_path / scope / "latest_success" / name)
    monkeypatch.setattr(manifest_module, "write_json", lambda path, data: writes.append((str(path), data)))

    manifest_module.write_manifest(
        {"run_id": "run-legacy", "status": "done", "failure_reason": "", "scope": "run"},
        {
            "concept_text": "legacy citypop payload",
            "style_name": "citypop",
            "citypop_bible": {"style": "japanese_citypop_80s_90s"},
            "workflow_inputs": {},
            "workflow_inputs_preview": {},
            "render_inputs": {},
            "planner_prompts": {},
            "audio_plan": {},
            "audio_map": {},
            "shot_plan": [],
            "render_plan": [],
            "still_results": [],
            "clip_results": [],
            "review_report": {},
            "final_video": "final.mp4",
            "music_file": "music.mp3",
        },
    )

    manifest = writes[0][1]
    assert manifest["style_bible"] == {"style": "japanese_citypop_80s_90s"}
    assert "citypop_bible" not in manifest
