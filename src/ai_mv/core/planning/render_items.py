from __future__ import annotations

from ai_mv.core.planning.continuity_contracts import (
    build_continuity_contract as continuity_contracts_build_continuity_contract,
    build_shot_relation_contract as continuity_contracts_build_shot_relation_contract,
)
from ai_mv.core.planning.edit_intents import build_edit_intent as edit_intents_build_edit_intent
from ai_mv.core.planning.prompt_assembly import (
    build_prompt_bundle as prompt_assembly_build_prompt_bundle,
    build_prompt_draft as prompt_assembly_build_prompt_draft,
    build_prompt_seed as prompt_assembly_build_prompt_seed,
    polish_prompt as prompt_assembly_polish_prompt,
)
from ai_mv.core.planning.production_policy import build_production_policy as production_policy_build_production_policy
from ai_mv.core.planning.pose_action_need import build_pose_action_need as pose_action_need_build_pose_action_need
from ai_mv.core.planning.pose_anchor_selection import build_pose_anchor_selection as pose_anchor_selection_build_pose_anchor_selection
from ai_mv.core.planning.prompt_contracts import (
    build_clip_positive_prompt as prompt_contracts_build_clip_positive_prompt,
    build_clip_prompt_seed as prompt_contracts_build_clip_prompt_seed,
    build_still_prompt_text as prompt_contracts_build_still_prompt_text,
)
from ai_mv.core.planning.render_item_inputs import resolve_render_item_inputs as render_item_inputs_resolve_render_item_inputs
from ai_mv.core.planning.render_item_payload import build_render_item_payload as render_item_payload_build_render_item_payload
from ai_mv.core.planning.render_sizing import calculate_render_count as render_sizing_calculate_render_count
from ai_mv.core.planning.workflow_prompt_adapters import (
    build_workflow_prompt_payloads,
    parse_user_intent_contract,
)
from ai_mv.core.planning.reference_policy import (
    build_reference_policy as reference_policy_build_reference_policy,
    build_variation_delta_contract as reference_policy_build_variation_delta_contract,
)
from ai_mv.core.planning.render_priority import build_render_planning as render_priority_build_render_planning
from ai_mv.core.planning.variation_profile import (
    build_render_seed_for_shot as variation_profile_build_render_seed_for_shot,
    build_variation_profile as variation_profile_build_variation_profile,
    build_variation_seed_for_shot as variation_profile_build_variation_seed_for_shot,
)



def build_render_item(config: dict, concept_text: str, style_name_or_bible, style_bible_or_shot, shot: dict | None = None) -> dict:
    render_item_inputs = render_item_inputs_resolve_render_item_inputs(
        config,
        concept_text,
        style_name_or_bible,
        style_bible_or_shot,
        shot,
    )
    style_name = render_item_inputs["style_name"]
    style_bible = render_item_inputs["style_bible"]
    shot = render_item_inputs["shot"]
    prompt_bundle = prompt_assembly_build_prompt_bundle(style_name, concept_text, style_bible, shot)
    prompt_seed = prompt_bundle["prompt_seed"]
    prompt_draft = prompt_bundle["prompt_draft"]
    prompt_polish = prompt_bundle["prompt_polish"]
    render_mode = str(shot["render_mode"]).strip()
    continuity_contract = build_continuity_contract(shot)
    shot_relation_contract = build_shot_relation_contract(shot)
    variation_seed = _variation_seed_for_shot(shot)
    variation_profile = build_variation_profile(variation_seed, shot)
    if isinstance(shot.get("story_contract"), dict):
        variation_profile = {**variation_profile, "story_contract": dict(shot["story_contract"])}
    if isinstance(shot.get("narrative_progression"), dict):
        variation_profile = {**variation_profile, "narrative_progression": dict(shot["narrative_progression"])}
    reference_policy = build_reference_policy(shot)
    clip_prompt_seed = build_clip_prompt_seed(render_mode, shot, prompt_seed, variation_profile, shot_relation_contract)
    clip_positive_prompt = build_clip_positive_prompt(
        render_mode,
        shot,
        clip_prompt_seed,
        variation_profile,
        shot_relation_contract,
        reference_policy,
    )
    edit_intent = build_edit_intent(shot, variation_profile)
    render_count = calculate_render_count(float(shot.get("duration_sec", 0.0) or 0.0))
    render_planning = build_render_planning(style_name, shot)
    variation_delta = build_variation_delta_contract(shot, reference_policy)
    production_policy = production_policy_build_production_policy(shot, style_name=style_name)
    pose_anchor_selection = pose_anchor_selection_build_pose_anchor_selection({**shot, "concept_text": concept_text})
    pose_action_need = pose_action_need_build_pose_action_need({**shot, "concept_text": concept_text}, concept_text)
    still_prompt_text = build_still_prompt_text(
        prompt_seed,
        prompt_draft,
        prompt_polish,
        variation_profile,
        shot_relation_contract,
        reference_policy,
        variation_delta,
    )
    workflow_prompts = build_workflow_prompt_payloads(
        parse_user_intent_contract(concept_text),
        {
            "shot_id": shot.get("shot_id", ""),
            "prompt_seed": prompt_seed,
            "prompt_draft": prompt_draft,
            "prompt_polish": prompt_polish,
            "still_prompt_text": still_prompt_text,
            "clip_prompt_seed": clip_prompt_seed,
            "clip_positive_prompt": clip_positive_prompt,
            "story_contract": dict(shot.get("story_contract", {})) if isinstance(shot.get("story_contract"), dict) else {},
            "selected_pose_anchor_id": str(pose_anchor_selection.get("selected_pose_anchor_id", "")).strip() if isinstance(pose_anchor_selection, dict) else "",
            "candidate_role": str((production_policy or {}).get("candidate_role", "")).strip(),
            "recommended_duration_sec": (production_policy or {}).get("recommended_duration_sec", {}),
        },
        base_ltx_negative=str(config.get("render", {}).get("ltx_negative", "")).strip() if isinstance(config, dict) else "",
    )
    out = render_item_payload_build_render_item_payload(
        shot=shot,
        render_mode=render_mode,
        render_count=render_count,
        render_planning=render_planning,
        render_seed=_render_seed_for_shot(shot),
        variation_seed=variation_seed,
        variation_profile=variation_profile,
        continuity_contract=continuity_contract,
        shot_relation_contract=shot_relation_contract,
        prompt_bundle=prompt_bundle,
        still_prompt_text=still_prompt_text,
        clip_prompt_seed=clip_prompt_seed,
        clip_positive_prompt=clip_positive_prompt,
        edit_intent=edit_intent,
        reference_policy=reference_policy,
        variation_delta=variation_delta,
        production_policy=production_policy,
        pose_anchor_selection=pose_anchor_selection,
        pose_action_need=pose_action_need,
        workflow_prompts=workflow_prompts,
    )
    return out



