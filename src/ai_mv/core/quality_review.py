from __future__ import annotations

from ai_mv.core.contracts.prompt_schema import coverage_review_schema
from ai_mv.infra.codex_cli_client import generate_structured


def build_quality_review(config: dict, payload: dict) -> dict:
    review: dict = {}
    coverage = _maybe_review_coverage(config, payload)
    if coverage:
        review["visual"] = coverage
    return review


def build_run_summary(state: dict, payload: dict, quality_review: dict) -> dict:
    audio_map = payload.get("audio_map", {}) if isinstance(payload, dict) else {}
    sections = audio_map.get("sections", []) if isinstance(audio_map, dict) else []
    labels = [str(x.get("label", x.get("name", ""))).strip() for x in sections if isinstance(x, dict)]
    songform = [str(x.get("name", "")).strip() for x in sections if isinstance(x, dict)]
    return {
        "run_id": state["run_id"],
        "profile_name": str(payload.get("selected_profile", "")).strip(),
        "language": str(audio_map.get("language", "")).strip(),
        "selected_songform": songform,
        "selected_labels": labels,
        "failure_reason": str(state.get("failure_reason", "")).strip(),
        "completed_stages": list(state.get("completed_stages", [])),
        "current_stage": str(state.get("current_stage", "")).strip(),
    }


def _maybe_review_coverage(config: dict, payload: dict) -> dict:
    visual = payload.get("visual_brief")
    workflow_inputs = payload.get("workflow_inputs_preview", {})
    if not isinstance(visual, dict) or not isinstance(workflow_inputs, dict):
        return {}
    tti = workflow_inputs.get("tti_anchor", {})
    uso = workflow_inputs.get("uso_chain", {})
    wan = workflow_inputs.get("wan_interpolation", {})
    if not tti or not uso or not wan:
        return {}
    prompt = _coverage_prompt(payload, visual, tti, uso, wan)
    raw = generate_structured(config, prompt, coverage_review_schema())
    return {
        "reasoning": str(raw["reasoning"]).strip(),
        "strengths": [str(x).strip() for x in raw["strengths"] if str(x).strip()],
        "risks": [str(x).strip() for x in raw["risks"] if str(x).strip()],
        "prompt": prompt,
    }


def _coverage_prompt(payload: dict, visual: dict, tti: dict, uso: dict, wan: dict) -> str:
    profile = str(payload.get("audio_map", {}).get("profile_summary", "")).strip()
    sections = _section_summary(visual)
    tti_text = str(tti.get("master_anchor", {}).get("text", tti.get("master_anchor", {}).get("prompt_text", ""))).strip()
    uso_text = _uso_summary(uso)
    wan_text = _wan_summary(wan)
    return (
        "You are a music-video coverage reviewer checking whether the planned visual payload would edit into a compelling MV. "
        "Return JSON only. "
        "Review the single provided plan; do not rank or compare alternatives. "
        "Evaluate same-world continuity, section progression, repeated-return escalation, editability, and character consistency. "
        "Penalize portrait repetition, weak visual payoff in Chorus 2 or Final Chorus, and same-space sections that do not progress. "
        f"Profile={profile}. "
        f"Section dramaturgy={sections}. "
        f"TTI master anchor={tti_text}. "
        f"USO workflow inputs={uso_text}. "
        f"WAN workflow inputs={wan_text}."
    )


def _section_summary(visual: dict) -> str:
    rows = []
    for row in visual.get("section_briefs", []):
        if not isinstance(row, dict):
            continue
        rows.append(
            f"{row.get('section_name','')}: beat={row.get('story_beat','')}; location={row.get('location_anchor','')}; arc={row.get('emotional_arc','')}"
        )
    return " | ".join(rows)


def _uso_summary(uso: dict) -> str:
    items = uso.get("items", []) if isinstance(uso, dict) else []
    rows = []
    for item in items[:12]:
        if not isinstance(item, dict):
            continue
        rows.append(
            f"{item.get('shot_id','')}: phase={item.get('clip_phase','')}; relation={item.get('space_relation','')}; start={item.get('start_text','')}; end={item.get('end_text','')}"
        )
    return " | ".join(rows)


def _wan_summary(wan: dict) -> str:
    clips = wan.get("clips", []) if isinstance(wan, dict) else []
    rows = []
    for clip in clips[:12]:
        if not isinstance(clip, dict):
            continue
        rows.append(
            f"{clip.get('shot_id','')}: energy={clip.get('energy','')}; relation={clip.get('space_relation','')}; pos={clip.get('positive_prompt','')}"
        )
    return " | ".join(rows)
