import pytest

from ai_mv.core.contracts.errors import StageFailure
from ai_mv.core.orchestration.input_gate import validate_stage_input


def test_gate_rejects_empty_merge_inputs():
    with pytest.raises(StageFailure):
        validate_stage_input("assemble", {"clip_results": [], "music_file": ""})


def test_gate_accepts_planning_chain():
    validate_stage_input(
        "plan",
        {
            "audio_plan": {"genre_description": "x"},
            "audio_map": {"sections": [{"name": "verse"}]},
            "music_file": "music.mp3",
        },
    )
    validate_stage_input(
        "stills",
        {
            "shot_plan": [{"shot_id": "S001", "material_id": "MAT_001"}],
            "material_plan": [{"material_id": "MAT_001", "section_id": "SEC_001"}],
            "render_plan": [{"shot_id": "S001", "material_id": "MAT_001", "render_mode": "ia2v"}],
            "style_bible": {"style": "citypop"},
        },
    )


def test_gate_accepts_render_chain():
    validate_stage_input(
        "clips",
        {
            "shot_plan": [{"shot_id": "S001", "material_id": "MAT_001"}],
            "render_plan": [{"shot_id": "S001", "material_id": "MAT_001", "render_mode": "ia2v"}],
            "still_results": [{"shot_id": "S001", "material_id": "MAT_001", "image": "stills/S001.png"}],
            "music_file": "music.mp3",
        },
    )



def test_gate_rejects_stills_inputs_when_material_linkage_is_missing():
    with pytest.raises(StageFailure):
        validate_stage_input(
            "stills",
            {
                "shot_plan": [{"shot_id": "S001", "material_id": ""}],
                "material_plan": [{"material_id": "MAT_001", "section_id": "SEC_001"}],
                "render_plan": [{"shot_id": "S001", "material_id": "MAT_001", "render_mode": "ia2v"}],
                "style_bible": {"style": "citypop"},
            },
        )



def test_gate_rejects_stills_inputs_when_render_plan_material_id_belongs_to_another_shot():
    with pytest.raises(StageFailure):
        validate_stage_input(
            "stills",
            {
                "shot_plan": [
                    {"shot_id": "S001", "material_id": "MAT_001"},
                    {"shot_id": "S002", "material_id": "MAT_002"},
                ],
                "material_plan": [
                    {"material_id": "MAT_001", "section_id": "SEC_001"},
                    {"material_id": "MAT_002", "section_id": "SEC_002"},
                ],
                "render_plan": [
                    {"shot_id": "S001", "material_id": "MAT_002", "render_mode": "ia2v"},
                    {"shot_id": "S002", "material_id": "MAT_001", "render_mode": "ia2v"},
                ],
                "style_bible": {"style": "citypop"},
            },
        )



def test_gate_rejects_stills_inputs_when_render_plan_contains_unknown_shot_id():
    with pytest.raises(StageFailure):
        validate_stage_input(
            "stills",
            {
                "shot_plan": [{"shot_id": "S001", "material_id": "MAT_001"}],
                "material_plan": [{"material_id": "MAT_001", "section_id": "SEC_001"}],
                "render_plan": [
                    {"shot_id": "S001", "material_id": "MAT_001", "render_mode": "ia2v"},
                    {"shot_id": "S999", "material_id": "MAT_001", "render_mode": "ia2v"},
                ],
                "style_bible": {"style": "citypop"},
            },
        )



def test_gate_rejects_stills_inputs_when_material_plan_contains_unused_row():
    with pytest.raises(StageFailure):
        validate_stage_input(
            "stills",
            {
                "shot_plan": [{"shot_id": "S001", "material_id": "MAT_001"}],
                "material_plan": [
                    {"material_id": "MAT_001", "section_id": "SEC_001"},
                    {"material_id": "MAT_999", "section_id": "SEC_999"},
                ],
                "render_plan": [{"shot_id": "S001", "material_id": "MAT_001", "render_mode": "ia2v"}],
                "style_bible": {"style": "citypop"},
            },
        )



def test_gate_rejects_clips_inputs_when_still_material_id_disagrees_with_render_linkage():
    with pytest.raises(StageFailure):
        validate_stage_input(
            "clips",
            {
                "shot_plan": [{"shot_id": "S001", "material_id": "MAT_001"}],
                "render_plan": [{"shot_id": "S001", "material_id": "MAT_001", "render_mode": "ia2v"}],
                "still_results": [{"shot_id": "S001", "material_id": "MAT_999", "image": "stills/S001.png"}],
                "music_file": "music.mp3",
            },
        )



def test_gate_rejects_clips_inputs_when_still_results_contains_unknown_shot_id():
    with pytest.raises(StageFailure):
        validate_stage_input(
            "clips",
            {
                "shot_plan": [{"shot_id": "S001", "material_id": "MAT_001"}],
                "render_plan": [{"shot_id": "S001", "material_id": "MAT_001", "render_mode": "ia2v"}],
                "still_results": [
                    {"shot_id": "S001", "material_id": "MAT_001", "image": "stills/S001.png"},
                    {"shot_id": "S999", "material_id": "MAT_001", "image": "stills/S999.png"},
                ],
                "music_file": "music.mp3",
            },
        )



def test_gate_rejects_clips_inputs_when_render_plan_contains_unknown_shot_id():
    with pytest.raises(StageFailure):
        validate_stage_input(
            "clips",
            {
                "shot_plan": [{"shot_id": "S001", "material_id": "MAT_001"}],
                "render_plan": [
                    {"shot_id": "S001", "material_id": "MAT_001", "render_mode": "ia2v"},
                    {"shot_id": "S999", "material_id": "", "render_mode": "ia2v"},
                ],
                "still_results": [{"shot_id": "S001", "material_id": "MAT_001", "image": "stills/S001.png"}],
                "music_file": "music.mp3",
            },
        )



def test_gate_rejects_clips_inputs_when_duplicate_still_rows_exist():
    with pytest.raises(StageFailure):
        validate_stage_input(
            "clips",
            {
                "shot_plan": [{"shot_id": "S001", "material_id": "MAT_001"}],
                "render_plan": [{"shot_id": "S001", "material_id": "MAT_001", "render_mode": "ia2v"}],
                "still_results": [
                    {"shot_id": "S001", "material_id": "MAT_001", "image": "stills/S001.png"},
                    {"shot_id": "S001", "material_id": "MAT_001", "image": "stills/S001-dup.png"},
                ],
                "music_file": "music.mp3",
            },
        )



def test_gate_rejects_clips_inputs_when_still_results_contains_unplanned_dependency_row():
    with pytest.raises(StageFailure):
        validate_stage_input(
            "clips",
            {
                "shot_plan": [{"shot_id": "S002", "material_id": "MAT_002"}],
                "render_plan": [{"shot_id": "S002", "material_id": "MAT_002", "render_mode": "ia2v"}],
                "still_results": [
                    {"shot_id": "S002", "material_id": "MAT_002", "image": "stills/S002.png"},
                    {"shot_id": "S004", "material_id": "MAT_004", "image": "stills/S004.png"},
                ],
                "music_file": "music.mp3",
            },
        )
