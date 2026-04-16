from ai_mv.core.orchestration import pipeline
from ai_mv.core.stages.plan_mv import build_plan_preview_payload, run_plan_mv
from ai_mv.core.stages.review_stage import run_review_stage


def test_generic_stage_modules_export_plan_and_review_entrypoints():
    assert callable(build_plan_preview_payload)
    assert callable(run_plan_mv)
    assert callable(run_review_stage)


def test_pipeline_uses_generic_stage_entrypoint_names():
    names = [fn.__name__ for _stage, fn in pipeline._ordered_stages()]

    assert "run_plan_mv" in names
    assert "run_review_stage" in names