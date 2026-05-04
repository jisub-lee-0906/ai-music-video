from ai_mv.core.output_paths import audio_prefix, ltx_clip_prefix, still_prefix
from ai_mv.engines.flux2_image.mapper import map_flux2_workflow
from ai_mv.engines.ltx_ia2v.mapper import map_ltx_ia2v_workflow



def test_flux2_text_to_image_mapper():
    cfg = {"render": {"flux2_size": "1024x1024"}, "video": {"target": "1920x1080@24"}}
    item = {
        "shot_id": "S001",
        "positive_prompt": "city pop heroine, sunset coast, cinematic illustration lighting, film grain",
        "negative_prompt": "ugly, blurry",
        "filename_prefix": still_prefix("S001-run", "S001"),
        "seed": 1234,
        "steps": 28,
        "guidance": 4.5,
    }
    out = map_flux2_workflow(cfg, item)["node.inputs"]
    assert out["98:6"]["text"] == item["positive_prompt"]
    assert out["98:47"]["width"] == 1024
    assert out["98:47"]["height"] == 1024
    assert out["98:48"]["steps"] == 28
    assert out["98:25"]["noise_seed"] == 1234
    assert out["98:26"]["guidance"] == 4.5
    assert out["9"]["filename_prefix"] == "ai_mv/runs/S001-run/stills/shot-S001"



def test_flux2_reference_mapper_uses_reference_image_contract():
    cfg = {"render": {"flux2_size": "1024x1024"}, "video": {"target": "1920x1080@24"}}
    item = {
        "shot_id": "S002",
        "positive_prompt": "same protagonist under station light, locked identity details, single cinematic keyframe",
        "filename_prefix": still_prefix("S002-run", "S002"),
        "seed": 2222,
        "steps": 20,
        "guidance": 3.5,
        "reference_image": "stills/S001.png",
    }
    out = map_flux2_workflow(cfg, item)["node.inputs"]
    assert out["46"]["image"] == "stills/S001.png"
    assert out["68:6"]["text"] == item["positive_prompt"]
    assert out["68:48"]["steps"] == 20
    assert out["68:25"]["noise_seed"] == 2222
    assert out["68:26"]["guidance"] == 3.5
    assert out["9"]["filename_prefix"] == "ai_mv/runs/S002-run/stills/shot-S002"



def test_ltx_ia2v_mapper():
    cfg = {"render": {"ltx_ia2v_size": "1280x720", "ltx_fps": 24}, "video": {"target": "1920x1080@24"}}
    item = {
        "shot_id": "S003",
        "image": "stills/S003.png",
        "audio": "music/chorus.mp3",
        "prompt_seed": "city pop chorus close-up in moving car",
        "clip_prompt_seed": "chorus breakout, stable camera motion, audio-reactive energy",
        "positive_prompt": "generated positive prompt",
        "clip_positive_prompt": "chorus breakout, stable camera motion, audio-reactive energy, stable performer identity",
        "negative_prompt": "low quality",
        "audio_start_sec": 12.5,
        "duration_sec": 6.0,
        "filename_prefix": ltx_clip_prefix("S003-run", "S003", "ia2v"),
    }
    out = map_ltx_ia2v_workflow(cfg, item)["node.inputs"]
    assert out["269"]["image"] == "stills/S003.png"
    assert out["276"]["audio"] == "music/chorus.mp3"
    assert out["340:319"]["value"] == item["prompt_seed"]
    assert out["340:306"]["text"] == item["positive_prompt"]
    assert out["340:323"]["value"] == 24
    assert out["340:331"]["value"] == 6.0
    assert out["340:332"]["start_index"] == 12.5
    assert out["340:332"]["duration"] == 6.0
    assert out["341"]["filename_prefix"] == "ai_mv/runs/S003-run/clips/shot-S003-ia2v"


def test_ltx_ia2v_mapper_treats_legacy_clip_prompt_fields_as_diagnostic_only():
    cfg = {"render": {"ltx_ia2v_size": "1280x720", "ltx_fps": 24}, "video": {"target": "1920x1080@24"}}
    item = {
        "shot_id": "S004",
        "image": "stills/S004.png",
        "audio": "music/chorus.mp3",
        "prompt_seed": "workflow-safe seed label",
        "clip_prompt_seed": "legacy diagnostic city rooftop seed must not drive mapper",
        "positive_prompt": "workflow-safe LTX positive prompt",
        "clip_positive_prompt": "legacy diagnostic city rooftop prompt must not drive mapper",
        "negative_prompt": "low quality",
        "duration_sec": 4.0,
        "filename_prefix": ltx_clip_prefix("S004-run", "S004", "ia2v"),
    }

    out = map_ltx_ia2v_workflow(cfg, item)["node.inputs"]

    assert out["340:319"]["value"] == "workflow-safe seed label"
    assert out["340:306"]["text"] == "workflow-safe LTX positive prompt"
    assert "legacy diagnostic" not in out["340:319"]["value"]
    assert "legacy diagnostic" not in out["340:306"]["text"]


def test_output_path_contract_uses_run_scoped_clean_names():
    assert audio_prefix("mv-smoke-live-20260419-short") == "ai_mv/runs/mv-smoke-live-20260419-short/audio/song"
    assert still_prefix("S001-run", "S001") == "ai_mv/runs/S001-run/stills/shot-S001"
    assert ltx_clip_prefix("S001-run", "S001", "ia2v") == "ai_mv/runs/S001-run/clips/shot-S001-ia2v"
    assert ltx_clip_prefix("S001-run", "S001", "") == "ai_mv/runs/S001-run/clips/shot-S001-ia2v"



def test_output_path_contract_sanitizes_path_traversal_segments():
    assert audio_prefix("../escape") == "ai_mv/runs/escape/audio/song"
    assert still_prefix("safe/run", "../S001") == "ai_mv/runs/safe-run/stills/shot-S001"
    assert ltx_clip_prefix("..\\mix/../run", "S001/../../bad", "../ia2v") == "ai_mv/runs/mix-run/clips/shot-S001-bad-ia2v"
