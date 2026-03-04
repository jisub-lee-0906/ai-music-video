from ai_mv.core.contracts.errors import StageFailure
from ai_mv.core.contracts.stage_io import StageInput
from ai_mv.core.stages.merge_mux import run_merge_mux


def test_merge_fails_when_inputs_missing():
    stage_input = StageInput(run_id="merge-fail", config={"video": {"target": "1920x1080@24"}}, payload={"clips": [], "music_file": "none.wav"})
    try:
        run_merge_mux(stage_input)
        assert False
    except StageFailure:
        assert True
