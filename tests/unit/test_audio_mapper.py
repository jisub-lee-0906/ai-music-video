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
