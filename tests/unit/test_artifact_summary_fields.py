import importlib


def test_artifact_summary_fields_helper_derives_style_and_assembly_revision_metadata():
    helper_module = importlib.import_module("ai_mv.core.artifacts.summary_fields")

    out = helper_module.derive_summary_fields(
        {
            "style_name": "fallback_style",
            "style_resolution": {
                "style_name": "citypop",
                "selection_source": "auto",
                "selection_stability": "stable",
                "confidence": 0.93,
            },
            "review_report": {
                "assembly_revision_summary": {
                    "present": True,
                    "action": "revise_transition_selection",
                    "target": "assembly",
                    "final_video": "final.mp4",
                    "music_file": "music.mp3",
                }
            },
        }
    )

    assert out == {
        "style_name": "citypop",
        "style_selection_source": "auto",
        "style_selection_stability": "stable",
        "style_selection_confidence": 0.93,
        "assembly_revision_present": True,
        "assembly_revision_action": "revise_transition_selection",
        "assembly_revision_target": "assembly",
        "assembly_revision_final_video": "final.mp4",
        "assembly_revision_music_file": "music.mp3",
    }



def test_artifact_summary_fields_helper_preserves_fallbacks_and_sanitizes_invalid_confidence():
    helper_module = importlib.import_module("ai_mv.core.artifacts.summary_fields")

    out = helper_module.derive_summary_fields(
        {
            "style_name": "dream_pop",
            "style_resolution": {
                "selection_source": "override",
                "selection_stability": "volatile",
                "confidence": "nan",
            },
            "review_report": {},
        }
    )

    assert out == {
        "style_name": "dream_pop",
        "style_selection_source": "override",
        "style_selection_stability": "volatile",
        "style_selection_confidence": 0.0,
        "assembly_revision_present": False,
        "assembly_revision_action": "",
        "assembly_revision_target": "",
        "assembly_revision_final_video": "",
        "assembly_revision_music_file": "",
    }