def build_prompt_seed(style_name: str, concept_text: str, style_bible: dict, shot: dict) -> str:
    return prompt_assembly_build_prompt_seed(style_name, concept_text, style_bible, shot)



def build_prompt_draft(style_name: str, shot: dict) -> str:
    return prompt_assembly_build_prompt_draft(style_name, shot)



def build_still_prompt_text(
    prompt_seed: str,
    prompt_draft: str,
    prompt_polish: str,
    variation_profile: dict | None = None,
    shot_relation_contract: dict | None = None,
    reference_policy: dict | None = None,
    variation_delta_contract: dict | None = None,
) -> str:
    return prompt_contracts_build_still_prompt_text(
        prompt_seed,
        prompt_draft,
        prompt_polish,
        variation_profile,
        shot_relation_contract,
        reference_policy,
        variation_delta_contract,
    )



def build_clip_prompt_seed(
    render_mode: str,
    shot: dict,
    prompt_seed: str,
    variation_profile: dict | None = None,
    shot_relation_contract: dict | None = None,
) -> str:
    return prompt_contracts_build_clip_prompt_seed(
        render_mode,
        shot,
        prompt_seed,
        variation_profile,
        shot_relation_contract,
    )



def build_clip_positive_prompt(
    render_mode: str,
    shot: dict,
    clip_prompt_seed: str,
    variation_profile: dict | None = None,
    shot_relation_contract: dict | None = None,
    reference_policy: dict | None = None,
) -> str:
    return prompt_contracts_build_clip_positive_prompt(
        render_mode,
        shot,
        clip_prompt_seed,
        variation_profile,
        shot_relation_contract,
        reference_policy,
    )



def build_continuity_contract(shot: dict) -> dict:
    return continuity_contracts_build_continuity_contract(shot)



def build_shot_relation_contract(shot: dict) -> dict:
    return continuity_contracts_build_shot_relation_contract(shot)



def build_edit_intent(shot: dict, variation_profile: dict | None = None) -> dict:
    return edit_intents_build_edit_intent(shot, variation_profile)



def build_reference_policy(shot: dict) -> dict:
    return reference_policy_build_reference_policy(shot)



def build_variation_delta_contract(shot: dict, reference_policy: dict | None = None) -> dict:
    return reference_policy_build_variation_delta_contract(shot, reference_policy)



def calculate_render_count(duration_sec: float) -> int:
    return render_sizing_calculate_render_count(duration_sec)



def _render_seed_for_shot(shot: dict) -> int:
    return variation_profile_build_render_seed_for_shot(shot)



def _variation_seed_for_shot(shot: dict) -> int:
    return variation_profile_build_variation_seed_for_shot(shot)



def build_variation_profile(variation_seed: int, shot: dict) -> dict:
    return variation_profile_build_variation_profile(variation_seed, shot)



def build_render_planning(style_name: str, shot: dict) -> dict:
    return render_priority_build_render_planning(style_name, shot)



def polish_prompt(prompt_seed: str, prompt_draft: str) -> str:
    return prompt_assembly_polish_prompt(prompt_seed, prompt_draft)
