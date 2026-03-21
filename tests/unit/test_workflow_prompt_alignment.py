import ai_mv.engines.acestep_1_5_aio.planner as audio_planner
import ai_mv.engines.flux_2_dev_tti.planner as tti_planner
import ai_mv.engines.flux_2_dev_ref.planner as flux2_ref_planner
import ai_mv.engines.lyrics_timeline.planner as lyrics_timeline_planner
import ai_mv.engines.wan_2_2_flf2v.planner as wan_planner
from ai_mv.core.contracts.prompt_schema import lyrics_timeline_schema
from ai_mv.core.workflow_prompt_contracts import compose_flux2_tti_prompt


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
        "world_intent": {"visual_intent": "warm urban nightlife", "story_world": "retro city-pop lane"},
                "negative_intent": {"visual_negative": "no futuristic sci-fi tone", "mv_avoid": "no clutter"},
            },
            "duration": 200,
            "bpm": 108,
        }
    )
    assert "AceStep tags text field" in prompt
    assert "Audio intent=" in prompt


def test_tti_prompt_mentions_direct_text_encoder_alignment():
    payload = {
        "visual_story_bible": {
            **_story_bible(),
            "resolved_profile_policy": {
                "visual_mode": "balanced",
                "continuity_mode": "same_heroine",
                "face_policy": "payoff_only",
                "shot_bias": "environment",
                "ref_policy": "identity_sensitive_only",
                "shot_distribution": {
                    "CHAR_MASTER": 0.15,
                    "EMOTION_CLOSE": 0.10,
                    "PERF_WIDE": 0.25,
                    "ENV_TRANSITION": 0.30,
                    "DETAIL_INSERT": 0.20,
                },
                "direct_face_sections": ["Final Chorus"],
            },
        },
        "lyrics_timeline": _timeline(),
    }
    prompt = tti_planner._planner_prompt({}, payload)
    assert "Write a shot timeline for downstream Flux and video workflows" in prompt
    assert "master_anchor prompt_text should contain only stable identity and world facts" in prompt
    assert "Every shot must include lyric_beat_id,shot_type,camera_language,pose_delta,emotion,scene_detail,motion_hint,workflow_motion_clause,space_relation,edit_role,continuity_lock,scene_change_level,anchor_strategy,continuity_basis,clip_count" in prompt
    assert "workflow_motion_clause should be a full WAN action clause beginning with a finite verb phrase" in prompt
    assert "Profile policy=" in prompt
    assert "face_policy=payoff_only" in prompt
    assert "Make nearby beats meaningfully different in framing, action, or visual state" in prompt
    assert "Story bible=" in prompt
    assert "Lyric timeline=" in prompt


def test_lyrics_timeline_prompt_mentions_full_line_coverage():
    prompt = lyrics_timeline_planner._planner_prompt(
        {"lyrics_blocks": [{"label": "Verse 1", "indexed_lines": [{"line_index": i, "text": f"line {i}"} for i in range(1, 7)]}]},
        [{
            "name": "verse_1",
            "label": "Verse 1",
            "start_sec": 0.0,
            "end_sec": 20.0,
            "lines": [{"line_index": i, "text": f"line {i}"} for i in range(1, 7)],
        }],
    )
    assert "Cover every lyric line at least once" in prompt
    assert "Treat line_refs as a complete coverage map" in prompt
    assert "Break each section into 1-4 visual beats" in prompt


def test_lyrics_timeline_schema_allows_five_beats_for_dense_sections():
    schema = lyrics_timeline_schema()
    assert schema["properties"]["sections"]["items"]["properties"]["lyric_beats"]["maxItems"] == 5


def test_flux2_ref_prompt_mentions_atom_generation_contract():
    payload = {
        "visual_story_bible": _story_bible(),
    }
    anchors = [_anchor("S010", "chorus", "Final Chorus")]
    prompt = flux2_ref_planner._planner_prompt({}, payload, anchors, "")
    assert "deterministic flux2 reference composer" in prompt
    assert "anchors=S010(" in prompt
    assert "|heroine|" in prompt
    assert "S010(" in prompt


def test_wan_prompt_mentions_motion_atom_contract():
    payload = {
        "visual_story_bible": _story_bible(),
    }
    clips = [_clip("S010_C01", "chorus", "Final Chorus")]
    prompt = wan_planner._planner_prompt({}, payload, clips, "")
    assert "deterministic wan composer" in prompt
    assert "clip_ids=S010_C01" in prompt
    assert "clips=S010_C01(" in prompt
    assert "S010_C01(heroine|" in prompt
    assert "clips=S010_C01(" in prompt


def test_flux2_tti_prompt_uses_style_subject_background_camera_order():
    text = compose_flux2_tti_prompt(
        "Base style sentence",
        "A heroine swings a guitar down",
        "The background is a planar alley with neon signs",
        "The camera uses an extreme low-angle dynamic shot",
    )
    assert text == (
        "Base style sentence. "
        "A heroine swings a guitar down. "
        "The background is a planar alley with neon signs. "
        "The camera uses an extreme low-angle dynamic shot."
    )


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


def _story_bible() -> dict:
    return {
        "hero_identity_lock": "hero",
        "world_rules": "world",
        "recurring_location_families": ["reflective threshold"],
        "forbidden_drift": ["drift"],
        "lyric_beats": [
            {
                "beat_id": "LB01_01",
                "section_name": "chorus",
                "section_label": "Final Chorus",
                "line_refs": [1],
                "literal_image": "rain street",
                "visible_action": "opens up in the same street",
                "emotional_turn": "lift",
                "continuity_anchor": "gaze shift",
                "payoff_role": "release",
                "repeat_variant_of": "",
                "location_family": "reflective threshold",
                "palette_hint": "red",
                "lighting_hint": "glow",
                "camera_commitment": "front portrait",
            }
        ],
        "section_progression": [
            {"section_name": "chorus", "section_label": "Final Chorus", "dominant_emotion": "lift", "story_function": "payoff", "lyric_beat_ids": ["LB01_01"]}
        ],
        "repeat_escalation_rules": ["final chorus must escalate visually"],
    }


def _timeline() -> dict:
    return {
        "sections": [
            {
                "section_name": "chorus",
                "section_label": "Final Chorus",
                "lines": [{"line_index": 1, "text": "rain street"}],
                "hook_lines": [1],
                "lyric_beats": [{"beat_id": "LB01_01", "line_refs": [1]}],
            }
        ]
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
        "workflow_motion_clause": "turning into center light and holding the line",
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
        "workflow_motion_clause": "moving through the lane and holding the look",
        "space_relation": "glass stays camera-right",
    }
