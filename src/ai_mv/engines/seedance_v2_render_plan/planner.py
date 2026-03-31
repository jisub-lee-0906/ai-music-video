from __future__ import annotations

from ai_mv.core.contracts.seedance_v2_normalize import normalize_render_plan_v2
from ai_mv.core.director_brief import build_director_brief_intent


def build_render_plan_v2(config: dict, payload: dict) -> dict:
    brief = build_director_brief_intent(config)
    director_plan = payload["director_plan_v2"]
    shot_packages: list[dict] = []
    wan_chain: list[dict] = []
    previous_chain_key = ""
    for index, shot in enumerate(director_plan.get("shot_packages", []), start=1):
        shot_row = dict(shot)
        shot_row["render_strategy"] = "ref_pair"
        shot_packages.append(shot_row)
        chain_key = f"{shot_row['shot_id']}:{index}"
        wan_chain.append(
            {
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
        )
        previous_chain_key = chain_key
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
        "REF start/end image pairs per shot, and a WAN chain that reuses previous_end after the first clip."
    )
