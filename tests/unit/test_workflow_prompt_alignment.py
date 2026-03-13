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
            {
                "section_name": "chorus",
                "emotional_arc": "lift",
                "palette_hint": "red",
                "lighting_hint": "glow",
                "staging_hint": "front portrait",
                "story_beat": "opens up in the same street",
                "location_anchor": "storefront pavement",
            }
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
    assert "Order the phrase chain so identity lands first" in prompt
    assert "A strong master_anchor reads like" in prompt
    assert "A weak master_anchor reads like" in prompt
    assert "Escalation guide=" in prompt
    assert "Final Chorus=peak return, luminous resolve, clearest environmental payoff" in prompt
    assert "Think like a finished music video" in prompt
    assert "mix front, three-quarter, profile, over-shoulder, and silhouette-friendly framings" in prompt
    assert "Verse shots should often read as travel, drift, or body-in-space coverage" in prompt
    assert "Bridge shots should introduce emotional distance" in prompt
    assert "Honor each section's story_beat and location_anchor" in prompt
    assert "space_relation must describe stable left-right or front-back geometry" in prompt
    assert "visible action readable before it tries to be pretty" in prompt
    assert "Bridge should visually interrupt the flow established before it" in prompt
    assert "Outro framing should leave a residue image" in prompt


def test_uso_prompt_mentions_atom_generation_contract():
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
    assert "Each item must include shot_id,subject_clause,action_clause,environment_clause,continuity_clause,negative_prompt" in prompt
    assert "Do not write full final prompt sentences" in prompt
    assert "subject_clause must be a short identity clause" in prompt
    assert "action_clause must describe one small visible change axis only" in prompt
    assert "Good action_clause examples" in prompt
    assert "Good environment_clause examples" in prompt
    assert "Final Chorus should feel like the visual peak" in prompt
    assert "visible payoff detail" in prompt
    assert "three-quarter turns, profile walks, over-shoulder glances" in prompt
    assert "avoid head-on beauty framing" in prompt
    assert "Honor the section story_beat and location_anchor" in prompt
    assert "Honor the shot space_relation exactly" in prompt
    assert "Do not silently mirror the scene between start and end frames" in prompt
    assert "earlier parts establish the space and body relation" in prompt
    assert "Do not give identical action_clause to multiple consecutive parts" in prompt
    assert "Bridge items should feel meaningfully interrupted or isolated" in prompt
    assert "Outro items should leave one memorable residue image" in prompt


def test_wan_prompt_mentions_motion_atom_contract():
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
    assert "Do not write the final positive_prompt prose" in prompt
    assert "motion payoff" in prompt
    assert "subject_motion must combine the visible starting state and the main body motion" in prompt
    assert "camera_relation should be one short framing phrase" in prompt
    assert "Good environment_detail examples" in prompt
    assert "Profile steering=" not in prompt
    assert "motifs=" not in prompt
    assert "Honor section story_beat and location_anchor" in prompt
    assert "Honor space_relation from the shot blueprint" in prompt
    assert "Later chorus returns can feel slightly clearer or more resolved" in prompt


def test_wan_energy_policy_lifts_final_chorus():
    final_clip = _clip("S010_C01", "chorus", "Final Chorus")
    chorus2_clip = _clip("S008_C01", "chorus", "Chorus 2")
    chorus_clip = _clip("S004_C01", "chorus", "Chorus")
    assert wan_planner._energy_policy(final_clip, "normal") == "high"
    assert wan_planner._energy_policy(chorus2_clip, "normal") == "normal"
    assert wan_planner._energy_policy(chorus_clip, "normal") == "normal"


def test_uso_anchor_summary_includes_clip_phase():
    row = uso_planner._anchor_summary_row(
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
                "location_anchor": "storefront pavement",
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
