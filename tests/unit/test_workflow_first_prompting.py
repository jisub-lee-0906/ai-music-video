import shutil
from pathlib import Path

from ai_mv.core.artifacts.prompt_compare_report import write_prompt_compare_report
from ai_mv.engines.acestep_1_5_aio.mapper import _audio_conditioning_text
from ai_mv.engines.visual_story_bible.brief_views import compact_world_atoms
import ai_mv.engines.flux_2_dev_ref.planner as flux2_ref_planner
import ai_mv.engines.flux_2_dev_tti.planner as tti_planner
import ai_mv.engines.wan_2_2_flf2v.planner as wan_planner
from ai_mv.utils.json_utils import write_json


def test_audio_conditioning_text_dedupes_genre_prefix():
    text = _audio_conditioning_text(
        {
            "tags": "k-pop, glossy",
            "genre_description": "K-Pop: punchy drums, sleek synth bass, bright chorus lift.",
        }
    )
    assert text == "K-Pop: punchy drums, sleek synth bass, bright chorus lift"


def test_tti_prompt_removes_hardcoded_beauty_baseline():
    prompt = tti_planner._planner_prompt({}, {"visual_story_bible": _plain_story_bible(), "lyrics_timeline": _timeline()})
    assert "stunningly beautiful" not in prompt
    assert "idol-like" not in prompt
    assert "high-end fashion model aesthetic" not in prompt


def test_flux2_ref_prompt_does_not_inject_house_style_without_profile_support():
    item = flux2_ref_planner._build_item(_anchor("S001"), _plain_story_bible(), 1)
    assert "stunningly beautiful" not in item["prompt_text"]
    assert "idol-like" not in item["prompt_text"]
    assert "high-end fashion model aesthetic" not in item["prompt_text"]


def test_wan_prompt_does_not_inject_house_style_without_profile_support():
    clip = wan_planner._apply_prompt(_clip("S001_C01"), _plain_story_bible())
    assert "stunningly beautiful" not in clip["positive_prompt"]
    assert "idol-like" not in clip["positive_prompt"]
    assert "high-end fashion model aesthetic" not in clip["positive_prompt"]


def test_compact_world_atoms_trims_policy_like_identity_tail():
    world = compact_world_atoms(
        {
            "hero_identity_lock": (
                "One consistent young adult East Asian heroine only, glossy K-pop idol presence, "
                "premium styling, mirror-skin glam, controlled direct gaze, no cast swaps, no age drift, "
                "no hairstyle-color drift beyond subtle styling variation, no wardrobe downgrade, "
                "always the same high-shine night-world protagonist"
            ),
            "world_rules": "same world",
        }
    )
    assert "glossy K-pop idol presence" in world["hero_identity"]
    assert "controlled direct gaze" in world["hero_identity"]
    assert "no cast swaps" not in world["hero_identity"]
    assert "no wardrobe downgrade" not in world["hero_identity"]


