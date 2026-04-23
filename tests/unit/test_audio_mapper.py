import ai_mv.engines.acestep_1_5_aio.mapper as audio_mapper



def test_map_audio_workflow_preserves_blank_language_when_unset():
    out = audio_mapper.map_audio_workflow(
        {},
        {
            "genre_description": "Synthwave: pulsing analog pads and a glossy nocturnal lead vocal.",
            "lyrics": "Streetlight flickers\nRearview ghosts",
            "seed": 41,
            "bpm": 112,
            "duration": 150,
            "language": "",
            "filename_prefix": "run_audio",
            "quality": "V0",
        },
    )

    assert out["node.inputs"][audio_mapper.AUDIO_TEXT]["language"] == ""



def test_map_audio_workflow_preserves_explicit_supported_language():
    out = audio_mapper.map_audio_workflow(
        {},
        {
            "genre_description": "K-Indie: shimmering guitars and a warm intimate vocal.",
            "lyrics": "불빛 사이로\n천천히 걸어가",
            "seed": 52,
            "bpm": 96,
            "duration": 165,
            "language": "ko",
            "filename_prefix": "run_audio_ko",
            "quality": "V0",
        },
    )

    assert out["node.inputs"][audio_mapper.AUDIO_TEXT]["language"] == "ko"


def test_map_audio_workflow_targets_current_checkpoint_workflow_save_node():
    out = audio_mapper.map_audio_workflow(
        {},
        {
            "genre_description": "City Pop: glossy synths and warm live drums.",
            "lyrics": "late night signs glow",
            "seed": 7,
            "bpm": 108,
            "duration": 120,
            "language": "en",
            "filename_prefix": "audio/run-7",
            "quality": "V0",
        },
    )

    assert out["node.inputs"][audio_mapper.AUDIO_SAVE]["filename_prefix"] == "audio/run-7"
    assert out["node.inputs"][audio_mapper.AUDIO_SAVE]["quality"] == "V0"
