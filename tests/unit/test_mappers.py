from ai_mv.engines.acestep_1_5_split.mapper import map_audio_workflow
from ai_mv.engines.flux_1_dev_tti.mapper import map_tti_workflow
from ai_mv.engines.flux_1_dev_uso.mapper import map_uso_workflow
from ai_mv.engines.wan_2_2_flf2v.mapper import map_wan_workflow


def test_audio_mapper():
    plan = {"tags": "kpop", "lyrics": "la", "seed": 1, "bpm": 120, "duration": 160}
    out = map_audio_workflow({}, plan)
    assert out["audio.duration"] == 160
    assert out["audio.bpm"] == 120


def test_tti_mapper():
    cfg = {"render": {"tti_size": "1024x576"}}
    shot = {"prompt": "p", "negative_prompt": "n", "seed": 3}
    out = map_tti_workflow(cfg, shot)
    assert out["video.width"] == 1024
    assert out["video.height"] == 576


def test_uso_mapper():
    cfg = {"render": {"uso_size": "1024x576"}}
    item = {"shot_id": "s_001", "ref": "a.png"}
    out = map_uso_workflow(cfg, item)
    assert out["shot.reference_image"] == "a.png"
    assert out["video.width"] == 1024


def test_wan_mapper():
    cfg = {"render": {"wan_size": "640x360"}}
    clip = {"shot_id": "s_001", "start": "a.png", "end": "b.png", "fps": 24, "frames": 96}
    out = map_wan_workflow(cfg, clip)
    assert out["shot.length_frames"] == 96
    assert out["video.width"] == 640
