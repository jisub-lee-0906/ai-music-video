from ai_mv.core.stages import render_verbalizer


def test_verbalize_ref_prompts_uses_minimal_place_action_carry():
    rows = [
        {
            "shot_id": "S001",
            "section_label": "Verse 1",
            "place": "a dim late-night diner",
            "action": "writing in a worn notebook",
            "carry": "worn notebook and half-empty coffee mug",
            "framing": "three-quarter medium framing",
            "literal_image": "Rain beads on the diner window",
            "emotional_turn": "The memory starts to return",
        }
    ]

    out = render_verbalizer.verbalize_ref_prompts({}, rows)

    assert out["S001"].startswith("The performer is writing in a worn notebook in a dim late-night diner, three-quarter medium framing.")
    assert "worn notebook and half-empty coffee mug remain in view".lower() in out["S001"].lower()
    assert "Rain beads on the diner window." in out["S001"]
    assert out["S001"].endswith("Keep the face.")


def test_verbalize_wan_prompts_uses_compact_bridge_sentence():
    rows = [
        {
            "shot_id": "S002",
            "place": "a wet city street at night",
            "bridge_action": "crossing the rainy street with one readable step forward",
            "carry": "worn notebook",
        }
    ]

    out = render_verbalizer.verbalize_wan_prompts({}, rows)

    assert out["S002"].startswith("The performer is crossing the rainy street with one readable step forward on a wet city street at night.")
    assert "The same worn notebook stay in view." in out["S002"]


def test_verbalize_ref_prompts_uses_plural_subject_for_group_voice():
    rows = [
        {
            "shot_id": "S010",
            "section_label": "Chorus",
            "place": "a wet city street at night",
            "action": "walking side by side through the rainy street",
            "carry": "dark coats and wet asphalt",
            "framing": "medium-wide full-body framing",
            "literal_image": "Wet asphalt and blurred headlights stretching across the block",
            "emotional_turn": "The tension loosens into a more direct forward motion",
        }
    ]

    out = render_verbalizer.verbalize_ref_prompts(
        {
            "prompt": "a late-night walk after an argument",
            "genre": "alt rock",
            "voice": "duo mixed, textured and intimate",
            "language": "en",
        },
        rows,
    )

    assert out["S010"].startswith("The performers are walking side by side through the rainy street on a wet city street at night, medium-wide full-body framing.")
    assert out["S010"].endswith("Keep the faces consistent.")
