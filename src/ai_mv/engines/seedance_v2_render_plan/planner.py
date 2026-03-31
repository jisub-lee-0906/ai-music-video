from __future__ import annotations

from ai_mv.core.contracts.seedance_v2_normalize import normalize_render_plan_v2
from ai_mv.core.director_brief import build_director_brief_intent
from ai_mv.core.stages.render_verbalizer_v2 import verbalize_ref_prompt_pairs, verbalize_wan_prompts


def build_render_plan_v2(config: dict, payload: dict) -> dict:
    brief = build_director_brief_intent(config)
    director_plan = payload["director_plan_v2"]
    shot_packages: list[dict] = []
    wan_chain: list[dict] = []
    previous_chain_key = ""
    for index, shot in enumerate(director_plan.get("shot_packages", []), start=1):
        shot_row = dict(shot)
        shot_row["render_strategy"] = "ref_pair"
        shot_row["ref_prompt_clauses"] = {
            "subject_intro": str(brief.get("ref_subject_intro", "")).strip() or "The same Korean female idol",
            "location": _render_location_clause(shot_row),
            "start_state": str(shot_row.get("ref_start_action_line", "")).strip() or str(shot_row.get("subject_action", "")).strip() or str(shot_row.get("visible_action", "")).strip(),
            "end_state": str(shot_row.get("ref_end_action_line", "")).strip() or str(shot_row.get("subject_action", "")).strip() or str(shot_row.get("visible_action", "")).strip(),
            "lighting": str(shot_row.get("ref_lighting_line", "")).strip() or str(shot_row.get("lighting_intent", "")).strip(),
        }
        shot_packages.append(shot_row)
        chain_key = f"{shot_row['shot_id']}:{index}"
        wan_row = {
            "shot_id": shot_row["shot_id"],
            "render_strategy": "wan_chain",
            "start_source": "ref_start" if index == 1 else "previous_end",
            "previous_chain_key": previous_chain_key,
            "chain_key": chain_key,
            "end_source": f"ref_end:{shot_row['shot_id']}",
            "environment_anchor": shot_row["environment_anchor"],
            "location_description": str(shot_row.get("location_description", "")).strip(),
            "lighting_intent": str(shot_row.get("lighting_intent", "")).strip(),
            "duration_sec": float(shot_row.get("duration_sec", 2.0) or 2.0),
            "literal_image": str(shot_row.get("literal_image", "")).strip(),
            "visible_action": str(shot_row.get("visible_action", "")).strip(),
            "subject_action": str(shot_row.get("subject_action", "")).strip(),
            "wan_action_line": str(shot_row.get("wan_action_line", "")).strip(),
        }
        wan_row["wan_prompt_clauses"] = {
            "subject_intro": str(brief.get("ref_subject_intro", "")).strip() or "The same Korean female idol",
            "location": _render_location_clause(wan_row),
            "bridge_action": str(wan_row.get("wan_action_line", "")).strip() or str(wan_row.get("subject_action", "")).strip() or str(wan_row.get("visible_action", "")).strip(),
            "lighting": str(wan_row.get("lighting_intent", "")).strip(),
        }
        wan_chain.append(wan_row)
        previous_chain_key = chain_key
    _verbalize_render_prompts(config, shot_packages, wan_chain)
    render_plan = {
        "master_anchor": {
            "render_strategy": "tti_master",
            "identity_core": brief["identity_core"],
            "style_contract": brief["style_contract"],
            "camera_intent": "neutral presentation pose with readable full-body character reference",
            "environment_anchor": "simple pale backdrop for anchor extraction",
        },
        "shot_packages": shot_packages,
        "wan_chain": wan_chain,
    }
    return normalize_render_plan_v2(render_plan)


def build_render_plan_v2_preview_prompt(config: dict, payload: dict) -> str:
    return (
        "Map each director shot into backend strategies using one global TTI master anchor, "
        "REF start/end image pairs per shot, a meaning-preserving render verbalizer for natural prompt prose, "
        "and a WAN chain that reuses previous_end after the first clip."
    )


def _render_location_clause(row: dict) -> str:
    location = " ".join(str(row.get("location_description", "")).strip().rstrip(".").split())
    if location:
        return f"In {location}"
    anchor = " ".join(str(row.get("environment_anchor", "")).strip().rstrip(".").split())
    return f"In {anchor}" if anchor else ""


def _verbalize_render_prompts(config: dict, shot_packages: list[dict], wan_chain: list[dict]) -> None:
    ref_rows = []
    for shot in shot_packages:
        clauses = dict(shot.get("ref_prompt_clauses", {}))
        ref_rows.append(
            {
                "shot_id": str(shot.get("shot_id", "")).strip(),
                "subject_intro": str(clauses.get("subject_intro", "")).strip(),
                "location": str(clauses.get("location", "")).strip(),
                "start_state": str(clauses.get("start_state", "")).strip(),
                "end_state": str(clauses.get("end_state", "")).strip(),
                "lighting": str(clauses.get("lighting", "")).strip(),
            }
        )
    ref_prompts = verbalize_ref_prompt_pairs(config, ref_rows)
    for shot in shot_packages:
        prompts = ref_prompts.get(str(shot.get("shot_id", "")).strip(), {})
        shot["ref_start_prompt_text"] = str(prompts.get("start_prompt_text", "")).strip()
        shot["ref_end_prompt_text"] = str(prompts.get("end_prompt_text", "")).strip()

    wan_rows = []
    for row in wan_chain:
        clauses = dict(row.get("wan_prompt_clauses", {}))
        wan_rows.append(
            {
                "shot_id": str(row.get("shot_id", "")).strip(),
                "subject_intro": str(clauses.get("subject_intro", "")).strip(),
                "location": str(clauses.get("location", "")).strip(),
                "bridge_action": str(clauses.get("bridge_action", "")).strip(),
                "lighting": str(clauses.get("lighting", "")).strip(),
            }
        )
    wan_prompts = verbalize_wan_prompts(config, wan_rows)
    for row in wan_chain:
        row["wan_positive_prompt_text"] = str(wan_prompts.get(str(row.get("shot_id", "")).strip(), "")).strip()
