from ai_mv.styles.alt_pop.bible import get_alt_pop_bible
from ai_mv.styles.alt_pop.prompting import build_alt_pop_prompt_seed
from ai_mv.styles.alt_pop.rules import alt_pop_section_shot_specs
from ai_mv.styles.dream_pop.bible import get_dream_pop_bible
from ai_mv.styles.dream_pop.prompting import build_dream_pop_prompt_seed
from ai_mv.styles.dream_pop.rules import dream_pop_section_shot_specs
from ai_mv.styles.j_rock.bible import get_j_rock_bible
from ai_mv.styles.j_rock.prompting import build_j_rock_prompt_seed
from ai_mv.styles.j_rock.rules import j_rock_section_shot_specs
from ai_mv.styles.idol_pop.bible import get_idol_pop_bible
from ai_mv.styles.idol_pop.prompting import build_idol_pop_prompt_seed
from ai_mv.styles.idol_pop.rules import idol_pop_section_shot_specs
from ai_mv.styles.k_indie.bible import get_k_indie_bible
from ai_mv.styles.k_indie.prompting import build_k_indie_prompt_seed
from ai_mv.styles.k_indie.rules import k_indie_section_shot_specs


def _visual_mode(specs: list[dict]) -> str:
    assert len(specs) == 1
    return str(specs[0]["visual_mode"])


def test_alt_pop_section_specs_keep_verse_prechorus_and_bridge_visually_distinct():
    verse = _visual_mode(alt_pop_section_shot_specs("verse", 4.0))
    pre_chorus = _visual_mode(alt_pop_section_shot_specs("pre_chorus", 4.0))
    bridge = _visual_mode(alt_pop_section_shot_specs("bridge", 4.0))

    assert len({verse, pre_chorus, bridge}) == 3


def test_idol_pop_section_specs_keep_verse_prechorus_and_bridge_visually_distinct():
    verse = _visual_mode(idol_pop_section_shot_specs("verse", 4.0))
    pre_chorus = _visual_mode(idol_pop_section_shot_specs("pre_chorus", 4.0))
    bridge = _visual_mode(idol_pop_section_shot_specs("bridge", 4.0))

    assert len({verse, pre_chorus, bridge}) == 3


def test_dream_pop_section_specs_keep_verse_prechorus_and_bridge_visually_distinct():
    verse = _visual_mode(dream_pop_section_shot_specs("verse", 4.0))
    pre_chorus = _visual_mode(dream_pop_section_shot_specs("pre_chorus", 4.0))
    bridge = _visual_mode(dream_pop_section_shot_specs("bridge", 4.0))

    assert len({verse, pre_chorus, bridge}) == 3


def test_k_indie_section_specs_keep_verse_prechorus_and_bridge_visually_distinct():
    verse = _visual_mode(k_indie_section_shot_specs("verse", 4.0))
    pre_chorus = _visual_mode(k_indie_section_shot_specs("pre_chorus", 4.0))
    bridge = _visual_mode(k_indie_section_shot_specs("bridge", 4.0))

    assert len({verse, pre_chorus, bridge}) == 3


def test_j_rock_section_specs_keep_verse_prechorus_and_bridge_visually_distinct():
    verse = _visual_mode(j_rock_section_shot_specs("verse", 4.0))
    pre_chorus = _visual_mode(j_rock_section_shot_specs("pre_chorus", 4.0))
    bridge = _visual_mode(j_rock_section_shot_specs("bridge", 4.0))

    assert len({verse, pre_chorus, bridge}) == 3


def test_alt_pop_prompt_seed_changes_across_verse_prechorus_and_bridge_roles():
    bible = get_alt_pop_bible()
    verse = build_alt_pop_prompt_seed(
        "restless alt-pop city night",
        bible,
        {"visual_mode": "glass_corridor", "section_type": "verse", "shot_role": "verse_edge"},
    )
    pre_chorus = build_alt_pop_prompt_seed(
        "restless alt-pop city night",
        bible,
        {"visual_mode": "pre_chorus_tension", "section_type": "pre_chorus", "shot_role": "pre_chorus_tension"},
    )
    bridge = build_alt_pop_prompt_seed(
        "restless alt-pop city night",
        bible,
        {"visual_mode": "bridge_glass", "section_type": "bridge", "shot_role": "bridge_glass"},
    )

    assert len({verse, pre_chorus, bridge}) == 3


