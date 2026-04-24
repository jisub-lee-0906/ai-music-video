from __future__ import annotations

import json
from pathlib import Path


def load_audio_review_summary(path_value: object) -> dict[str, object]:
    path_str = str(path_value or "").strip()
    if not path_str:
        return {}
    try:
        payload = json.loads(Path(path_str).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"invalid audio review rubric file: {path_str}") from exc
    return summarize_audio_review_payload(payload)


def summarize_audio_review_payload(payload: object) -> dict[str, object]:
    if not isinstance(payload, dict):
        return {}
    weights = _weights(payload)
    segments = [row for row in payload.get("segments", []) if isinstance(row, dict)]
    reason_codes = sorted({str(reason).strip() for row in segments for reason in row.get("reason_codes", []) if str(reason).strip()})
    axis_scores = _axis_scores(segments)
    weighted_score = _resolved_weighted_score(payload, weights, axis_scores)
    if weighted_score <= 0.0 and not reason_codes and not axis_scores:
        return {"status": "pending", "weighted_score": 0.0, "recommended_next_action": "", "reason_codes": [], "prescription": {}}
    recommended_next_action = _recommended_next_action(weighted_score)
    prescription = _prescription(reason_codes)
    overall = payload.get("overall") if isinstance(payload.get("overall"), dict) else {}
    verdict = str(overall.get("verdict", "")).strip() or _default_verdict(reason_codes, weighted_score)
    return {
        "status": "reviewed",
        "weighted_score": weighted_score,
        "verdict": verdict,
        "recommended_next_action": str(overall.get("recommended_next_action", "")).strip() or recommended_next_action,
        "reason_codes": reason_codes,
        "axis_scores": axis_scores,
        "prescription": prescription,
    }


def _weights(payload: dict) -> dict[str, float]:
    scoring = payload.get("scoring") if isinstance(payload.get("scoring"), dict) else {}
    raw = scoring.get("weights") if isinstance(scoring.get("weights"), dict) else {}
    return {str(key).strip(): float(value) for key, value in raw.items() if str(key).strip()}


def _axis_scores(segments: list[dict]) -> dict[str, float]:
    buckets: dict[str, list[float]] = {}
    for row in segments:
        scores = row.get("scores") if isinstance(row.get("scores"), dict) else {}
        for axis, value in scores.items():
            try:
                parsed = float(value)
            except Exception:
                continue
            if parsed <= 0.0:
                continue
            buckets.setdefault(str(axis).strip(), []).append(parsed)
    return {axis: round(sum(values) / len(values), 3) for axis, values in buckets.items() if axis}


def _resolved_weighted_score(payload: dict, weights: dict[str, float], axis_scores: dict[str, float]) -> float:
    overall = payload.get("overall") if isinstance(payload.get("overall"), dict) else {}
    existing = overall.get("weighted_score")
    try:
        if existing is not None:
            parsed = float(existing)
            if parsed > 0.0:
                return round(parsed, 2)
    except Exception:
        pass
    total_weight = sum(weight for axis, weight in weights.items() if axis in axis_scores)
    if total_weight <= 0.0:
        return 0.0
    earned = sum((axis_scores[axis] / 5.0) * weight for axis, weight in weights.items() if axis in axis_scores)
    return round((earned / total_weight) * 100.0, 2)


def _recommended_next_action(weighted_score: float) -> str:
    if weighted_score >= 85.0:
        return "publish"
    if weighted_score >= 75.0:
        return "optional_audio_reroll"
    if weighted_score >= 65.0:
        return "revise_audio_prompt_and_regenerate"
    return "regenerate_audio"


def _default_verdict(reason_codes: list[str], weighted_score: float) -> str:
    if reason_codes:
        return ", ".join(reason_codes)
    if weighted_score >= 85.0:
        return "strong listening review"
    if weighted_score >= 75.0:
        return "usable with minor audio caveats"
    if weighted_score >= 65.0:
        return "needs another audio quality loop"
    return "audio needs regeneration"


