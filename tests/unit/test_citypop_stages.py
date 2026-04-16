from ai_mv.core.stages.plan_citypop_mv import build_plan_preview_payload as legacy_build_plan_preview_payload
from ai_mv.core.stages.plan_mv import build_plan_preview_payload



def test_citypop_legacy_stage_module_still_exports_preview_builder():
    payload = {
        "concept_text": "Japanese 80s city pop",
        "audio_map": {
            "duration_sec": 8.0,
            "sections": [{"name": "chorus", "start_sec": 0.0, "end_sec": 8.0}],
        },
    }

    assert legacy_build_plan_preview_payload({}, payload) == build_plan_preview_payload({}, payload)
