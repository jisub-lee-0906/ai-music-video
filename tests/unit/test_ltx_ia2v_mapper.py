from ai_mv.engines.ltx_ia2v.mapper import map_ltx_ia2v_workflow


def test_ltx_ia2v_mapper_applies_size_fps_and_duration_to_workflow_nodes():
    mapped = map_ltx_ia2v_workflow(
        {"render": {"ltx_ia2v_size": "768x432", "ltx_fps": 12}},
        {
            "image": "source.png",
            "audio": "bed.wav",
            "positive_prompt": "move same protagonist",
            "negative_prompt": "identity drift",
            "prompt_seed": "seed text",
            "filename_prefix": "ai_mv/runs/micro/clips/shot-S012-ia2v",
            "duration_sec": 1.5,
            "audio_start_sec": 0.0,
        },
    )

    node_inputs = mapped["node.inputs"]
    assert node_inputs["340:330"] == {"value": 768}
    assert node_inputs["340:324"] == {"value": 432}
    assert node_inputs["340:323"] == {"value": 12}
    assert node_inputs["340:331"] == {"value": 1.5}
    assert node_inputs["340:332"] == {"start_index": 0.0, "duration": 1.5}
