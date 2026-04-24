from __future__ import annotations

import json
from pathlib import Path

from ai_mv.core.review.audio_review import summarize_audio_review_payload



def run_audio_review_batch_score(
    rubric_path: str,
    updates_json: str,
    verdict: str = "",
    next_action: str = "",
) -> int:
    path = Path(str(rubric_path or "").strip())
    if not path.exists():
        raise RuntimeError(f"audio review rubric not found: {path}")
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise RuntimeError("audio review rubric must be a JSON object")
    updates = _load_updates(updates_json)
    updated_count = 0
    for row in updates:
        segment = _find_segment(payload, str(row.get("segment_id", "")).strip())
        segment["scores"] = dict(row.get("scores", {}))
        segment["reason_codes"] = list(row.get("reason_codes", []))
        segment["notes"] = str(row.get("notes", ""))
        updated_count += 1
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
    print(f"updated_segments={updated_count}")
    print(f"weighted_score={payload['overall']['weighted_score']}")
    return 0



def _load_updates(raw: str) -> list[dict]:
    parsed = json.loads(str(raw or "[]"))
    if not isinstance(parsed, list):
        raise RuntimeError("updates_json must decode to a list")
    out = []
    for row in parsed:
        if not isinstance(row, dict):
            continue
        out.append(
            {
                "segment_id": str(row.get("segment_id", "")).strip(),
                "scores": {str(key).strip(): int(value) for key, value in (row.get("scores") or {}).items() if str(key).strip()} if isinstance(row.get("scores"), dict) else {},
                "reason_codes": [str(value).strip() for value in row.get("reason_codes", []) if str(value).strip()] if isinstance(row.get("reason_codes"), list) else [],
                "notes": str(row.get("notes", "")),
            }
        )
    return out



def _find_segment(payload: dict, segment_id: str) -> dict:
    for row in payload.get("segments", []):
        if isinstance(row, dict) and str(row.get("segment_id", "")).strip() == segment_id:
            return row
    raise RuntimeError(f"unknown audio review segment_id: {segment_id}")