def test_alt_pop_style_visual_modes_do_not_replace_non_city_concept_world():
    bible = get_alt_pop_bible()
    concept = "alt-pop forest pier music video, one solitary protagonist follows fireflies over moss and water"
    seeds = [
        build_alt_pop_prompt_seed(
            concept,
            bible,
            {"visual_mode": mode, "section_type": section, "shot_role": role},
        )
        for mode, section, role in [
            ("rooftop_edge", "verse", "verse_edge"),
            ("glass_corridor", "verse", "verse_edge"),
            ("pre_chorus_tension", "pre_chorus", "pre_chorus_tension"),
            ("bridge_glass", "bridge", "bridge_glass"),
            ("chorus_front", "chorus", "chorus_front"),
            ("release_stride", "outro", "release_stride"),
        ]
    ]

    combined = " ".join(seeds).lower()

    assert "forest pier" in combined
    for leaked in (
        "night rooftop",
        "club-adjacent",
        "city reflections",
        "skybridge",
        "city backlight",
        "night street",
        "chrome reflections",
        "rooftop edge",
    ):
        assert leaked not in combined


def test_idol_pop_prompt_seed_changes_across_verse_prechorus_and_bridge_roles():
    bible = get_idol_pop_bible()
    verse = build_idol_pop_prompt_seed(
        "bright idol pop city performance with glossy late-night lights",
        bible,
        {"visual_mode": "city_chorus_walk", "section_type": "verse", "shot_role": "verse_confidence"},
    )
    pre_chorus = build_idol_pop_prompt_seed(
        "bright idol pop city performance with glossy late-night lights",
        bible,
        {"visual_mode": "pre_chorus_lift", "section_type": "pre_chorus", "shot_role": "pre_chorus_lift"},
    )
    bridge = build_idol_pop_prompt_seed(
        "bright idol pop city performance with glossy late-night lights",
        bible,
        {"visual_mode": "bridge_close_gloss", "section_type": "bridge", "shot_role": "bridge_close"},
    )

    assert len({verse, pre_chorus, bridge}) == 3


def test_dream_pop_prompt_seed_changes_across_verse_prechorus_and_bridge_roles():
    bible = get_dream_pop_bible()
    verse = build_dream_pop_prompt_seed(
        "dream-pop midnight haze",
        bible,
        {"visual_mode": "window_haze", "section_type": "verse", "shot_role": "verse_drift"},
    )
    pre_chorus = build_dream_pop_prompt_seed(
        "dream-pop midnight haze",
        bible,
        {"visual_mode": "pre_chorus_lift", "section_type": "pre_chorus", "shot_role": "pre_chorus_lift"},
    )
    bridge = build_dream_pop_prompt_seed(
        "dream-pop midnight haze",
        bible,
        {"visual_mode": "bridge_hush", "section_type": "bridge", "shot_role": "bridge_hush"},
    )

    assert len({verse, pre_chorus, bridge}) == 3


def test_k_indie_prompt_seed_changes_across_verse_prechorus_and_bridge_roles():
    bible = get_k_indie_bible()
    verse = build_k_indie_prompt_seed(
        "k-indie rainy walk home",
        bible,
        {"visual_mode": "crosswalk_wait", "section_type": "verse", "shot_role": "verse_walk"},
    )
    pre_chorus = build_k_indie_prompt_seed(
        "k-indie rainy walk home",
        bible,
        {"visual_mode": "pre_chorus_tension", "section_type": "pre_chorus", "shot_role": "pre_chorus_tension"},
    )
    bridge = build_k_indie_prompt_seed(
        "k-indie rainy walk home",
        bible,
        {"visual_mode": "bridge_pause", "section_type": "bridge", "shot_role": "bridge_pause"},
    )

    assert len({verse, pre_chorus, bridge}) == 3


def test_j_rock_prompt_seed_changes_across_verse_prechorus_and_bridge_roles():
    bible = get_j_rock_bible()
    verse = build_j_rock_prompt_seed(
        "j-rock midnight rush",
        bible,
        {"visual_mode": "amp_corridor", "section_type": "verse", "shot_role": "verse_charge"},
    )
    pre_chorus = build_j_rock_prompt_seed(
        "j-rock midnight rush",
        bible,
        {"visual_mode": "pre_chorus_lift", "section_type": "pre_chorus", "shot_role": "pre_chorus_lift"},
    )
    bridge = build_j_rock_prompt_seed(
        "j-rock midnight rush",
        bible,
        {"visual_mode": "bridge_break", "section_type": "bridge", "shot_role": "bridge_break"},
    )

    assert len({verse, pre_chorus, bridge}) == 3
