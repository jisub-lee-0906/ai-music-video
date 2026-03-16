import ai_mv.engines.acestep_1_5_split.planner as audio_planner
import ai_mv.engines.flux_1_dev_tti.planner as tti_planner
import ai_mv.engines.flux2_reference.planner as flux2_ref_planner
import ai_mv.engines.wan_2_2_flf2v.planner as wan_planner


def test_audio_prompt_mentions_acestep_tags_field_alignment():
    prompt = audio_planner._audio_prompt(
        {
            "tags": "city pop",
            "profile_summary": "retro city-pop lane",
            "audio_direction": "mature female vocal, glossy piano",
            "hook_direction": "rain on glass, boulevard pulse",
            "visual_direction": "warm urban nightlife",
            "negative_direction": "no futuristic sci-fi tone",
            "profile_intent": {
                "audio_intent": {"brief": "mature female vocal, glossy piano", "hook_brief": "rain on glass, boulevard pulse"},
                "world_intent": {"visual_brief": "warm urban nightlife", "story_world": "retro city-pop lane"},
                "negative_intent": {"visual_negative": "no futuristic sci-fi tone", "mv_avoid": "no clutter"},
            },
            "duration": 200,
            "bpm": 108,
        }
    )
    assert "AceStep tags text field" in prompt
    assert "Audio intent=" in prompt


def test_tti_prompt_mentions_direct_text_encoder_alignment():
    brief = {
        "hero_identity": "hero",
        "world_rules": "world",
        "recurring_location_families": ["reflective threshold"],
        "allowed_visual_variation": ["framing changes"],
        "visual_motifs": ["rain"],
        "negative_constraints": ["drift"],
        "section_briefs": [
            {
                "section_name": "chorus",
                "emotional_arc": "lift",
                "palette_hint": "red",
                "lighting_hint": "glow",
                "staging_hint": "front portrait",
                "story_beat": "opens up in the same street",
                "location_anchor": "reflective threshold",
                "escalation_level": "payoff",
                "motion_axis": "gaze shift",
            }
        ],
    }
    audio_map = {
        "profile_intent": {
            "audio_intent": {"brief": "desc", "hook_brief": "hook"},
            "world_intent": {"visual_brief": "harbor neon romance", "story_world": "retro city-pop lane"},
        },
        "section_semantics": [{"section_name": "chorus", "section_label": "Final Chorus", "movement_bias": "clear hero payoff", "release_level": "peak", "hero_frame_priority": "peak"}],
    }
    sections = [{"name": "chorus", "label": "Final Chorus", "start_sec": 0.0, "end_sec": 8.0}]
    prompt = tti_planner._planner_prompt({}, audio_map, brief, sections)
    assert "deterministic visual contract" in prompt
    assert "master_anchor prompt_text must be a compact diffusion prompt string composed of stable identity and world facts only" in prompt
    assert "Escalation guide=" in prompt
    assert "Final Chorus=peak return, luminous resolve, clearest environmental payoff" in prompt
    assert "Honor each section's story_beat, location_anchor, escalation_level, and motion_axis" in prompt
    assert "Shot grammar=" in prompt
    assert "Location grammar=" in prompt
    assert "Section semantics=Final Chorus|clear hero payoff|peak|peak" in prompt
    assert "Audio intent=desc" in prompt
    assert "World intent=harbor neon romance" in prompt


def test_flux2_ref_prompt_mentions_atom_generation_contract():
    payload = {
        "visual_brief": _brief(),
    }
    anchors = [_anchor("S010", "chorus", "Final Chorus")]
    prompt = flux2_ref_planner._planner_prompt({}, payload, anchors, "")
    assert "deterministic flux2 reference composer" in prompt
    assert "hero=hero" in prompt
    assert "world=world" in prompt
    assert "S010(" in prompt


def test_wan_prompt_mentions_motion_atom_contract():
    payload = {
        "visual_brief": _brief(),
    }
    clips = [_clip("S010_C01", "chorus", "Final Chorus")]
    prompt = wan_planner._planner_prompt({}, payload, clips, "")
    assert "deterministic wan composer" in prompt
    assert "clip_ids=S010_C01" in prompt
    assert "hero=hero" in prompt
    assert "clips=S010_C01(" in prompt


def test_wan_energy_policy_lifts_final_chorus():
    final_clip = _clip("S010_C01", "chorus", "Final Chorus")
    chorus2_clip = _clip("S008_C01", "chorus", "Chorus 2")
    chorus_clip = _clip("S004_C01", "chorus", "Chorus")
    assert wan_planner._energy_policy(final_clip, "normal") == "high"
    assert wan_planner._energy_policy(chorus2_clip, "normal") == "normal"
    assert wan_planner._energy_policy(chorus_clip, "normal") == "normal"


def test_flux2_ref_anchor_summary_includes_clip_phase():
    row = flux2_ref_planner._anchor_summary_row(
        {
            "shot_id": "S010_C01",
            "section_name": "chorus",
            "section_label": "Final Chorus",
            "shot_type": "PERF_WIDE",
            "emotion": "lift",
            "pose_delta": "small turn",
            "scene_detail": "rain glow",
            "space_relation": "glass stays camera-right",
            "clip_index": 1,
            "clip_count": 3,
        }
    )
    assert "establish" in row


def _brief() -> dict:
    return {
        "hero_identity": "hero",
        "world_rules": "world",
        "recurring_location_families": ["reflective threshold"],
        "allowed_visual_variation": ["framing changes"],
        "visual_motifs": ["rain"],
        "negative_constraints": ["drift"],
        "section_briefs": [
            {
                "section_name": "chorus",
                "emotional_arc": "lift",
                "palette_hint": "red",
                "lighting_hint": "glow",
                "staging_hint": "front portrait",
                "story_beat": "opens up in the same street",
                "location_anchor": "reflective threshold",
                "escalation_level": "payoff",
                "motion_axis": "gaze shift",
            }
        ],
    }


def _anchor(shot_id: str, section_name: str, section_label: str) -> dict:
    return {
        "shot_id": shot_id,
        "section_name": section_name,
        "section_label": section_label,
        "shot_type": "PERF_WIDE",
        "emotion": "lift",
        "pose_delta": "small turn",
        "scene_detail": "rain glow",
        "motion_hint": "slow move",
        "space_relation": "glass stays camera-right",
    }


def _clip(shot_id: str, section_name: str, section_label: str) -> dict:
    return {
        "shot_id": shot_id,
        "section_name": section_name,
        "section_label": section_label,
        "camera_language": "clean frame",
        "emotion": "lift",
        "scene_detail": "rain glow",
        "motion_hint": "slow move",
        "space_relation": "glass stays camera-right",
    }
