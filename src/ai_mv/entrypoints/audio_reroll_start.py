from __future__ import annotations

from ai_mv.core.artifacts.paths import latest_success_file
from ai_mv.entrypoints.start import _load_prepared_config, _prepare_comfy_queue, _prepare_run_brief
from ai_mv.core.orchestration.pipeline import run_pipeline
from ai_mv.entrypoints.doctor import run_doctor
from ai_mv.infra.single_flight_lock import acquire_lock, release_lock
from ai_mv.core.state.state_store import read_snapshot
from ai_mv.utils.json_utils import read_json



def run_audio_reroll_start(
    rubric_path: str,
    run_id: str | None = None,
    concept_text: str | None = None,
    scope: str = "run",
) -> int:
    normalized_rubric_path = str(rubric_path or "").strip()
    if not normalized_rubric_path:
        raise RuntimeError("audio reroll start requires a rubric_path")
    resolved_scope = str(scope or "run").strip() or "run"
    rid = run_id or ""
    lock = acquire_lock("audio-reroll-start")
    try:
        explicit_concept_text = str(concept_text or "").strip()
        latest_success = _latest_success_defaults(resolved_scope) if not explicit_concept_text else {"concept_text": explicit_concept_text, "default_style_name": ""}
        resolved_concept_text = explicit_concept_text or latest_success["concept_text"]
        cfg = _load_prepared_config(resolved_concept_text)
        planning = cfg.get("planning") if isinstance(cfg.get("planning"), dict) else {}
        cfg["planning"] = dict(planning)
        default_style_name = str(latest_success.get("default_style_name", "")).strip()
        if default_style_name and not str(cfg["planning"].get("default_style_name", "")).strip():
            cfg["planning"]["default_style_name"] = default_style_name
        review = cfg.get("review") if isinstance(cfg.get("review"), dict) else {}
        cfg["review"] = dict(review)
        cfg["review"]["audio_review_rubric_path"] = normalized_rubric_path
        if run_doctor(cfg) != 0:
            return 1
        _prepare_comfy_queue(cfg)
        rid = _prepare_run_brief(cfg, rid)
        run_pipeline(cfg, rid, allow_existing_run=True)
        snap = read_snapshot(rid)
        print(f"run_id={rid}")
        print(f"status={snap['status']}")
        print(f"failure_reason={snap['failure_reason']}")
        print(f"rubric_path={normalized_rubric_path}")
        return 0 if snap["status"] == "done" else 1
    finally:
        release_lock(lock)



def _latest_success_defaults(scope: str) -> dict:
    manifest = read_json(latest_success_file("manifest.json", scope))
    input_block = manifest.get("input") if isinstance(manifest.get("input"), dict) else {}
    concept_text = str(input_block.get("concept_text", "")).strip()
    if not concept_text:
        raise RuntimeError(f"latest_success manifest missing input.concept_text for scope={scope}")
    plan_block = manifest.get("plan") if isinstance(manifest.get("plan"), dict) else {}
    default_style_name = str(plan_block.get("style_lane", "")).strip()
    return {"concept_text": concept_text, "default_style_name": default_style_name}
