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

    assert "SubjectForm: single person." in out["S001"]
    assert "Action: writing in a worn notebook." in out["S001"]
    assert "Place: a dim late-night diner." in out["S001"]
    assert "Detail: Rain beads on the diner window." in out["S001"]
    assert "Carry: worn notebook and half-empty coffee mug." in out["S001"]
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

    assert "SubjectForm: single person." in out["S002"]
    assert "Motion: crossing the rainy street with one readable step forward." in out["S002"]
    assert "Place: a wet city street at night." in out["S002"]
    assert "Carry: worn notebook." in out["S002"]


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

    assert "SubjectForm: plural." in out["S010"]
    assert "Action: walking side by side through the rainy street." in out["S010"]
    assert out["S010"].endswith("Keep the faces consistent.")


def test_verbalize_ref_prompts_uses_female_subject_for_solo_female_voice():
    rows = [
        {
            "shot_id": "S011",
            "section_label": "Verse 1",
            "place": "a wet city street at night",
            "action": "walking alone through the rainy street",
            "carry": "wet asphalt",
            "framing": "medium-wide full-body framing",
            "literal_image": "Wet asphalt and blurred headlights stretching across the block",
        }
    ]

    out = render_verbalizer.verbalize_ref_prompts(
        {
            "prompt": "late-night breakup walk",
            "genre": "synth pop",
            "voice": "solo female, airy and emotional",
            "language": "ko",
        },
        rows,
    )

    assert "SubjectForm: single female." in out["S011"]
    assert "Action: walking alone through the rainy street." in out["S011"]
    assert out["S011"].endswith("Keep the face.")
