from pathlib import Path

import pytest

from ai_mv.core.contracts.errors import ComfyRequestError
from ai_mv.core.workflow_names import FLUX2_KEYFRAME_WORKFLOW, FLUX2_STILL_WORKFLOW
from ai_mv.engines.flux2_image.runner import run_flux2_still


def test_run_flux2_still_recovers_when_comfy_history_outputs_are_missing(tmp_path, monkeypatch):
    cfg = _config(tmp_path)
    out = tmp_path / "output" / "prompt_lab" / "flux2_track_a" / "batch-1"
    out.mkdir(parents=True)
    expected = out / "F001_A1_s1001_00001_.png"
    expected.write_bytes(b"png")

    monkeypatch.setattr(
        "ai_mv.engines.flux2_image.runner.run_workflow",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(ComfyRequestError("prompt_id=abc: Comfy history outputs missing")),
    )

    image_path = run_flux2_still(
        cfg,
        {
            "shot_id": "F001",
            "positive_prompt": "prompt",
            "filename_prefix": "prompt_lab/flux2_track_a/batch-1/F001_A1_s1001",
            "seed": 1001,
            "flux2_size": "1280x720",
        },
    )

    assert image_path == str(expected.resolve())


def test_run_flux2_still_keeps_white_background_identity_anchor_on_tti_even_if_reference_leaks(tmp_path, monkeypatch):
    cfg = _config(tmp_path)
    calls = []

    def _fake_run_workflow(_config, workflow_name, mapping, required_inputs):
        calls.append(
            {
                "workflow_name": workflow_name,
                "mapping": mapping,
                "required_inputs": required_inputs,
            }
        )
        return {"files": ["ANCHOR_CHARACTER_UPPER_BODY.png"]}

    monkeypatch.setattr("ai_mv.engines.flux2_image.runner.run_workflow", _fake_run_workflow)
    monkeypatch.setattr(
        "ai_mv.engines.flux2_image.runner.resolve_generated_file",
        lambda _config, image_name, _extensions, _kind: tmp_path / "output" / image_name,
    )

    image_path = run_flux2_still(
        cfg,
        {
            "shot_id": "ANCHOR_CHARACTER_UPPER_BODY",
            "positive_prompt": "upper-body model card, pure white seamless background",
            "filename_prefix": "anchors/ANCHOR_CHARACTER_UPPER_BODY",
            "workflow_target": "image_flux2_text_to_image",
            "reference_image": "D:/old/world-anchor.png",
        },
    )

    assert image_path.endswith("ANCHOR_CHARACTER_UPPER_BODY.png")
    assert calls[0]["workflow_name"] == FLUX2_STILL_WORKFLOW
    assert "LoadImage" not in calls[0]["required_inputs"]
    node_inputs = calls[0]["mapping"]["node.inputs"]
    assert all("image" not in value for value in node_inputs.values())


def test_run_flux2_still_routes_keyframe_to_flux_reference_when_reference_image_is_present(tmp_path, monkeypatch):
    cfg = _config(tmp_path)
    calls = []

    def _fake_run_workflow(_config, workflow_name, mapping, required_inputs):
        calls.append(
            {
                "workflow_name": workflow_name,
                "mapping": mapping,
                "required_inputs": required_inputs,
            }
        )
        return {"files": ["S001.png"]}

    monkeypatch.setattr("ai_mv.engines.flux2_image.runner.run_workflow", _fake_run_workflow)
    monkeypatch.setattr("ai_mv.engines.flux2_image.runner.stage_image_for_comfy", lambda _config, image: "ANCHOR_CHARACTER_UPPER_BODY.png")
    monkeypatch.setattr(
        "ai_mv.engines.flux2_image.runner.resolve_generated_file",
        lambda _config, image_name, _extensions, _kind: tmp_path / "output" / image_name,
    )

    run_flux2_still(
        cfg,
        {
            "shot_id": "S001",
            "positive_prompt": "same character in neon story keyframe",
            "filename_prefix": "stills/S001",
            "workflow_target": "image_flux2_reference_image",
            "reference_image": "D:/renders/ANCHOR_CHARACTER_UPPER_BODY.png",
        },
    )

    assert calls[0]["workflow_name"] == FLUX2_KEYFRAME_WORKFLOW
    assert calls[0]["required_inputs"]["LoadImage"] == ["image"]
    image_inputs = [value["image"] for value in calls[0]["mapping"]["node.inputs"].values() if isinstance(value, dict) and "image" in value]
    assert image_inputs == ["ANCHOR_CHARACTER_UPPER_BODY.png"]


def _config(tmp_path: Path) -> dict:
    inp = tmp_path / "input"
    out = tmp_path / "output"
    inp.mkdir()
    out.mkdir(exist_ok=True)
    return {
        "integrations": {
            "comfyui_base_url": "http://127.0.0.1:8000",
            "comfyui_input_dir": str(inp),
            "comfyui_output_dir": str(out),
            "workflows_dir": "workflows",
        },
        "render": {"flux2_size": "1280x720"},
        "video": {"target": "1920x1080@24"},
    }
