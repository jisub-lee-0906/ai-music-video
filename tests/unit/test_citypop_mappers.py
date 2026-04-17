from ai_mv.core.output_paths import ltx_clip_prefix, qwen_still_prefix
from ai_mv.engines.ltx_flf2v.mapper import map_ltx_flf2v_workflow
from ai_mv.engines.ltx_i2v.mapper import map_ltx_i2v_workflow
from ai_mv.engines.ltx_ia2v.mapper import map_ltx_ia2v_workflow
from ai_mv.engines.qwen_image.mapper import map_qwen_workflow


def test_qwen_mapper():
    cfg = {"render": {"qwen_size": "1024x1024"}, "video": {"target": "1920x1080@24"}}
    item = {
        "shot_id": "S001",
        "positive_prompt": "city pop heroine, sunset coast, clean cel shading, film grain",
        "negative_prompt": "ugly, blurry",
        "filename_prefix": qwen_still_prefix("S001"),
        "seed": 1234,
        "steps": 28,
        "cfg": 4.5,
    }
    out = map_qwen_workflow(cfg, item)["node.inputs"]
    assert out["76:6"]["text"] == item["positive_prompt"]
    assert out["76:7"]["text"] == item["negative_prompt"]
    assert out["76:58"]["width"] == 1024
    assert out["76:58"]["height"] == 1024
    assert out["76:3"]["seed"] == 1234
    assert out["60"]["filename_prefix"] == "stills/S001"


def test_ltx_i2v_mapper():
    cfg = {"render": {"ltx_i2v_size": "1280x720", "ltx_fps": 24}, "video": {"target": "1920x1080@24"}}
    item = {
        "shot_id": "S001",
        "image": "stills/S001.png",
        "prompt_seed": "city pop singer in a convertible at blue hour",
        "clip_prompt_seed": "slow windshield drift, preserve subject continuity",
        "positive_prompt": "generated positive prompt",
        "clip_positive_prompt": "slow windshield drift, single continuous motion, no abrupt pose change",
        "negative_prompt": "low quality",
        "duration_sec": 5.0,
        "filename_prefix": ltx_clip_prefix("S001", "i2v"),
    }
    out = map_ltx_i2v_workflow(cfg, item)["node.inputs"]
    assert out["269"]["image"] == "stills/S001.png"
    assert out["267:266"]["value"] == item["clip_prompt_seed"]
    assert out["267:240"]["text"] == item["clip_positive_prompt"]
    assert out["267:257"]["value"] == 1280
    assert out["267:258"]["value"] == 720
    assert out["267:260"]["value"] == 24
    assert out["267:225"]["value"] == 121
    assert out["75"]["filename_prefix"] == "clips/S001_i2v"


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
        "filename_prefix": ltx_clip_prefix("S003", "ia2v"),
    }
    out = map_ltx_ia2v_workflow(cfg, item)["node.inputs"]
    assert out["269"]["image"] == "stills/S003.png"
    assert out["276"]["audio"] == "music/chorus.mp3"
    assert out["340:319"]["value"] == item["clip_prompt_seed"]
    assert out["340:306"]["text"] == item["clip_positive_prompt"]
    assert out["340:323"]["value"] == 24
    assert out["340:331"]["value"] == 6.0
    assert out["340:332"]["start_index"] == 12.5
    assert out["340:332"]["duration"] == 6.0
    assert out["341"]["filename_prefix"] == "clips/S003_ia2v"


def test_ltx_flf2v_mapper():
    cfg = {"render": {"ltx_flf2v_size": "1280x720", "ltx_fps": 24}, "video": {"target": "1920x1080@24"}}
    item = {
        "shot_id": "S005",
        "first_image": "stills/S004.png",
        "last_image": "stills/S005.png",
        "clip_prompt_seed": "bridge transition, bridge escape, tunnel reveal",
        "positive_prompt": "camera drifts from windshield reflection to singer close-up",
        "clip_positive_prompt": "bridge transition, bridge escape, tunnel reveal, matched endpoints, short transition beat, no world change",
        "negative_prompt": "blurry, low quality",
        "duration_sec": 5.0,
        "filename_prefix": ltx_clip_prefix("S005", "flf2v"),
    }
    out = map_ltx_flf2v_workflow(cfg, item)["node.inputs"]
    assert out["31"]["image"] == "stills/S004.png"
    assert out["39"]["image"] == "stills/S005.png"
    assert out["129:128"]["text"] == item["clip_positive_prompt"]
    assert out["129:113"]["value"] == 1280
    assert out["129:98"]["value"] == 720
    assert out["129:114"]["value"] == 24
    assert out["129:102"]["value"] == 121
    assert out["68"]["filename_prefix"] == "clips/S005_flf2v"
