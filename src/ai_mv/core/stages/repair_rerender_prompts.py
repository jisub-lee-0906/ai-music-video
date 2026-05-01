from __future__ import annotations

from copy import deepcopy

from ai_mv.core.contracts.stage_io import StageInput, StageOutput


def run_repair_rerender_prompts(stage_input: StageInput) -> StageOutput:
    stage_inputs = stage_input.payload.get("rerender_stage_inputs") if isinstance(stage_input.payload.get("rerender_stage_inputs"), dict) else {}
    review_report = stage_input.payload.get("review_report") if isinstance(stage_input.payload.get("review_report"), dict) else {}
    execution_payloads = review_report.get("rerender_execution_payloads", []) if isinstance(review_report.get("rerender_execution_payloads"), list) else []
    repaired_inputs = deepcopy(stage_inputs)

    for item in execution_payloads:
        if not isinstance(item, dict):
            continue
        shot_id = str(item.get("shot_id", "")).strip()
        if not shot_id:
            continue
        prompt_focus = [str(name).strip() for name in item.get("prompt_contract_focus", []) if str(name).strip()]
        fix_strategy = str(item.get("fix_strategy", "")).strip()
        if not prompt_focus or not fix_strategy:
            continue
        for stage_name, stage_payload in repaired_inputs.items():
            if not isinstance(stage_payload, dict):
                continue
            render_plan = stage_payload.get("render_plan")
            if not isinstance(render_plan, list):
                continue
            for row in render_plan:
                if not isinstance(row, dict) or str(row.get("shot_id", "")).strip() != shot_id:
                    continue
                for field_name in prompt_focus:
                    current_value = str(row.get(field_name, "")).strip()
                    if current_value:
                        row[field_name] = _repair_prompt_text(
                            current_value=current_value,
                            field_name=field_name,
                            fix_strategy=fix_strategy,
                            render_row=row,
                        )

    return StageOutput("repair_rerender_prompts", "done", {"rerender_stage_inputs": repaired_inputs}, [])



def _repair_prompt_text(*, field_name: str, fix_strategy: str, current_value: str, render_row: dict | None = None) -> str:
    if fix_strategy == "enforce_single_frame_keyframe_composition" and field_name == "still_prompt_text":
        return _join_prompt_tokens(
            [
                current_value,
                "single cinematic keyframe",
                "one uninterrupted composition",
                "no panel layout",
                "no collage",
                "no split screen",
            ]
        )
    if fix_strategy == "tighten_subject_and_world_anchors" and field_name == "still_prompt_text":
        return _join_prompt_tokens(
            [
                current_value,
                "same protagonist",
                "same environment",
                "locked world details",
                "no unrelated scene intrusion",
            ]
        )
    if fix_strategy == "tighten_subject_identity_anchors" and field_name == "still_prompt_text":
        return _repair_subject_identity_prompt(field_name=field_name, current_value=current_value, render_row=render_row)
    if fix_strategy == "tighten_identity_continuity_anchors":
        return _repair_identity_continuity_prompt(field_name=field_name, current_value=current_value, render_row=render_row)
    if fix_strategy == "strengthen_character_payoff_and_subject_scale":
        return _repair_character_payoff_prompt(field_name=field_name, current_value=current_value)
    if fix_strategy == "strengthen_story_payoff_and_chorus_release":
        return _repair_story_payoff_prompt(field_name=field_name, current_value=current_value, render_row=render_row)
    if fix_strategy == "shorter_motion_and_clean_terminal_frames":
        return _repair_terminal_frame_prompt(field_name=field_name, current_value=current_value)
    return current_value



def _repair_terminal_frame_prompt(*, field_name: str, current_value: str) -> str:
    tokens = [part.strip() for part in str(current_value).split(",") if part.strip()]
    seed_prefix = tokens[0] if tokens else str(current_value).strip()
    if field_name == "clip_prompt_seed":
        return _join_prompt_tokens([seed_prefix, "clean terminal frame", "restrained motion range"])
    if field_name == "clip_positive_prompt":
        return _join_prompt_tokens(
            [
                seed_prefix,
                "clean terminal frame",
                "restrained motion range",
                "shorter motion beat",
                "clean exit frame",
                "no abrupt pose change",
            ]
        )
    return current_value



def _repair_subject_identity_prompt(*, field_name: str, current_value: str, render_row: dict | None = None) -> str:
    if field_name != "still_prompt_text":
        return current_value
    tokens = [
        current_value,
        "same protagonist",
        "locked identity details",
        "no identity drift",
        "no duplicate subject",
    ]
    if _is_reference_followup(render_row):
        tokens.extend(_reference_followup_tokens(render_row))
    return _join_prompt_tokens(tokens)



