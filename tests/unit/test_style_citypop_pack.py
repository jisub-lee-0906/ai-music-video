from ai_mv.core.stages.plan_mv import build_plan_preview_payload
from ai_mv.styles.citypop.bible import get_citypop_bible
from ai_mv.styles.citypop.prompting import build_citypop_prompt_draft, build_citypop_prompt_seed
from ai_mv.styles.citypop.rules import (
    BRIDGE_CONNECTIVE_FAMILIES,
    INTRO_WORLD_FIRST_FAMILIES,
    OUTRO_RELEASE_FAMILIES,
    apply_citypop_section_variants,
    citypop_section_shot_specs,
)


def test_citypop_style_pack_exposes_bible():
    bible = get_citypop_bible()

    assert bible["style"] == "japanese_citypop_80s_90s"
    assert "sunset amber" in bible["palette"]
    assert "city lights" in bible["motifs"]
    assert "k-pop look" in bible["negative_rules"]


def test_plan_preview_uses_citypop_style_pack_bible():
    out = build_plan_preview_payload(
        {},
        {
            "concept_text": "Japanese 80s city pop night drive",
            "audio_map": {
                "duration_sec": 16.0,
                "sections": [{"name": "chorus", "start_sec": 0.0, "end_sec": 16.0}],
            },
        },
    )

    assert out["style_bible"] == get_citypop_bible()


def test_citypop_prompting_builds_seed_from_style_pack_helpers():
    seed = build_citypop_prompt_seed(
        "Japanese 80s city pop night drive",
        get_citypop_bible(),
        {
            "section_name": "Chorus",
            "shot_role": "chorus_arrive",
            "visual_mode": "chorus_performance",
        },
    )

    assert "Japanese 80s city pop music video" in seed
    assert "same protagonist" in seed
    assert "same summer night-drive world" in seed
    assert "city pop" not in seed.lower() or "japanese 80s city pop music video" in seed.lower()
    assert "scene event:" not in seed
    assert "performance-led singer in a three-quarter medium frame with neon reflections" in seed
    assert "close-up of a singer facing the camera" not in seed


def test_citypop_prompting_supports_expressive_continuity_mode():
    seed = build_citypop_prompt_seed(
        "late-night city pop walk under wet neon lights",
        get_citypop_bible(),
        {
            "section_name": "Bridge",
            "shot_role": "bridge_shift",
            "visual_mode": "bridge_overlook",
            "continuity_mode": "expressive",
        },
    )

    assert "same protagonist" not in seed
    assert "same summer night-drive world" not in seed
    assert "echo the established night mood while allowing a deliberate visual reset" in seed


def test_citypop_prompting_builds_draft_from_style_pack_helpers():
    draft = build_citypop_prompt_draft({"visual_mode": "profile_mood"})

    assert "motion-safe keyframe" in draft
    assert "no layered collage" in draft
    assert "tight portrait close-up" in draft
    assert "film grain" in draft


def test_citypop_prompt_draft_keeps_chorus_performance_out_of_front_facing_closeup_default():
    draft = build_citypop_prompt_draft({"visual_mode": "chorus_performance", "framing_intent": "performance_medium"})

    assert "front-facing close-up" not in draft
    assert "performance-led medium shot" in draft


def test_citypop_rules_expose_section_shot_specs():
    specs = citypop_section_shot_specs("chorus", 8.0)

    assert [item["shot_role"] for item in specs] == ["chorus_arrive", "chorus_hold"]
    assert [item["visual_mode"] for item in specs] == ["chorus_performance", "neon_release"]


def test_citypop_rules_use_true_wide_families_for_intro_and_outro():
    intro_specs = citypop_section_shot_specs("intro", 3.0)
    outro_specs = citypop_section_shot_specs("outro", 3.0)

    assert intro_specs[0]["visual_mode"] in INTRO_WORLD_FIRST_FAMILIES
    assert outro_specs[0]["visual_mode"] in OUTRO_RELEASE_FAMILIES


def test_citypop_rules_use_less_portrait_biased_connective_families_for_prechorus_and_bridge():
    prechorus_specs = citypop_section_shot_specs("pre_chorus", 4.0)
    bridge_specs = citypop_section_shot_specs("bridge", 4.0)

    assert prechorus_specs[0]["visual_mode"] == "partial_figure_transition"
    assert bridge_specs[0]["visual_mode"] in BRIDGE_CONNECTIVE_FAMILIES