def _prescription(reason_codes: list[str]) -> dict[str, object]:
    if not reason_codes:
        return {}
    if "weak_hook" in reason_codes and ("muddy_vocals" in reason_codes or "pronunciation_artifacts" in reason_codes):
        return {
            "fix_strategy": "strengthen_hook_and_clean_vocal_delivery",
            "prompt_contract_focus": ["hook_brief", "vocal_profile", "audio_direction"],
            "reason_codes": reason_codes,
        }
    if "weak_hook" in reason_codes or "weak_chorus_lift" in reason_codes:
        return {
            "fix_strategy": "strengthen_hook_and_chorus_lift",
            "prompt_contract_focus": ["hook_brief", "audio_direction"],
            "reason_codes": reason_codes,
        }
    if "muddy_vocals" in reason_codes or "pronunciation_artifacts" in reason_codes:
        return {
            "fix_strategy": "clean_vocal_delivery_and_pronunciation",
            "prompt_contract_focus": ["vocal_profile", "language", "audio_direction"],
            "reason_codes": reason_codes,
        }
    if "generic_genre_hit" in reason_codes or "weak_mv_cues" in reason_codes:
        return {
            "fix_strategy": "tighten_genre_identity_and_mv_cues",
            "prompt_contract_focus": ["genre_description", "audio_direction", "hook_brief"],
            "reason_codes": reason_codes,
        }
    return {
        "fix_strategy": "revise_audio_prompt_and_regenerate",
        "prompt_contract_focus": ["audio_direction", "hook_brief"],
        "reason_codes": reason_codes,
    }



def apply_audio_review_prescription(audio: dict, summary: dict | None) -> dict:
    source = dict(audio) if isinstance(audio, dict) else {}
    normalized = dict(summary) if isinstance(summary, dict) else {}
    if str(normalized.get("recommended_next_action", "")).strip() == "publish":
        return source
    prescription = normalized.get("prescription") if isinstance(normalized.get("prescription"), dict) else {}
    if not prescription:
        return source
    reason_codes = [str(value).strip() for value in normalized.get("reason_codes", []) if str(value).strip()] if isinstance(normalized.get("reason_codes"), list) else []
    fix_strategy = str(prescription.get("fix_strategy", "")).strip()
    updated = dict(source)
    if fix_strategy == "strengthen_hook_and_clean_vocal_delivery":
        updated["hook_brief"] = _append_sentence(updated.get("hook_brief", ""), "Make the chorus hook instantly memorable, title-grade, and easy to sing back")
        updated["brief"] = _append_sentence(updated.get("brief", ""), "Prioritize clearer vocal delivery, cleaner pronunciation, and a stronger chorus lift")
        updated["vocal_profile"] = _append_csv(updated.get("vocal_profile", ""), "clear diction")
    elif fix_strategy == "strengthen_hook_and_chorus_lift":
        updated["hook_brief"] = _append_sentence(updated.get("hook_brief", ""), "Make the chorus hook more immediate, memorable, and emotionally decisive")
        updated["brief"] = _append_sentence(updated.get("brief", ""), "Push a larger chorus lift with stronger payoff and cleaner release energy")
    elif fix_strategy == "clean_vocal_delivery_and_pronunciation":
        updated["brief"] = _append_sentence(updated.get("brief", ""), "Prioritize cleaner vocal delivery, stable pronunciation, and less smeared phrasing")
        updated["vocal_profile"] = _append_csv(updated.get("vocal_profile", ""), "clear diction")
    elif fix_strategy == "tighten_genre_identity_and_mv_cues":
        updated["brief"] = _append_sentence(updated.get("brief", ""), "Strengthen genre identity and make section lifts more usable for MV editing cues")
        updated["hook_brief"] = _append_sentence(updated.get("hook_brief", ""), "Keep the chorus cue-rich and visually legible at the first hit")
    updated["negative_direction"] = _append_csv(updated.get("negative_direction", ""), *_reason_code_avoid_phrases(reason_codes))
    return updated



def _append_sentence(base: object, addition: str) -> str:
    left = str(base or "").strip().rstrip(". ")
    right = str(addition or "").strip().rstrip(". ")
    if not right:
        return left
    if not left:
        return right
    if right.lower() in left.lower():
        return left
    return f"{left}. {right}"



def _append_csv(base: object, *items: str) -> str:
    existing = [part.strip() for part in str(base or "").split(",") if part.strip()]
    lowered = {part.lower() for part in existing}
    for item in items:
        normalized = str(item or "").strip()
        if normalized and normalized.lower() not in lowered:
            existing.append(normalized)
            lowered.add(normalized.lower())
    return ", ".join(existing)



def _reason_code_avoid_phrases(reason_codes: list[str]) -> list[str]:
    mapping = {
        "muddy_vocals": "muddy vocals",
        "pronunciation_artifacts": "unclear pronunciation",
        "weak_hook": "forgettable hook",
        "weak_chorus_lift": "flat chorus lift",
        "weak_mv_cues": "weak edit cues",
        "generic_genre_hit": "generic genre texture",
    }
    return [mapping[code] for code in reason_codes if code in mapping]
