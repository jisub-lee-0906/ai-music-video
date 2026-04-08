from __future__ import annotations

from ai_mv.core.contracts.errors import CodexCliRequestError
from ai_mv.infra.codex_cli_client import generate_structured


def build_llm_review(config: dict, payload: dict) -> dict:
    review_cfg = config.get("review", {}) if isinstance(config, dict) else {}
    if isinstance(review_cfg, dict) and not bool(review_cfg.get("llm_review", True)):
        return _disabled_review()
    prompt = _review_prompt(config, payload)
    try:
        return generate_structured(config, prompt, _review_schema(), attempts=2)
    except CodexCliRequestError as exc:
        return _fallback_review(str(exc))


def _review_prompt(config: dict, payload: dict) -> str:
    audio_plan = payload.get("audio_plan", {}) if isinstance(payload, dict) else {}
    audio_map = payload.get("audio_map", {}) if isinstance(payload, dict) else {}
    prompt_plan = payload.get("prompt_plan", {}) if isinstance(payload, dict) else {}
    ref_items = [row for row in prompt_plan.get("ref_items", []) if isinstance(row, dict)]
    wan_items = [row for row in prompt_plan.get("wan_items", []) if isinstance(row, dict)]
    refs_preview = "\n".join(
        f"- {row.get('shot_id', '')}: {str(row.get('ref_prompt_text', '')).strip()}"
        for row in ref_items[:6]
    ) or "- none"
    wan_preview = "\n".join(
        f"- {row.get('shot_id', '')}: {str(row.get('wan_positive_prompt_text', '')).strip()}"
        for row in wan_items[:6]
    ) or "- none"
    lyrics_preview = _lyrics_preview(audio_plan)
    profile = {
        "prompt": str(config.get("prompt", "")).strip() if isinstance(config, dict) else "",
        "genre": str(config.get("genre", "")).strip() if isinstance(config, dict) else "",
        "voice": str(config.get("voice", "")).strip() if isinstance(config, dict) else "",
        "language": str(config.get("language", "")).strip() if isinstance(config, dict) else "",
        "visual_concept": str(config.get("visual_concept", "")).strip() if isinstance(config, dict) else "",
        "locations": [str(x).strip() for x in config.get("locations", [])] if isinstance(config.get("locations", []), list) else [],
        "props": [str(x).strip() for x in config.get("props", [])] if isinstance(config.get("props", []), list) else [],
        "motifs": [str(x).strip() for x in config.get("motifs", [])] if isinstance(config.get("motifs", []), list) else [],
        "anchor_subject": str(config.get("anchor_subject", "")).strip() if isinstance(config, dict) else "",
    }
    return (
        "You are reviewing an AI music video pipeline run. "
        "This is not a strict pass/fail validator. "
        "Act like an artist, music-video director, and critical creative reviewer. "
        "The project philosophy is music/profile-centered with lyrics as a supporting layer. "
        "Judge likely output quality from the available generated song details, REF prompts, WAN prompts, timing summaries, and file paths. "
        "Do not invent unseen visual details. If something cannot be known directly, say it as a likelihood or risk. "
        "Focus on: music-video coherence, character/world clarity, REF variety, WAN transition usefulness, and whether the final structure likely serves the song. "
        "Return strict JSON only.\n\n"
        f"Profile: {profile}\n"
        f"Audio language: {str(audio_map.get('language', '')).strip()}\n"
        f"Detected BPM: {audio_map.get('timing', {}).get('detected_bpm', 0)}\n"
        f"Audio duration sec: {float(payload.get('audio_duration_sec', audio_map.get('duration_sec', 0.0)) or 0.0):.3f}\n"
        f"Final video duration sec: {float(payload.get('final_duration_sec', 0.0) or 0.0):.3f}\n"
        f"Music file: {str(payload.get('music_file', '')).strip()}\n"
        f"Final video: {str(payload.get('final_video', '')).strip()}\n"
        f"Selected labels: {[str(x.get('label', x.get('name', ''))).strip() for x in audio_map.get('sections', []) if isinstance(x, dict)]}\n"
        f"Lyrics preview:\n{lyrics_preview}\n"
        f"REF count: {len(ref_items)}\n"
        f"WAN count: {len(wan_items)}\n"
        f"REF prompt preview:\n{refs_preview}\n"
        f"WAN prompt preview:\n{wan_preview}\n"
    )


def _lyrics_preview(audio_plan: dict) -> str:
    rows: list[str] = []
    for block in audio_plan.get("lyrics_blocks", []) if isinstance(audio_plan, dict) else []:
        if not isinstance(block, dict):
            continue
        label = str(block.get("label", "")).strip()
        lines = [str(x).strip() for x in block.get("lines", []) if str(x).strip()]
        if not label or not lines:
            continue
        rows.append(f"[{label}] " + " / ".join(lines[:2]))
        if len(rows) >= 5:
            break
    return "\n".join(rows) or "- none"


def _review_schema() -> dict:
    return {
        "type": "object",
        "required": ["summary", "overall_verdict", "strengths", "concerns", "next_focus", "stage_notes"],
        "properties": {
            "summary": {"type": "string"},
            "overall_verdict": {"type": "string", "enum": ["strong", "usable", "mixed", "weak"]},
            "strengths": {"type": "array", "items": {"type": "string"}, "minItems": 1, "maxItems": 5},
            "concerns": {"type": "array", "items": {"type": "string"}, "minItems": 1, "maxItems": 5},
            "next_focus": {"type": "array", "items": {"type": "string"}, "minItems": 1, "maxItems": 5},
            "stage_notes": {
                "type": "object",
                "required": ["audio", "tti", "ref", "wan", "final_mv"],
                "properties": {
                    "audio": {"type": "string"},
                    "tti": {"type": "string"},
                    "ref": {"type": "string"},
                    "wan": {"type": "string"},
                    "final_mv": {"type": "string"},
                },
            },
        },
    }


def _fallback_review(error_text: str) -> dict:
    return {
        "summary": "LLM review could not be generated for this run.",
        "overall_verdict": "mixed",
        "strengths": ["Pipeline artifacts were still produced."],
        "concerns": [f"LLM review failed: {error_text}"],
        "next_focus": ["Re-run the review when Codex CLI is stable."],
        "stage_notes": {
            "audio": "Unavailable because the review call failed.",
            "tti": "Unavailable because the review call failed.",
            "ref": "Unavailable because the review call failed.",
            "wan": "Unavailable because the review call failed.",
            "final_mv": "Unavailable because the review call failed.",
        },
    }


def _disabled_review() -> dict:
    return {
        "summary": "LLM review is disabled in config.",
        "overall_verdict": "mixed",
        "strengths": ["Technical artifacts can still be inspected separately."],
        "concerns": ["LLM critique was not requested for this run."],
        "next_focus": ["Enable review.llm_review to generate a creative review artifact."],
        "stage_notes": {
            "audio": "Disabled.",
            "tti": "Disabled.",
            "ref": "Disabled.",
            "wan": "Disabled.",
            "final_mv": "Disabled.",
        },
    }
