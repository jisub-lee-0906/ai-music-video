from ai_mv.core.stages.plan_mv import build_plan_preview_payload
from ai_mv.styles.alt_pop.bible import get_alt_pop_bible
from ai_mv.styles.dream_pop.bible import get_dream_pop_bible
from ai_mv.styles.j_rock.bible import get_j_rock_bible
from ai_mv.styles.k_indie.bible import get_k_indie_bible
from ai_mv.styles.resolver import resolve_style_name



def test_new_style_lane_scaffolds_expose_distinct_bibles():
    assert get_dream_pop_bible()["style"] == "dream_pop_cinematic_haze"
    assert get_alt_pop_bible()["style"] == "alt_pop_modern_cinematic_edge"
    assert get_k_indie_bible()["style"] == "k_indie_intimate_realism"
    assert get_j_rock_bible()["style"] == "j_rock_performance_drive"



def test_style_resolver_detects_new_canonical_lanes_from_concept_text():
    assert resolve_style_name("dreamy haze soft romance under moonlit overpass") == "dream_pop"
    assert resolve_style_name("edgy alt pop rooftop rebellion with chrome club light") == "alt_pop"
    assert resolve_style_name("k-indie quiet street realism with bookstore rain") == "k_indie"
    assert resolve_style_name("j-rock live house drive with electric chorus sprint") == "j_rock"



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

    assert out["style_name"] == "dream_pop"
    assert out["style_bible"]["style"] == "dream_pop_cinematic_haze"
    assert out["style_resolution"]["selection_source"] == "override"
