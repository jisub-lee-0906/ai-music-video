import ai_mv.engines.flux_2_dev_ref.runner as flux2_ref_runner
from ai_mv.core.output_paths import ANCHOR_DIR, flux2_ref_frame_prefix
from ai_mv.core.stages.flux2_ref_chain import build_flux2_ref_plan


def test_flux2_ref_uses_first_start_then_chains_previous_end_across_shots(monkeypatch):
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
    assert out[1]["start"] == out[0]["end"]
    assert out[2]["start"] == out[1]["end"]
    assert out[3]["start"] == out[2]["end"]
    assert out[0]["start_source"] == "rendered_start"
    assert out[1]["start_source"] == "previous_end"
    assert out[2]["start_source"] == "previous_end"
    assert out[3]["start_source"] == "previous_end"
    assert trace == [
        ("S001", f"{ANCHOR_DIR}/master.png", "start"),
        ("S001", f"{flux2_ref_frame_prefix('S001', 'start')}.png", "end"),
        ("S002", f"{flux2_ref_frame_prefix('S001', 'end')}.png", "end"),
        ("S003", f"{flux2_ref_frame_prefix('S002', 'end')}.png", "end"),
        ("S004", f"{flux2_ref_frame_prefix('S003', 'end')}.png", "end"),
    ]


def test_flux2_ref_plan_uses_literal_scene_description_for_ref_prompts():
    config = {
        "brief": "director_brief_example",
        "audio": {"brief": "Audio brief", "hook_brief": "Hook brief"},
        "visual": {"brief": "Visual brief", "negative": "Visual negative"},
        "mv": {
            "story_world": "Night city transit world",
            "payoff_style": "Cinematic release",
            "outro_feel": "Lingering after-image",
            "avoid": "Avoid list",
        },
        "character": {"identity_core": "same heroine"},
        "director": {
            "target_style": "cinematic live-action music video",
            "world_core": "night city",
            "camera_bias": "cinematic framing",
            "lighting_bias": "city-night lighting",
            "shadow_bias": "grounded shadows",
            "motion_bias": "natural motion",
            "transition_bias": "continuity",
            "motif_families": ["curb reflection", "puddle ring"],
            "ref_frame_style": "high-end music video keyframe quality",
        },
    }
    payload = {
        "master_anchor": f"{ANCHOR_DIR}/master.png",
        "render_plan": {
            "shot_packages": [
                {
                    "shot_id": "S001",
                    "environment_family": "wet_ground_path",
                    "environment_anchor": "a narrow side street after rain with one raised curb edge, shallow roadside water catching storefront spill light, and an empty lane trailing behind her",
                    "location_description": "a narrow side street after rain with one raised curb edge, shallow roadside water catching storefront spill light, and an empty lane trailing behind her",
                    "lighting_intent": "clean city-night spill",
                    "section_name": "Verse 1",
                    "section_label": "Verse 1",
                    "visual_role": "continuity_frame",
                },
                {
                    "shot_id": "S002",
                    "environment_family": "wet_ground_path",
                    "environment_anchor": "a broad wet roadway after rain with shallow puddles, painted lane markings, reflective asphalt, and distant traffic glow stretching behind her",
                    "location_description": "a broad wet roadway after rain with shallow puddles, painted lane markings, reflective asphalt, and distant traffic glow stretching behind her",
                    "lighting_intent": "clean city-night spill",
                    "section_name": "Verse 1",
                    "section_label": "Verse 1",
                    "visual_role": "continuity_frame",
                },
            ]
        },
        "lyrics_timeline": {"sections": []},
    }

    plan = build_flux2_ref_plan(config, payload)

    assert "narrow side street after rain" in plan["items"][0]["start_prompt_text"]
    assert "broad wet roadway after rain" in plan["items"][1]["end_prompt_text"]
    assert "close urban pocket around" not in plan["items"][0]["start_prompt_text"]
