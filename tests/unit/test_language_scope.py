from ai_mv.engines.acestep_1_5_aio import planner as audio_planner
from ai_mv.engines.flux_2_dev_tti import planner as tti_planner
from ai_mv.engines.flux_2_dev_ref import planner as flux2_ref_planner
from ai_mv.engines.visual_story_bible import planner as visual_planner
from ai_mv.engines.wan_2_2_flf2v import planner as wan_planner


def test_audio_prompt_contains_language_clause_only_for_lyrics():
    audio_plan = {
        "tags": "japanese city pop, female solo vocal",
        "style_guidance": "retro japanese city-pop mood",
        "language": "ja",
        "profile_summary": "adult city-pop romance with graceful nightlife melancholy",
        "audio_direction": "glossy electric piano groove with mature vocal poise",
        "hook_direction": "neon rain hook with harbor reflections and late train imagery",
        "visual_direction": "night boulevard reflections, polished chrome, rain on glass",
        "negative_direction": "avoid sci-fi drift and generic placeholder language",
        "duration": 160,
        "bpm": 118,
        "seed": 31,
    }
    audio_prompt = audio_planner._audio_prompt(audio_plan)
    assert "Lyrics language=ja." in audio_prompt
    assert "fluent modern Japanese lyrics" in audio_prompt
    assert "Avoid forced transliterations" in audio_prompt
    assert "profile's concrete world" in audio_prompt

    sections = [_section("intro", "Intro"), _section("chorus", "Final Chorus")]
    brief = _story_bible()
    payload = {
        "audio_map": _audio_map(),
        "visual_story_bible": brief,
        "anchors": [_anchor("S001"), _anchor("S002")],
        "flux2_ref_images": [_flux2_ref_image("S001"), _flux2_ref_image("S002")],
    }
    visual_prompt = visual_planner._planner_prompt({}, {"profile_intent": _audio_map().get("profile_intent", {}), "lyrics_timeline": _timeline()})
    tti_prompt = tti_planner._planner_prompt({}, {"visual_story_bible": brief, "lyrics_timeline": _timeline()})
    flux2_ref_prompt = flux2_ref_planner._planner_prompt({}, payload, payload["anchors"], "")
    wan_prompt = wan_planner._planner_prompt({}, payload, [_wan_clip("S001"), _wan_clip("S002")], "")

    for prompt in (visual_prompt, tti_prompt, flux2_ref_prompt, wan_prompt):
        assert "Lyrics language=" not in prompt
        assert "language=ja" not in prompt.lower()
        assert "storefront pavement" not in prompt
        assert "station corridor glass" not in prompt
        assert "crosswalk under neon" not in prompt


def _audio_map() -> dict:
    return {
        "tags": "japanese city pop, female solo vocal",
        "style_guidance": "retro japanese city-pop mood",
        "genre_description": "Japanese city-pop with glossy electric piano, warm bass glide, and graceful female lead phrasing.",
        "lyrics": "[Verse 1 - Night Drive]\n雨のネオンが揺れてる\n[Chorus - Neon Rain]\nネオンの雨",
        "profile_summary": "adult city-pop romance with graceful nightlife melancholy",
        "visual_direction": "night boulevard reflections, polished chrome, rain on glass",
        "negative_direction": "avoid sci-fi drift and generic placeholder language",
        "sections": [_section("intro", "Intro"), _section("chorus", "Final Chorus")],
    }


def _section(name: str, label: str) -> dict:
    return {"name": name, "label": label, "start_sec": 0.0, "end_sec": 8.0}


def _story_bible() -> dict:
    return {
        "hero_identity_lock": "East Asian heroine, graceful late-20s, sleek bob, satin blouse, gold earrings",
        "world_rules": "Wet city streets at night with polished reflections and restrained glamour.",
        "recurring_location_families": ["reflective threshold", "open night lane"],
        "forbidden_drift": ["no sci-fi drift", "no chaotic motion"],
        "lyric_beats": [
            {
                "beat_id": "LB01_01",
                "section_name": "intro",
                "section_label": "Intro",
                "line_refs": [1],
                "literal_image": "rain on glass",
                "visible_action": "slows by the window and checks the reflection",
                "emotional_turn": "quiet anticipation",
                "continuity_anchor": "gaze shift",
                "payoff_role": "entry",
                "repeat_variant_of": "",
                "location_family": "reflective threshold",
                "palette_hint": "soft blue silver",
                "lighting_hint": "wet neon haze",
                "camera_commitment": "still pose by rain-streaked window",
            },
            {
                "beat_id": "LB02_01",
                "section_name": "chorus",
                "section_label": "Final Chorus",
                "line_refs": [1],
                "literal_image": "chrome reflections",
                "visible_action": "steps into the open street and finally faces forward",
                "emotional_turn": "radiant return",
                "continuity_anchor": "travel line",
                "payoff_role": "release",
                "repeat_variant_of": "",
                "location_family": "open night lane",
                "palette_hint": "warmer rose accent",
                "lighting_hint": "chrome flare on skin",
                "camera_commitment": "open shoulders and direct gaze",
            },
        ],
        "section_progression": [
            {"section_name": "intro", "section_label": "Intro", "dominant_emotion": "quiet anticipation", "story_function": "entry", "lyric_beat_ids": ["LB01_01"]},
            {"section_name": "chorus", "section_label": "Final Chorus", "dominant_emotion": "radiant return", "story_function": "payoff", "lyric_beat_ids": ["LB02_01"]},
        ],
        "repeat_escalation_rules": ["final chorus escalates"],
    }


def _timeline() -> dict:
    return {
        "sections": [
            {"section_name": "intro", "section_label": "Intro", "lines": [{"line_index": 1, "text": "rain on glass"}], "hook_lines": [], "lyric_beats": [{"beat_id": "LB01_01", "line_refs": [1]}]},
            {"section_name": "chorus", "section_label": "Final Chorus", "lines": [{"line_index": 1, "text": "chrome reflections"}], "hook_lines": [1], "lyric_beats": [{"beat_id": "LB02_01", "line_refs": [1]}]},
        ]
    }


def _anchor(shot_id: str) -> dict:
    return {
        "shot_id": shot_id,
        "shot_type": "PERF_WIDE",
        "section_name": "chorus",
        "section_label": "Final Chorus",
        "emotion": "warm resolve",
        "pose_delta": "slight turn toward camera",
        "scene_detail": "rain-lit boulevard reflections",
        "motion_hint": "gentle forward glide",
        "duration_sec": 4.0,
        "anchor": "anchors/master.png",
        "identity_anchor": "anchors/master.png",
        "is_chorus": True,
        "camera_language": "clean medium-wide portrait",
        "start": "frames/start.png",
        "end": "frames/end.png",
    }


def _flux2_ref_image(shot_id: str) -> dict:
    row = _anchor(shot_id)
    row["ref"] = "anchors/master.png"
    row["prompt_text"] = "An East Asian heroine turns slightly toward the lens with rain-lit boulevard reflections behind her."
    row["negative_prompt"] = "low quality, blurry"
    row["delta"] = "slight turn and brighter eye contact"
    row["style_guidance"] = "retro city-pop"
    return row


def _wan_clip(shot_id: str) -> dict:
    row = _flux2_ref_image(shot_id)
    row["fps"] = 24
    row["frames"] = 96
    return row
