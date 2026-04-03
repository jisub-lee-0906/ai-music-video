import ai_mv.engines.flux_2_dev_ref.runner as flux2_ref_runner
from ai_mv.core.output_paths import ANCHOR_DIR, flux2_ref_frame_prefix
from ai_mv.core.stages.flux2_ref_chain import build_flux2_ref_plan


def test_flux2_ref_uses_master_anchor_for_every_start_and_end(monkeypatch):
    trace: list[tuple[str, str, str]] = []

    def _fake_render_frame(_config, item, *, frame_name, frame_idx):
        trace.append((str(item["shot_id"]), str(item["ref"]), str(frame_name)))
        return f"{flux2_ref_frame_prefix(item['shot_id'], frame_name)}.png"

    monkeypatch.setattr(flux2_ref_runner, "_render_frame", _fake_render_frame)

    plan = {
        "items": [
            {"shot_id": "S001", "ref": f"{ANCHOR_DIR}/master.png", "section_name": "verse", "duration_sec": 4.0, "shot_type": "CHAR_MASTER", "is_chorus": False, "clip_index": 1, "clip_count": 2},
            {"shot_id": "S002", "ref": f"{ANCHOR_DIR}/master.png", "section_name": "verse", "duration_sec": 4.0, "shot_type": "CHAR_MASTER", "is_chorus": False, "clip_index": 2, "clip_count": 2},
            {"shot_id": "S003", "ref": f"{ANCHOR_DIR}/master.png", "section_name": "chorus", "duration_sec": 4.0, "shot_type": "CHAR_MASTER", "is_chorus": True, "clip_index": 1, "clip_count": 3},
            {"shot_id": "S004", "ref": f"{ANCHOR_DIR}/master.png", "section_name": "chorus", "duration_sec": 4.0, "shot_type": "CHAR_MASTER", "is_chorus": True, "clip_index": 2, "clip_count": 3},
        ]
    }
    out = flux2_ref_runner.run_flux2_ref({}, plan)

    assert out[0]["start"] == f"{flux2_ref_frame_prefix('S001', 'start')}.png"
    assert out[1]["start"] == f"{flux2_ref_frame_prefix('S002', 'start')}.png"
    assert out[2]["start"] == f"{flux2_ref_frame_prefix('S003', 'start')}.png"
    assert out[3]["start"] == f"{flux2_ref_frame_prefix('S004', 'start')}.png"
    assert out[0]["start_source"] == "master_anchor"
    assert out[1]["start_source"] == "master_anchor"
    assert out[2]["start_source"] == "master_anchor"
    assert out[3]["start_source"] == "master_anchor"
    assert trace == [
        ("S001", f"{ANCHOR_DIR}/master.png", "start"),
        ("S001", f"{ANCHOR_DIR}/master.png", "end"),
        ("S002", f"{ANCHOR_DIR}/master.png", "start"),
        ("S002", f"{ANCHOR_DIR}/master.png", "end"),
        ("S003", f"{ANCHOR_DIR}/master.png", "start"),
        ("S003", f"{ANCHOR_DIR}/master.png", "end"),
        ("S004", f"{ANCHOR_DIR}/master.png", "start"),
        ("S004", f"{ANCHOR_DIR}/master.png", "end"),
    ]


def test_flux2_ref_plan_uses_literal_scene_description_for_ref_prompts():
    config = {
        "brief": "director_brief_example",
        "audio": {"brief": "Audio brief", "hook_brief": "Hook brief"},
        "visual": {
            "story_premise": "A heroine moves through one connected night world.",
            "world_rules": "The world stays physically connected and grounded.",
            "heroine_arc": "She gains direction through forward movement.",
            "forbidden_story_moves": "Avoid dream resets and extra characters.",
        },
        "character": {"identity_core": "same heroine"},
    }
    payload = {
        "master_anchor": f"{ANCHOR_DIR}/master.png",
        "prompt_plan": {
            "ref_items": [
                {
                    "shot_id": "S001",
                    "primary_surface": "narrow side street after rain with one raised curb edge",
                    "content_trace": "shallow roadside water catching storefront spill light",
                    "ref_start_prompt_text": "The same heroine moves along a narrow side street after rain with one raised curb edge.",
                    "ref_end_prompt_text": "The same heroine carries her next step along a narrow side street after rain with one raised curb edge.",
                    "section_name": "Verse 1",
                    "section_label": "Verse 1",
                },
                {
                    "shot_id": "S002",
                    "primary_surface": "broad wet roadway after rain with shallow puddles",
                    "content_trace": "painted lane markings and reflective asphalt",
                    "ref_start_prompt_text": "The same heroine enters a broad wet roadway after rain with shallow puddles.",
                    "ref_end_prompt_text": "The same heroine crosses a broad wet roadway after rain with shallow puddles.",
                    "section_name": "Verse 1",
                    "section_label": "Verse 1",
                },
            ]
        },
    }

    plan = build_flux2_ref_plan(config, payload)

    assert "narrow side street after rain" in plan["items"][0]["start_prompt_text"]
    assert "broad wet roadway after rain" in plan["items"][1]["end_prompt_text"]
    assert plan["items"][0]["scene_detail"] == "narrow side street after rain with one raised curb edge"
