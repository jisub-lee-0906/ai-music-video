from ai_mv.engines.acestep_1_5_split.mapper import map_audio_workflow
from ai_mv.engines.flux_1_dev_tti.mapper import map_tti_workflow
from ai_mv.engines.flux_1_dev_uso.mapper import map_uso_workflow
from ai_mv.engines.wan_2_2_flf2v.mapper import map_wan_workflow


def test_audio_mapper():
    plan = {
        "tags": "kpop",
        "lyrics": "la",
        "seed": 1,
        "bpm": 120,
        "duration": 160,
        "filename_prefix": "audio/run/music",
        "quality": "V0",
    }
    out = map_audio_workflow({}, plan)
    nodes = out["node.inputs"]
    assert nodes["94"]["duration"] == 160
    assert nodes["94"]["bpm"] == 120


def test_tti_mapper():
    cfg = {"render": {"tti_size": "1024x576"}}
    shot = {"prompt": "p", "negative_prompt": "n", "seed": 3, "filename_prefix": "anchors/s_001_a"}
    out = map_tti_workflow(cfg, shot)
    nodes = out["node.inputs"]
    assert nodes["27"]["width"] == 1024
    assert nodes["27"]["height"] == 576


def test_uso_mapper():
    cfg = {"render": {"uso_size": "1024x576"}}
    item = {
        "shot_id": "s_001",
        "frame_idx": 0,
        "frame_name": "start",
        "ref": "a.png",
        "shot_type": "CHAR_MASTER",
        "style_ref": "refs/front.png",
        "style_guidance": "clean mv look",
        "delta": "small pose shift",
        "filename_prefix": "uso/s_001_start",
    }
    out = map_uso_workflow(cfg, item)
    nodes = out["node.inputs"]
    assert nodes["47"]["image"] == "a.png"
    assert nodes["112:110"]["width"] == 1024


def test_wan_mapper():
    cfg = {"render": {"wan_size": "640x360"}}
    clip = {
        "shot_id": "s_001",
        "start": "a.png",
        "end": "b.png",
        "fps": 24,
        "frames": 96,
        "energy": "mid",
        "prompt": "mv motion",
        "negative_prompt": "blur",
        "wan_size": "640x360",
        "seed_offset": 0,
        "filename_prefix": "clips/s_001",
    }
    out = map_wan_workflow(cfg, clip)
    nodes = out["node.inputs"]
    assert nodes["81"]["length"] == 96
    assert nodes["81"]["width"] == 640
