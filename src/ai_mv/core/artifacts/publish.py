from __future__ import annotations

from ai_mv.core.artifacts.manifest import write_manifest
from ai_mv.core.artifacts.quality_review import write_quality_review
from ai_mv.core.artifacts.run_summary import write_run_summary
from ai_mv.core.quality_review import build_quality_review, build_run_summary


def write_pipeline_artifacts(state: dict, payload: dict, config: dict) -> None:
    write_manifest(state, payload)
    quality_review = build_quality_review(config, payload)
    write_quality_review(state, quality_review)
    write_run_summary(state, build_run_summary(state, payload, quality_review))
