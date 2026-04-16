from ai_mv.core.contracts.stage_io import StageInput
from ai_mv.core.stages.plan_citypop_mv import build_plan_preview_payload as legacy_build_plan_preview_payload
from ai_mv.core.stages.plan_citypop_mv import run_plan_citypop_mv
from ai_mv.core.stages.plan_mv import build_plan_preview_payload
from ai_mv.core.stages.plan_mv import run_plan_mv


def _sample_payload() -> dict:
    return {
        "concept_text": "Japanese 80s city pop night drive",
        "audio_map": {
            "duration_sec": 16.0,
            "sections": [
                {"name": "intro", "start_sec": 0.0, "end_sec": 4.0},
                {"name": "chorus", "start_sec": 4.0, "end_sec": 12.0},
                {"name": "outro", "start_sec": 12.0, "end_sec": 16.0},
            ],
        },
    }


def test_citypop_legacy_preview_builder_matches_generic_plan_preview():
    payload = _sample_payload()

    assert legacy_build_plan_preview_payload({}, payload) == build_plan_preview_payload({}, payload)



def test_citypop_legacy_stage_wrapper_matches_generic_plan_stage():
    stage_input = StageInput(run_id="run-legacy", config={}, payload=_sample_payload())

    legacy_out = run_plan_citypop_mv(stage_input)
    generic_out = run_plan_mv(stage_input)

    assert legacy_out.stage == generic_out.stage
    assert legacy_out.status == generic_out.status
    assert legacy_out.payload == generic_out.payload