def test_prompt_compare_report_marks_alignment_and_retained_profile_backing():
    before = Path("artifacts/preflight/test-before-compare")
    after = Path("artifacts/preflight/test-after-compare")
    shutil.rmtree(before, ignore_errors=True)
    shutil.rmtree(after, ignore_errors=True)
    before.mkdir(parents=True, exist_ok=True)
    after.mkdir(parents=True, exist_ok=True)
    write_json(
        before / "prompt_preview.json",
        {
            "run_id": "test-before-compare",
            "prompts": {
                "shot_timeline": {"prompt": "default aesthetic baseline is stunningly beautiful photorealistic live-action imagery."},
                "flux2_ref_chain": {"batches": [{"prompt": "default aesthetic baseline is stunningly beautiful heroine."}]},
                "wan_interpolation": {"batches": [{"prompt": "default aesthetic baseline is stunningly beautiful heroine."}]},
            },
        },
    )
    write_json(
        before / "workflow_inputs_preview.json",
        {
            "run_id": "test-before-compare",
            "workflow_inputs": {
                "audio": {"text_inputs": {"tags": "K-Pop: bright hook."}},
                "visual_story_bible": {"story_bible_preview": {"hero_identity_lock": "hero"}},
                "shot_timeline": {"master_anchor": {"text": "stunningly beautiful heroine"}},
                "flux2_ref_chain": {"items": [{"start_text": "stunningly beautiful heroine", "end_text": "stunningly beautiful heroine"}]},
                "wan_interpolation": {"clips": [{"positive_prompt": "stunningly beautiful heroine", "negative_prompt": "logo"}]},
            },
        },
    )
    write_json(
        after / "prompt_preview.json",
        {
            "run_id": "test-after-compare",
            "prompts": {
                "shot_timeline": {"prompt": "workflow-ready shot atoms."},
                "flux2_ref_chain": {"batches": [{"prompt": "compose compact prompts for the workflow positive text field."}]},
                "wan_interpolation": {"batches": [{"prompt": "compose short motion-first prompts for the workflow positive and negative text fields."}]},
            },
        },
    )
    write_json(
        after / "workflow_inputs_preview.json",
        {
            "run_id": "test-after-compare",
            "workflow_inputs": {
                "audio": {"text_inputs": {"tags": "K-Pop: bright hook."}},
                "visual_story_bible": {"story_bible_preview": {"hero_identity_lock": "hero"}},
                "shot_timeline": {"master_anchor": {"text": "premium glossy k-pop heroine"}},
                "flux2_ref_chain": {"items": [{"start_text": "premium glossy k-pop heroine", "end_text": "premium glossy k-pop heroine"}]},
                "wan_interpolation": {"clips": [{"positive_prompt": "Premium glossy k-pop heroine. Bright threshold world.", "negative_prompt": "logo"}]},
            },
        },
    )
    report = write_prompt_compare_report(
        "test-before-compare",
        "test-after-compare",
        "kpop_highgloss",
        {
            "audio": {"brief": ""},
            "visual": {"brief": "premium glossy k-pop heroine", "negative": ""},
            "mv": {"story_world": "", "action_vocabulary": "", "payoff_style": "", "avoid": ""},
            "profile": "kpop_highgloss",
        },
    )
    assert report["overall_alignment"] == "aligned"
    shot_stage = next(stage for stage in report["stages"] if stage["stage"] == "shot_timeline")
    assert "stunningly beautiful" in shot_stage["removed_house_style_leaks"]
    assert shot_stage["alignment"] == "aligned"


def _plain_story_bible() -> dict:
    return {
        "hero_identity_lock": "one performer with a clean direct gaze",
        "world_rules": "single reflective night set, clean lines, no text",
        "recurring_location_families": ["reflective threshold"],
        "forbidden_drift": ["text"],
        "lyric_beats": [
            {
                "beat_id": "LB01",
                "section_name": "chorus",
                "section_label": "Chorus",
                "line_refs": [1],
                "literal_image": "clean reflected light",
                "visible_action": "steps into the lit center and holds",
                "emotional_turn": "control locks in",
                "continuity_anchor": "center lane",
                "payoff_role": "release",
                "repeat_variant_of": "",
                "location_family": "reflective threshold",
                "palette_hint": "silver white",
                "lighting_hint": "hard practical glow",
                "camera_commitment": "front-facing medium",
            }
        ],
        "section_progression": [{"section_name": "chorus", "section_label": "Chorus", "dominant_emotion": "lift", "story_function": "payoff", "lyric_beat_ids": ["LB01"]}],
        "repeat_escalation_rules": ["returns must vary"],
    }


def _timeline() -> dict:
    return {"sections": [{"section_name": "chorus", "section_label": "Chorus", "lines": [{"line_index": 1, "text": "line"}], "hook_lines": [1], "lyric_beats": [{"beat_id": "LB01", "line_refs": [1]}]}]}


def _anchor(shot_id: str) -> dict:
    return {
        "shot_id": shot_id,
        "anchor": "anchor.png",
        "identity_anchor": "anchor.png",
        "duration_sec": 4.0,
        "clip_index": 1,
        "clip_count": 1,
        "shot_type": "PERF_WIDE",
        "section_name": "chorus",
        "section_label": "Chorus",
        "pose_delta": "turns into center light",
        "scene_detail": "reflective threshold",
        "space_relation": "center lane",
        "kinetic_transition": "snap_zoom_in",
        "kinetic_intensity": "high",
        "lighting_fx": "hard practical glow",
        "lyric_beat_id": "LB01",
    }


def _clip(shot_id: str) -> dict:
    return {
        "shot_id": shot_id,
        "section_name": "chorus",
        "section_label": "Chorus",
        "shot_type": "PERF_WIDE",
        "motion_hint": "steps into the lit center and holds",
        "camera_language": "snap zoom into center lock",
        "scene_detail": "reflective threshold",
        "space_relation": "center lane",
        "kinetic_transition": "snap_zoom_in",
        "kinetic_intensity": "high",
        "lighting_fx": "hard practical glow",
        "lyric_beat_id": "LB01",
        "duration_sec": 4.0,
        "clip_index": 1,
        "clip_count": 1,
        "use_ref": False,
    }
