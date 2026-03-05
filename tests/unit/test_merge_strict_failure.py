from ai_mv.core.contracts.errors import StageFailure
from ai_mv.core.contracts.stage_io import StageInput
from ai_mv.core.stages.merge_mux import run_merge_mux


def test_merge_fails_when_inputs_missing():
    cfg = {
        "video": {"target": "1920x1080@24"},
        "integrations": {"comfyui_output_dir": "C:/tmp/not-used"},
    }
    stage_input = StageInput(run_id="merge-fail", config=cfg, payload={"clips": [], "music_file": "none.wav"})
    try:
        run_merge_mux(stage_input)
        assert False
    except StageFailure:
        assert True
