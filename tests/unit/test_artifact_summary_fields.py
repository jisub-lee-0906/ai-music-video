import importlib


def test_artifact_summary_fields_helper_derives_style_and_assembly_revision_metadata():
    helper_module = importlib.import_module("ai_mv.core.artifacts.summary_fields")

    out = helper_module.derive_summary_fields(
        {
            "style_lane": "fallback_lane",
            "style_resolution": {
                "style_lane": "citypop",
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
                    "target_shots": ["S010"],
                    "target_material_ids": ["MAT_010"],
                    "target_section_ids": ["SEC_010"],
                }
            },
        }
    )

    assert out == {
        "style_lane": "citypop",
        "style_selection_source": "auto",
        "style_selection_stability": "stable",
        "style_selection_confidence": 0.93,
        "assembly_revision_present": True,
        "assembly_revision_action": "revise_transition_selection",
        "assembly_revision_target": "assembly",
        "assembly_revision_final_video": "final.mp4",
        "assembly_revision_music_file": "music.mp3",
        "assembly_revision_target_shots": ["S010"],
        "assembly_revision_target_material_ids": ["MAT_010"],
        "assembly_revision_target_section_ids": ["SEC_010"],
    }



def test_artifact_summary_fields_helper_preserves_fallbacks_and_sanitizes_invalid_confidence():
    helper_module = importlib.import_module("ai_mv.core.artifacts.summary_fields")

    out = helper_module.derive_summary_fields(
        {
            "style_lane": "dream_pop",
            "style_resolution": {
                "selection_source": "override",
                "selection_stability": "volatile",
                "confidence": "nan",
            },
            "review_report": {},
        }
    )

    assert out == {
        "style_lane": "dream_pop",
        "style_selection_source": "override",
        "style_selection_stability": "volatile",
        "style_selection_confidence": 0.0,
        "assembly_revision_present": False,
        "assembly_revision_action": "",
        "assembly_revision_target": "",
        "assembly_revision_final_video": "",
        "assembly_revision_music_file": "",
        "assembly_revision_target_shots": [],
        "assembly_revision_target_material_ids": [],
        "assembly_revision_target_section_ids": [],
    }