def _repair_identity_continuity_prompt(*, field_name: str, current_value: str, render_row: dict | None = None) -> str:
    tokens = [part.strip() for part in str(current_value).split(",") if part.strip()]
    seed_prefix = tokens[0] if tokens else str(current_value).strip()
    if field_name == "still_prompt_text":
        base_tokens = [
            current_value,
            "same protagonist",
            "continuity-locked identity details",
            "match adjacent shots",
            "no identity drift",
            "preserve neighboring-shot continuity",
        ]
        if _is_reference_followup(render_row):
            base_tokens.extend(_reference_followup_tokens(render_row))
        return _join_prompt_tokens(base_tokens)
    if field_name == "clip_prompt_seed":
        return _join_prompt_tokens([seed_prefix, "same protagonist", "preserve neighboring-shot continuity"])
    if field_name == "clip_positive_prompt":
        return _join_prompt_tokens(
            [
                seed_prefix,
                "same protagonist",
                "preserve neighboring-shot continuity",
                "match adjacent shots",
                "no identity drift",
                "no abrupt pose change",
            ]
        )
    return current_value



def _repair_character_payoff_prompt(*, field_name: str, current_value: str) -> str:
    tokens = [part.strip() for part in str(current_value).split(",") if part.strip()]
    seed_prefix = tokens[0] if tokens else str(current_value).strip()
    if field_name == "still_prompt_text":
        return _join_prompt_tokens(
            [
                current_value,
                "same protagonist",
                "stronger character payoff",
                "subject-led composition",
                "larger foreground subject",
                "no background-dominant framing",
            ]
        )
    if field_name == "clip_prompt_seed":
        return _join_prompt_tokens([seed_prefix, "same protagonist", "stronger character payoff", "larger foreground subject"])
    if field_name == "clip_positive_prompt":
        return _join_prompt_tokens(
            [
                current_value,
                "same protagonist",
                "stronger character payoff",
                "subject-led composition",
                "larger foreground subject",
                "no background-dominant framing",
            ]
        )
    return current_value



def _repair_story_payoff_prompt(*, field_name: str, current_value: str, render_row: dict | None = None) -> str:
    tokens = [part.strip() for part in str(current_value).split(",") if part.strip()]
    seed_prefix = tokens[0] if tokens else str(current_value).strip()
    payoff_requirement = _payoff_requirement(render_row)
    story_function = str((render_row or {}).get("story_function", "")).strip().lower() if isinstance(render_row, dict) else ""
    release_token = "chorus release lift" if story_function == "release" else "story payoff lift"
    shared_tokens = [
        "same protagonist",
        release_token,
        "visible emotional turn",
        "clear story beat fulfillment",
        "not another safe mood-only shot",
    ]
    if payoff_requirement:
        shared_tokens.insert(3, payoff_requirement)
    if field_name == "still_prompt_text":
        return _join_prompt_tokens([current_value, *shared_tokens, "subject-led composition", "larger foreground subject"])
    if field_name == "clip_prompt_seed":
        return _join_prompt_tokens([seed_prefix, "same protagonist", payoff_requirement, "visible emotional turn", release_token])
    if field_name == "clip_positive_prompt":
        return _join_prompt_tokens([current_value, *shared_tokens, "intentional change from previous shot"])
    return current_value



def _payoff_requirement(render_row: dict | None) -> str:
    if not isinstance(render_row, dict):
        return ""
    return str(render_row.get("payoff_requirement", "") or "").strip()



def _reference_followup_tokens(render_row: dict | None) -> list[str]:
    if not isinstance(render_row, dict):
        return []
    reference_mode = str(render_row.get("reference_mode", "")).strip().lower()
    variation_scope = str(render_row.get("edit_variation_scope", "")).strip().lower()
    if reference_mode == "use_performance_anchor_still" or variation_scope == "performance_pose_upgrade":
        return [
            "preserve face shape from the anchor still",
            "avoid near-duplicate framing",
        ]
    if reference_mode == "use_anchor_still" and variation_scope == "framing_only":
        return ["change camera distance or viewing angle from the anchor frame"]
    if reference_mode == "use_anchor_still" and variation_scope == "bridge_reframe":
        return ["shift into a bridge-specific camera move from the anchor frame"]
    return []



def _is_reference_followup(render_row: dict | None) -> bool:
    if not isinstance(render_row, dict):
        return False
    return str(render_row.get("reference_mode", "")).strip().lower() in {"use_anchor_still", "use_performance_anchor_still"}



def _join_prompt_tokens(parts: list[str]) -> str:
    tokens: list[str] = []
    for part in parts:
        for token in [item.strip() for item in str(part or "").split(",") if item.strip()]:
            if token not in tokens:
                tokens.append(token)
    return ", ".join(tokens)
