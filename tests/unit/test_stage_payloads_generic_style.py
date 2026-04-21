import pytest

from ai_mv.core.artifacts import manifest as manifest_module
from ai_mv.core.contracts.errors import StageFailure
from ai_mv.core.orchestration.input_gate import validate_stage_input
from ai_mv.core.orchestration.stage_runs import merge_stage_payload


def test_gate_accepts_generic_style_bible_for_stills():
    validate_stage_input(
        "stills",
        {
            "shot_plan": [{"shot_id": "S001", "material_id": "MAT_001"}],
            "material_plan": [{"material_id": "MAT_001", "section_id": "SEC_001"}],
            "render_plan": [{"shot_id": "S001", "material_id": "MAT_001", "render_mode": "i2v"}],
            "style_bible": {"style": "synthwave"},
        },
    )


def test_gate_rejects_legacy_citypop_bible_for_stills():
    with pytest.raises(StageFailure):
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


def test_merge_stage_payload_rejects_legacy_citypop_bible_patch():
    with pytest.raises(StageFailure):
        merge_stage_payload(
            {},
            {"citypop_bible": {"style": "japanese_citypop_80s_90s"}},
            "plan",
        )


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
            "style_lane": "synthwave",
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
    assert manifest["plan"] == {
        "style_lane": "synthwave",
        "style_resolution": {"style_lane": "synthwave"},
        "section_plan": [],
        "material_plan": [],
        "render_plan": [],
    }
    assert manifest["input"] == {"concept_text": "dreamy synthwave neon highway night drive"}
    assert manifest["song"]["master_audio"] == "music.mp3"
    assert "style_bible" not in manifest
    assert "citypop_bible" not in manifest


def test_write_manifest_does_not_backfill_style_bible_from_legacy_citypop_bible(monkeypatch, tmp_path):
    writes: list[tuple[str, dict]] = []

    monkeypatch.setattr(manifest_module, "run_file", lambda run_id, name, scope="run": tmp_path / scope / run_id / name)
    monkeypatch.setattr(manifest_module, "latest_file", lambda name, scope="run": tmp_path / scope / "latest" / name)
    monkeypatch.setattr(manifest_module, "latest_success_file", lambda name, scope="run": tmp_path / scope / "latest_success" / name)
    monkeypatch.setattr(manifest_module, "write_json", lambda path, data: writes.append((str(path), data)))

    manifest_module.write_manifest(
        {"run_id": "run-legacy", "status": "done", "failure_reason": "", "scope": "run"},
        {
            "concept_text": "legacy citypop payload",
            "style_lane": "citypop",
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
    assert manifest["plan"] == {
        "style_lane": "citypop",
        "style_resolution": {"style_lane": "citypop"},
        "section_plan": [],
        "material_plan": [],
        "render_plan": [],
    }
    assert "style_bible" not in manifest
    assert "citypop_bible" not in manifest
