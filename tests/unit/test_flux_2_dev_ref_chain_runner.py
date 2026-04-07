import ai_mv.engines.flux_2_dev_ref.runner as flux2_ref_runner
from ai_mv.core.output_paths import ANCHOR_DIR, flux2_ref_frame_prefix
from ai_mv.core.stages.flux2_ref_chain import build_flux2_ref_plan


def test_flux2_ref_uses_master_anchor_for_one_keyframe_per_shot(monkeypatch):
    trace: list[tuple[str, str]] = []

    def _fake_render_keyframe(_config, item):
        trace.append((str(item["shot_id"]), str(item["ref"])))
        return f"{flux2_ref_frame_prefix(item['shot_id'], sequence_index=int(item.get('timeline_index', 0) or 0))}.png"

    monkeypatch.setattr(flux2_ref_runner, "_render_keyframe", _fake_render_keyframe)

    plan = {
        "items": [
            {"shot_id": "S001", "ref": f"{ANCHOR_DIR}/master.png", "section_name": "verse", "duration_sec": 4.0, "shot_type": "CHAR_MASTER", "is_chorus": False, "clip_index": 1, "clip_count": 2, "timeline_index": 1},
            {"shot_id": "S002", "ref": f"{ANCHOR_DIR}/master.png", "section_name": "verse", "duration_sec": 4.0, "shot_type": "CHAR_MASTER", "is_chorus": False, "clip_index": 2, "clip_count": 2, "timeline_index": 2},
            {"shot_id": "S003", "ref": f"{ANCHOR_DIR}/master.png", "section_name": "chorus", "duration_sec": 4.0, "shot_type": "CHAR_MASTER", "is_chorus": True, "clip_index": 1, "clip_count": 3, "timeline_index": 3},
            {"shot_id": "S004", "ref": f"{ANCHOR_DIR}/master.png", "section_name": "chorus", "duration_sec": 4.0, "shot_type": "CHAR_MASTER", "is_chorus": True, "clip_index": 2, "clip_count": 3, "timeline_index": 4},
        ]
    }
    out = flux2_ref_runner.run_flux2_ref({}, plan)

    assert out[0]["end"] == f"{flux2_ref_frame_prefix('S001', sequence_index=1)}.png"
    assert out[1]["end"] == f"{flux2_ref_frame_prefix('S002', sequence_index=2)}.png"
    assert out[2]["end"] == f"{flux2_ref_frame_prefix('S003', sequence_index=3)}.png"
    assert out[3]["end"] == f"{flux2_ref_frame_prefix('S004', sequence_index=4)}.png"
    assert trace == [
        ("S001", f"{ANCHOR_DIR}/master.png"),
        ("S002", f"{ANCHOR_DIR}/master.png"),
        ("S003", f"{ANCHOR_DIR}/master.png"),
        ("S004", f"{ANCHOR_DIR}/master.png"),
    ]


def test_flux2_ref_plan_uses_literal_scene_description_for_ref_prompts():
    config = {
        "brief": "director_brief_example",
        "audio": {"brief": "Audio brief", "hook_brief": "Hook brief"},
        "visual": {
            "story_premise": "A performer moves through one connected night world.",
            "world_rules": "The world stays physically connected and grounded.",
            "performer_arc": "She gains direction through forward movement.",
            "forbidden_story_moves": "Avoid dream resets and extra characters.",
        },
        "character": {"identity_core": "same performer"},
    }
    payload = {
        "master_anchor": f"{ANCHOR_DIR}/master.png",
        "prompt_plan": {
            "ref_items": [
                {
                    "shot_id": "S001",
                    "ref_prompt_text": "The same performer moves along a narrow side street after rain with one raised curb edge.",
                    "section_name": "Verse 1",
                    "section_label": "Verse 1",
                },
                {
                    "shot_id": "S002",
                    "ref_prompt_text": "The same performer crosses a broad wet roadway after rain with shallow puddles.",
                    "section_name": "Verse 1",
                    "section_label": "Verse 1",
                },
            ]
        },
    }

    plan = build_flux2_ref_plan(config, payload)

    assert "narrow side street after rain" in plan["items"][0]["prompt_text"]
    assert "broad wet roadway after rain" in plan["items"][1]["prompt_text"]
    assert plan["items"][0]["prompt_text"].startswith("The same performer moves")
