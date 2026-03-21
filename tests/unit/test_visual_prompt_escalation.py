import ai_mv.engines.flux_2_dev_tti.planner as tti_planner
import ai_mv.engines.flux_2_dev_ref.planner as flux2_ref_planner
import ai_mv.engines.wan_2_2_flf2v.planner as wan_planner


def test_tti_prompt_uses_section_labels_for_escalation():
    payload = {"visual_story_bible": _story_bible(), "lyrics_timeline": _timeline()}
    prompt = tti_planner._planner_prompt({}, payload)
    assert "Write a shot timeline for downstream Flux and video workflows" in prompt
    assert "Story bible=" in prompt
    assert "Lyric timeline=" in prompt


def test_flux2_ref_prompt_mentions_return_intensity():
    payload = {
        "visual_story_bible": _story_bible(),
    }
    anchors = [_anchor("S010", "chorus", "Final Chorus")]
    prompt = flux2_ref_planner._planner_prompt({}, payload, anchors, "")
    assert "Final Chorus should feel like the visual peak" not in prompt
    assert "Profile steering=" not in prompt
    assert "Write Flux2 ref prompts for continuity shots" in prompt
    assert "Lyrics context=" not in prompt
    assert "Avoid=" not in prompt


def test_wan_prompt_mentions_final_chorus_payoff():
    payload = {
        "visual_story_bible": _story_bible(),
    }
    clips = [_clip("S010_C01", "chorus", "Final Chorus")]
    prompt = wan_planner._planner_prompt({}, payload, clips, "")
    assert "Final Chorus should feel like the motion payoff" not in prompt
    assert "Write WAN FLF2V prompts for start and end frames that are already fixed" in prompt
    assert "Profile steering=" not in prompt
    assert "motifs=" not in prompt
    assert "Shot manifest=S010_C01" in prompt


def _story_bible() -> dict:
    return {
        "hero_identity_lock": "hero",
        "world_rules": "world",
        "recurring_location_families": ["open night lane"],
        "forbidden_drift": ["drift"],
        "lyric_beats": [
            {"beat_id": "LB01_01", "section_name": "chorus", "section_label": "Final Chorus", "line_refs": [1], "literal_image": "rain", "visible_action": "faces forward", "emotional_turn": "lift", "continuity_anchor": "gaze shift", "payoff_role": "release", "repeat_variant_of": "", "location_family": "open night lane", "palette_hint": "red", "lighting_hint": "glow", "camera_commitment": "front portrait"}
        ],
        "section_progression": [{"section_name": "chorus", "section_label": "Final Chorus", "dominant_emotion": "lift", "story_function": "payoff", "lyric_beat_ids": ["LB01_01"]}],
        "repeat_escalation_rules": ["final chorus escalates"],
    }


def _timeline() -> dict:
    return {"sections": [{"section_name": "chorus", "section_label": "Final Chorus", "lines": [{"line_index": 1, "text": "rain"}], "hook_lines": [1], "lyric_beats": [{"beat_id": "LB01_01", "line_refs": [1]}]}]}


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
