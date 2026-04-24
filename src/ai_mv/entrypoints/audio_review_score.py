from __future__ import annotations

import json
from pathlib import Path

from ai_mv.core.review.audio_review import summarize_audio_review_payload



def run_audio_review_score(
    rubric_path: str,
    segment_id: str,
    scores_json: str,
    reason_codes_json: str,
    notes: str = "",
    verdict: str = "",
    next_action: str = "",
) -> int:
    path = Path(str(rubric_path or "").strip())
    if not path.exists():
        raise RuntimeError(f"audio review rubric not found: {path}")
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise RuntimeError("audio review rubric must be a JSON object")
    normalized_segment_id = str(segment_id or "").strip()
    scores = _load_scores(scores_json)
    reason_codes = _load_reason_codes(reason_codes_json)
    segment = _find_segment(payload, normalized_segment_id)
    segment["scores"] = scores
    segment["reason_codes"] = reason_codes
    segment["notes"] = str(notes or "")
    summary = summarize_audio_review_payload(payload)
    overall = payload.get("overall") if isinstance(payload.get("overall"), dict) else {}
    payload["overall"] = dict(overall)
    payload["overall"]["weighted_score"] = summary.get("weighted_score", 0.0)
    if str(verdict or "").strip():
        payload["overall"]["verdict"] = str(verdict).strip()
    elif str(summary.get("verdict", "")).strip():
        payload["overall"]["verdict"] = str(summary.get("verdict", "")).strip()
    if str(next_action or "").strip():
        payload["overall"]["recommended_next_action"] = str(next_action).strip()
    elif str(summary.get("recommended_next_action", "")).strip():
        payload["overall"]["recommended_next_action"] = str(summary.get("recommended_next_action", "")).strip()
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(f"rubric_path={path}")
    print(f"segment_id={normalized_segment_id}")
    print(f"weighted_score={payload['overall']['weighted_score']}")
    return 0



def _find_segment(payload: dict, segment_id: str) -> dict:
    for row in payload.get("segments", []):
        if isinstance(row, dict) and str(row.get("segment_id", "")).strip() == segment_id:
            return row
    raise RuntimeError(f"unknown audio review segment_id: {segment_id}")



def _load_scores(raw: str) -> dict:
    parsed = json.loads(str(raw or "{}"))
    if not isinstance(parsed, dict):
        raise RuntimeError("scores_json must decode to a dict")
    out = {}
    for key, value in parsed.items():
        name = str(key or "").strip()
        if not name:
            continue
        out[name] = int(value)
    return out



def _load_reason_codes(raw: str) -> list[str]:
    parsed = json.loads(str(raw or "[]"))
    if not isinstance(parsed, list):
        raise RuntimeError("reason_codes_json must decode to a list")
    out = []
    for value in parsed:
        normalized = str(value or "").strip()
        if normalized and normalized not in out:
            out.append(normalized)
    return out
