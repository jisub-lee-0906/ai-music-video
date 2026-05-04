from ai_mv.core.stages.plan_mv import build_plan_preview_payload
from ai_mv.styles.alt_pop.bible import get_alt_pop_bible
from ai_mv.styles.dream_pop.bible import get_dream_pop_bible
from ai_mv.styles.dream_pop.prompting import build_dream_pop_prompt_seed
from ai_mv.styles.j_rock.bible import get_j_rock_bible
from ai_mv.styles.j_rock.prompting import build_j_rock_prompt_seed
from ai_mv.styles.k_indie.bible import get_k_indie_bible
from ai_mv.styles.k_indie.prompting import build_k_indie_prompt_seed
from ai_mv.styles.resolver import STYLE_PACKS, resolve_style_name
from ai_mv.styles.synthwave.bible import get_synthwave_bible
from ai_mv.styles.synthwave.prompting import build_synthwave_prompt_seed



def test_style_registry_includes_all_six_canonical_v1_lanes_with_complete_pack_contracts():
    assert tuple(STYLE_PACKS.keys()) == (
        "citypop",
        "idol_pop",
        "synthwave",
        "dream_pop",
        "alt_pop",
        "k_indie",
        "j_rock",
    )
    for lane_name, pack in STYLE_PACKS.items():
        assert sorted(pack.keys()) == [
            "bible",
            "prompt_draft",
            "prompt_seed",
            "section_specs",
            "section_variants",
        ]
        assert callable(pack["bible"])
        assert callable(pack["prompt_seed"])
        assert callable(pack["prompt_draft"])
        assert callable(pack["section_specs"])
        assert callable(pack["section_variants"])



def test_new_style_lane_scaffolds_expose_distinct_bibles():
    assert get_dream_pop_bible()["style"] == "dream_pop_cinematic_haze"
    assert get_alt_pop_bible()["style"] == "alt_pop_modern_cinematic_edge"
    assert get_k_indie_bible()["style"] == "k_indie_intimate_realism"
    assert get_j_rock_bible()["style"] == "j_rock_performance_drive"



def test_style_resolver_detects_new_canonical_lanes_from_concept_text():
    assert resolve_style_name("dreamy haze soft romance under moonlit overpass") == "dream_pop"
    assert resolve_style_name("bright idol pop city performance with glossy late-night lights") == "idol_pop"
    assert resolve_style_name("edgy alt pop rooftop rebellion with chrome club light") == "alt_pop"
    assert resolve_style_name("k-indie quiet street realism with bookstore rain") == "k_indie"
    assert resolve_style_name("j-rock live house drive with electric chorus sprint") == "j_rock"



def test_plan_preview_accepts_all_six_canonical_style_overrides_for_ambiguous_concept():
    expected_styles = {
        "citypop": "japanese_citypop_80s_90s",
        "idol_pop": "idol_pop_night_performance_gloss",
        "synthwave": "retro_synthwave_nightdrive_80s",
        "dream_pop": "dream_pop_cinematic_haze",
        "alt_pop": "alt_pop_modern_cinematic_edge",
        "k_indie": "k_indie_intimate_realism",
        "j_rock": "j_rock_performance_drive",
    }
    for lane_name, bible_style in expected_styles.items():
        out = build_plan_preview_payload(
            {"planning": {"default_style_name": lane_name}},
            {
                "concept_text": "lonely cinematic road at dusk",
                "audio_map": {
                    "duration_sec": 16.0,
                    "sections": [{"name": "chorus", "start_sec": 0.0, "end_sec": 16.0}],
                },
            },
        )

        assert out["style_lane"] == lane_name
        assert out["style_bible"]["style"] == bible_style
        assert out["style_resolution"]["style_lane"] == lane_name
        assert out["style_resolution"]["selection_source"] == "override"



def test_new_style_prompt_seeds_do_not_hardcode_young_woman_identity():
    cases = [
        (build_synthwave_prompt_seed, get_synthwave_bible(), {"visual_mode": "neon_highway"}),
        (build_dream_pop_prompt_seed, get_dream_pop_bible(), {"visual_mode": "chorus_bloom"}),
        (build_k_indie_prompt_seed, get_k_indie_bible(), {"visual_mode": "chorus_portrait"}),
        (build_j_rock_prompt_seed, get_j_rock_bible(), {"visual_mode": "chorus_charge"}),
    ]
    for builder, bible, shot in cases:
        seed = builder("one solitary protagonist crosses an unfamiliar world", bible, shot).lower()
        assert "young woman" not in seed
        assert "young man" not in seed
        assert "solitary" in seed or "protagonist" in seed


def test_plan_preview_accepts_new_style_override_for_ambiguous_concept():
    out = build_plan_preview_payload(
        {"planning": {"default_style_name": "dream_pop"}},
        {
            "concept_text": "lonely cinematic road at dusk",
            "audio_map": {
                "duration_sec": 16.0,
                "sections": [{"name": "chorus", "start_sec": 0.0, "end_sec": 16.0}],
            },
        },
    )

    assert out["style_lane"] == "dream_pop"
    assert out["style_bible"]["style"] == "dream_pop_cinematic_haze"
    assert out["style_resolution"]["selection_source"] == "override"