def test_citypop_rules_apply_progressive_section_variants():
    out = apply_citypop_section_variants(
        "verse",
        [
            {"shot_role": "verse_setup", "visual_mode": "night_drive"},
            {"shot_role": "verse_setup", "visual_mode": "night_drive"},
            {"shot_role": "verse_setup", "visual_mode": "night_drive"},
            {"shot_role": "verse_setup", "visual_mode": "night_drive"},
        ],
    )

    assert [item["shot_role"] for item in out] == ["verse_setup", "verse_detail", "verse_flow", "verse_glow"]
    assert [item["visual_mode"] for item in out] == ["night_drive", "rain_window_detail", "night_drive", "city_glance"]


def test_citypop_prompt_seed_keeps_release_wide_environment_first_without_dropping_subject_anchor():
    seed = build_citypop_prompt_seed(
        "late-night city pop walk under wet neon lights",
        get_citypop_bible(),
        {
            "section_name": "Outro",
            "shot_role": "outro_release",
            "visual_mode": "skyline_release",
            "framing_intent": "release_wide",
        },
    )

    assert "rainy neon skyline boulevard at dusk" in seed
    assert "one anchored figure under the skyline glow" in seed
    assert seed.index("rainy neon skyline boulevard at dusk") < seed.index("one anchored figure under the skyline glow")


def test_citypop_prompt_seed_uses_world_first_intro_family_without_empty_canvas_language():
    seed = build_citypop_prompt_seed(
        "late-night city pop walk under wet neon lights",
        get_citypop_bible(),
        {
            "section_name": "Intro",
            "shot_role": "intro_mood",
            "visual_mode": "empty_boulevard_anchor",
            "framing_intent": "establishing_wide",
        },
    )

    assert "near-empty rain-slick boulevard with dominant roadway depth and distant traffic glow" in seed
    assert "one distant anchored figure under the boulevard lights" in seed
    assert seed.index("near-empty rain-slick boulevard with dominant roadway depth and distant traffic glow") < seed.index("one distant anchored figure under the boulevard lights")


def test_citypop_prompt_draft_keeps_true_wide_release_but_reanchors_the_subject():
    draft = build_citypop_prompt_draft({"visual_mode": "skyline_release", "framing_intent": "release_wide"})

    assert "off-center composition" in draft
    assert "anchored subject silhouette" in draft
    assert "controlled negative space" in draft
    assert "readable subject scale" in draft
    assert "no direct face toward camera" in draft
    assert "skyline-led negative space" not in draft
    assert "small figure emphasis" not in draft


def test_citypop_prompt_draft_strengthens_world_first_rules_for_intro_family_without_allowing_blank_subject_loss():
    draft = build_citypop_prompt_draft({"visual_mode": "empty_boulevard_anchor", "framing_intent": "establishing_wide"})

    assert "world-first establishing frame with boulevard depth and one distant anchored figure" in draft
    assert "one distant anchored figure" in draft
    assert "avoid empty dead zones" in draft
    assert "no foreground figure" not in draft


def test_citypop_prompt_draft_adds_partial_figure_rules_for_connective_family_without_environment_dominance():
    draft = build_citypop_prompt_draft({"visual_mode": "partial_figure_transition", "framing_intent": "connective_medium"})

    assert "partial-figure transition frame" in draft
    assert "anchored partial figure" in draft
    assert "no direct face toward camera" in draft
    assert "environment dominates the frame" not in draft


def test_citypop_prompt_draft_keeps_bridge_overlook_subject_readable():
    draft = build_citypop_prompt_draft({"visual_mode": "bridge_overlook", "framing_intent": "connective_medium"})

    assert "observational medium shot with bridge-led depth and a clearly anchored subject" in draft
    assert "anchored partial figure" in draft
    assert "environment dominates the frame" not in draft


def test_citypop_prompt_draft_keeps_curbside_silhouette_readable_even_when_world_first():
    draft = build_citypop_prompt_draft({"visual_mode": "curbside_silhouette", "framing_intent": "establishing_wide"})

    assert "one anchored curbside silhouette" in draft
    assert "readable silhouette" in draft
    assert "subject barely legible" not in draft
