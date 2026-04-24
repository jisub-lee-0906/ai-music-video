from __future__ import annotations

import json
from pathlib import Path

from ai_mv.entrypoints.audio_review_batch_score import run_audio_review_batch_score
from ai_mv.entrypoints.audio_reroll import run_audio_reroll_preflight
from ai_mv.entrypoints.audio_reroll_start import run_audio_reroll_start



def run_audio_review_session(
    rubric_path: str,
    updates_json: str,
    verdict: str = "",
    next_action: str = "",
    reroll_mode: str = "none",
    run_id: str | None = None,
    concept_text: str | None = None,
    scope: str = "run",
) -> int:
    normalized_rubric_path = str(rubric_path or "").strip()
    normalized_mode = str(reroll_mode or "none").strip() or "none"
    if normalized_mode not in {"none", "preflight", "start"}:
        raise RuntimeError(f"unsupported reroll_mode: {normalized_mode}")
    batch_rc = run_audio_review_batch_score(
        normalized_rubric_path,
        updates_json,
        verdict,
        next_action,
    )
    if batch_rc != 0:
        return batch_rc
    payload = json.loads(Path(normalized_rubric_path).read_text(encoding="utf-8"))
    overall = payload.get("overall") if isinstance(payload.get("overall"), dict) else {}
    weighted_score = float(overall.get("weighted_score", 0.0) or 0.0)
    print(f"rubric_path={normalized_rubric_path}")
    print(f"reroll_mode={normalized_mode}")
    print(f"weighted_score={weighted_score}")
    if normalized_mode == "none":
        return 0
    if normalized_mode == "preflight":
        return run_audio_reroll_preflight(normalized_rubric_path, run_id, concept_text, scope)
    return run_audio_reroll_start(normalized_rubric_path, run_id, concept_text, scope)
