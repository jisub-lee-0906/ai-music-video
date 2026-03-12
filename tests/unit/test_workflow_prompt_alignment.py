import ai_mv.engines.acestep_1_5_split.planner as audio_planner
import ai_mv.engines.flux_1_dev_tti.planner as tti_planner
import ai_mv.engines.flux_1_dev_uso.planner as uso_planner
import ai_mv.engines.wan_2_2_flf2v.planner as wan_planner


def test_audio_prompt_mentions_acestep_tags_field_alignment():
    prompt = audio_planner._audio_prompt(
        {
            "tags": "city pop",
            "style_guidance": "night drive romance",
            "profile_summary": "retro city-pop lane",
            "audio_direction": "mature female vocal, glossy piano",
            "hook_direction": "rain on glass, boulevard pulse",
            "visual_direction": "warm urban nightlife",
            "negative_direction": "no futuristic sci-fi tone",
            "duration": 200,
            "bpm": 108,
        }
    )
    assert "AceStep tags text field" in prompt


def test_tti_prompt_mentions_direct_text_encoder_alignment():
    brief = {
        "hero_identity": "hero",
        "world_rules": "world",
        "visual_motifs": ["rain"],
        "negative_constraints": ["drift"],
        "section_briefs": [
            {"section_name": "chorus", "emotional_arc": "lift", "palette_hint": "red", "lighting_hint": "glow", "staging_hint": "front portrait"}
        ],
    }
    audio_map = {
        "genre_description": "desc",
        "lyrics": "line",
        "tags": "city pop",
        "style_guidance": "guide",
        "profile_summary": "retro city-pop lane",
        "visual_direction": "harbor neon romance",
        "negative_direction": "no sci-fi drift",
    }
    sections = [{"name": "chorus", "label": "Final Chorus", "start_sec": 0.0, "end_sec": 8.0}]
    prompt = tti_planner._planner_prompt({}, audio_map, brief, sections)
    assert "injected directly into the workflow text encoder" in prompt
    assert "Map repeated-return escalation in clear steps" in prompt
    assert "Escalation guide=" in prompt
    assert "Final Chorus=peak return, luminous resolve, clearest environmental payoff" in prompt
    assert "Think like a finished music video" in prompt
    assert "mix front, three-quarter, profile, over-shoulder, and silhouette-friendly framings" in prompt


def test_uso_prompt_mentions_mapper_appended_clauses():
    payload = {
        "audio_map": {
            "lyrics": "line",
            "style_guidance": "guide",
            "profile_summary": "retro city-pop lane",
            "visual_direction": "harbor neon romance",
            "negative_direction": "no sci-fi drift",
        },
        "visual_brief": _brief(),
    }
    anchors = [_anchor("S010", "chorus", "Final Chorus")]
    prompt = uso_planner._planner_prompt({}, payload, anchors, "")
    assert "mapper appends frame timing and intent clauses" in prompt
    assert "Final Chorus should feel like the visual peak" in prompt
    assert "visible payoff detail" in prompt
    assert "three-quarter turns, profile walks, over-shoulder glances" in prompt


def test_wan_prompt_mentions_direct_text_encoder_alignment():
    payload = {
        "audio_map": {
            "lyrics": "line",
            "style_guidance": "guide",
            "profile_summary": "retro city-pop lane",
            "visual_direction": "harbor neon romance",
            "negative_direction": "no sci-fi drift",
        },
        "visual_brief": _brief(),
    }
    clips = [_clip("S010_C01", "chorus", "Final Chorus")]
    prompt = wan_planner._planner_prompt({}, payload, clips, "")
    assert "injected directly into the workflow text encoder" in prompt
    assert "motion payoff" in prompt
    assert "city have finally locked into the same beat" in prompt
    assert "vary frontal, three-quarter, profile, reflected, and silhouette-friendly motion views" in prompt


def test_wan_energy_policy_lifts_final_chorus():
    final_clip = _clip("S010_C01", "chorus", "Final Chorus")
    chorus2_clip = _clip("S008_C01", "chorus", "Chorus 2")
    chorus_clip = _clip("S004_C01", "chorus", "Chorus")
    assert wan_planner._energy_policy(final_clip, "normal") == "high"
    assert wan_planner._energy_policy(chorus2_clip, "normal") == "normal"
    assert wan_planner._energy_policy(chorus_clip, "normal") == "normal"


def _brief() -> dict:
    return {
        "hero_identity": "hero",
        "world_rules": "world",
        "visual_motifs": ["rain"],
        "negative_constraints": ["drift"],
        "section_briefs": [
            {"section_name": "chorus", "emotional_arc": "lift", "palette_hint": "red", "lighting_hint": "glow", "staging_hint": "front portrait"}
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
    }
