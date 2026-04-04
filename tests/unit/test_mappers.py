from ai_mv.engines.acestep_1_5_aio.mapper import map_audio_workflow
from ai_mv.engines.flux_2_dev_tti.mapper import map_tti_workflow
from ai_mv.engines.flux_2_dev_ref.mapper import map_flux2_ref_workflow
from ai_mv.engines.wan_2_2_flf2v.mapper import map_wan_workflow
from ai_mv.core.output_paths import audio_prefix, flux2_ref_frame_prefix, master_anchor_prefix, wan_clip_prefix


def test_audio_mapper():
    plan = {
        "tags": "kpop",
        "audio_direction": "K-pop with glossy synth-pop drums, bright lead vocal focus, and a tight dance-pop pulse.",
        "genre_description": "Bright idol-pop with punchy 808s and layered hooks.",
        "lyrics": "we're alive",
        "seed": 1,
        "bpm": 120,
        "duration": 160,
        "keyscale": "A minor",
        "filename_prefix": audio_prefix("run"),
        "quality": "V0",
    }
    out = map_audio_workflow({}, plan)
    nodes = out["node.inputs"]
    assert nodes["94"]["duration"] == 160
    assert nodes["94"]["bpm"] == 120
    assert nodes["94"]["tags"] == "K-Pop: Bright idol-pop with punchy 808s and layered hooks"
    assert nodes["94"]["lyrics"] == "we're alive"
    assert nodes["94"]["keyscale"] == "A minor"


def test_audio_mapper_preserves_non_ascii_lyrics_and_language():
    plan = {
        "tags": "jpop",
        "audio_direction": "Japanese city pop with warm analog keys, mature graceful lead vocal, and a soft neon glide.",
        "genre_description": "Elegant Japanese city-pop with warm analog keys and soft neon glide.",
        "lyrics": "濡れた街灯を追いかけて\nあなたの影を見つけた",
        "seed": 7,
        "bpm": 108,
        "duration": 180,
        "language": "ja",
        "filename_prefix": audio_prefix("run"),
        "quality": "V0",
    }
    out = map_audio_workflow({}, plan)
    nodes = out["node.inputs"]
    assert nodes["94"]["lyrics"] == plan["lyrics"]
    assert nodes["94"]["language"] == "ja"
    assert nodes["94"]["tags"] == "J-Pop: Elegant Japanese city-pop with warm analog keys and soft neon glide"


def test_audio_mapper_normalizes_common_genre_aliases():
    plan = {
        "tags": "uk garage, shuffling drums, female vocal",
        "genre_description": "Tight two-step swing with airy toplines and glossy late-night pads.",
        "lyrics": "hold on",
        "seed": 9,
        "bpm": 132,
        "duration": 150,
        "filename_prefix": audio_prefix("run"),
        "quality": "V0",
    }
    out = map_audio_workflow({}, plan)
    assert out["node.inputs"]["94"]["tags"] == "UK Garage: Tight two-step swing with airy toplines and glossy late-night pads"


def test_audio_mapper_prefers_genre_like_tag_over_performance_tags():
    plan = {
        "tags": "female solo vocal, airy adlibs, drum and bass, glossy pads",
        "genre_description": "Fast breakbeats, sub bass pressure, and a bright melodic lift.",
        "lyrics": "run with me",
        "seed": 11,
        "bpm": 174,
        "duration": 140,
        "filename_prefix": audio_prefix("run"),
        "quality": "V0",
    }
    out = map_audio_workflow({}, plan)
    assert out["node.inputs"]["94"]["tags"] == "Drum and Bass: Fast breakbeats, sub bass pressure, and a bright melodic lift"


def test_tti_mapper():
    cfg = {"render": {"tti_size": "1024x1024"}, "video": {"target": "1920x1080@24"}}
    shot = {
        "prompt_text": "cinematic portrait, silver hair, magical butterflies, glass roses, soft rim light, dream garden",
        "seed": 3,
        "filename_prefix": master_anchor_prefix(),
    }
    out = map_tti_workflow(cfg, shot)
    nodes = out["node.inputs"]
    assert nodes["98:47"]["width"] == 1024
    assert nodes["98:47"]["height"] == 1024
    assert nodes["98:48"]["width"] == 1024
    assert nodes["98:48"]["height"] == 1024
    assert nodes["98:6"]["text"] == shot["prompt_text"]
    assert nodes["98:25"]["noise_seed"] >= 1000


def test_flux2_ref_mapper():
    cfg = {"render": {"ref_size": "1024x576", "tti_size": "1280x720"}, "video": {"target": "1920x1080@24"}}
    item = {
        "shot_id": "s_001",
        "frame_idx": 0,
        "frame_name": "start",
        "ref": "a.png",
        "prompt_text": "A European girl with a heartfelt smile in an endless blooming summer field.",
        "negative_prompt": "blurry, low detail",
        "shot_type": "CHAR_MASTER",
        "style_ref": "refs/front.png",
        "filename_prefix": flux2_ref_frame_prefix("s_001", sequence_index=1),
    }
    out = map_flux2_ref_workflow(cfg, item)
    nodes = out["node.inputs"]
    assert nodes["46"]["image"] == "a.png"
    assert nodes["68:47"]["width"] == 1024
    assert nodes["68:47"]["height"] == 576
    assert nodes["68:48"]["width"] == 1024
    assert nodes["68:48"]["height"] == 576
    assert nodes["68:6"]["text"] == item["prompt_text"]
    assert nodes["68:25"]["noise_seed"] > 2000


def test_wan_mapper():
    cfg = {"render": {"wan_size": "640x640"}, "video": {"target": "1920x1080@24"}}
    clip = {
        "shot_id": "s_001",
        "start": "a.png",
        "end": "b.png",
        "fps": 24,
        "frames": 96,
        "energy": "normal",
        "positive_prompt": "A kitten made of ice crystals wakes and transforms into a giant beast.",
        "negative_prompt": "blur",
        "wan_size": "640x640",
        "filename_prefix": wan_clip_prefix("s_001", "s_002", start_index=1, end_index=2),
    }
    out = map_wan_workflow(cfg, clip)
    nodes = out["node.inputs"]
    assert nodes["81"]["length"] == 96
    assert nodes["81"]["width"] == 640
    assert "start_image" not in nodes["81"]
    assert "end_image" not in nodes["81"]
