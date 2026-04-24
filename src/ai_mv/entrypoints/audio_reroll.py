from __future__ import annotations

from ai_mv.core.artifacts.paths import latest_success_file
from ai_mv.entrypoints.preflight import _load_prepared_config, _prepare_run_brief, run_preflight
from ai_mv.infra.single_flight_lock import acquire_lock, release_lock
from ai_mv.utils.json_utils import read_json



def run_audio_reroll_preflight(
    rubric_path: str,
    run_id: str | None = None,
    concept_text: str | None = None,
    scope: str = "run",
) -> int:
    normalized_rubric_path = str(rubric_path or "").strip()
    if not normalized_rubric_path:
        raise RuntimeError("audio reroll requires a rubric_path")
    resolved_scope = str(scope or "run").strip() or "run"
    rid = run_id or ""
    lock = acquire_lock("audio-reroll-preflight")
    try:
        resolved_concept_text = str(concept_text or "").strip() or _latest_success_concept_text(resolved_scope)
        cfg = _load_prepared_config(resolved_concept_text)
        review = cfg.get("review") if isinstance(cfg.get("review"), dict) else {}
        cfg["review"] = dict(review)
        cfg["review"]["audio_review_rubric_path"] = normalized_rubric_path
        rid = _prepare_run_brief(cfg, rid)
        try:
            run_preflight(cfg, rid, allow_existing_run=True)
            print(f"run_id={rid}")
            print("status=done")
            print(f"rubric_path={normalized_rubric_path}")
            return 0
        except Exception:
            print(f"run_id={rid}")
            print("status=failed")
            print(f"rubric_path={normalized_rubric_path}")
            raise
    finally:
        release_lock(lock)



def _latest_success_concept_text(scope: str) -> str:
    manifest = read_json(latest_success_file("manifest.json", scope))
    input_block = manifest.get("input") if isinstance(manifest.get("input"), dict) else {}
    concept_text = str(input_block.get("concept_text", "")).strip()
    if not concept_text:
        raise RuntimeError(f"latest_success manifest missing input.concept_text for scope={scope}")
    return concept_text
