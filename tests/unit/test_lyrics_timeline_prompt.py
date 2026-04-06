from ai_mv.engines.lyrics_timeline import planner


def test_lyrics_timeline_prompt_includes_visual_context_and_concrete_shot_rules():
    config = {
        "prompt": "Rainy city-night breakup song.",
        "genre": "k-pop synth pop",
        "voice": "solo female, airy and emotional",
        "language": "ko",
        "visual_concept": "Realistic cinematic music video across diner, street, and intersection.",
        "locations": ["dim retro diner", "wet city street at night", "wide wet intersection at night"],
        "props": ["worn notebook", "half-empty coffee mug"],
    }
    audio_plan = {
        "lyrics_blocks": [
            {
                "label": "Verse 1",
                "indexed_lines": [
                    {"line_index": 1, "text": "젖은 창문 너머로 네가 흐려져"},
                    {"line_index": 2, "text": "비에 젖은 거리 위로 발끝이 멀어져"},
                ],
            }
        ]
    }
    sections = [
        {
            "name": "verse_1",
            "label": "Verse 1",
            "start_sec": 0.0,
            "end_sec": 12.0,
            "lines": [
                {"line_index": 1, "text": "젖은 창문 너머로 네가 흐려져"},
                {"line_index": 2, "text": "비에 젖은 거리 위로 발끝이 멀어져"},
            ],
        }
    ]

    prompt = planner.build_lyrics_timeline_preview_prompt(config, audio_plan, sections)

    assert "literal_image must stay close to the lyric image and name concrete physical things" in prompt
    assert "Do not write meta phrases like 'the scene shows'" in prompt
    assert "Visual concept=Realistic cinematic music video across diner, street, and intersection." in prompt
    assert "Preferred locations=dim retro diner, wet city street at night, wide wet intersection at night." in prompt
    assert "Carry-friendly props=worn notebook, half-empty coffee mug." in prompt
