from __future__ import annotations

from ai_mv.core.contracts.stage_io import StageInput, StageOutput
from ai_mv.core.output_paths import still_prefix
from ai_mv.core.stages.still_qa_gate import evaluate_still_for_ia2v
from ai_mv.engines.flux2_image.runner import run_flux2_still

_RAW_STILL_VISUAL_MODES = {"window_reflection"}
_RAW_STILL_PROMPT_MARKERS = (
    "clear face visibility",
    "visible upper-body framing",
    "readable medium shot",
    "motion-safe continuity",
    "preserved neighboring-shot continuity",
)
_WIDE_STILL_PROMPT_MARKERS = (
    "full-body readability",
    "medium-wide frame",
)


def run_render_stills(stage_input: StageInput) -> StageOutput:
    shot_plan = [row for row in stage_input.payload.get("shot_plan", []) if isinstance(row, dict)]
    material_plan = [row for row in stage_input.payload.get("material_plan", []) if isinstance(row, dict)]
    render_plan = [row for row in stage_input.payload.get("render_plan", []) if isinstance(row, dict)]
    prior_stills = [row for row in stage_input.payload.get("still_results", []) if isinstance(row, dict)]
    render_map = {str(row.get("shot_id", "")).strip(): row for row in render_plan}
    prior_still_map = {str(row.get("shot_id", "")).strip(): row for row in prior_stills}
    generated_still_map: dict[str, dict] = {}
    material_map = {str(row.get("material_id", "")).strip(): row for row in material_plan if str(row.get("material_id", "")).strip()}
    anchor_results = _render_anchor_package(stage_input)
    anchor_package = stage_input.payload.get("anchor_package")
    anchor_still_map = (
        {str(row.get("anchor_id", "")).strip(): row for row in anchor_results if str(row.get("anchor_id", "")).strip()}
        if isinstance(anchor_package, dict)
        else None
    )
    anchor_identity_prompt = _anchor_identity_prompt(anchor_still_map)
    still_results = []
    for shot in shot_plan:
        shot_id = str(shot.get("shot_id", "")).strip()
        render_item = render_map.get(shot_id, {})
        material_id = str(render_item.get("material_id", "") or shot.get("material_id", "")).strip()
        material_row = material_map.get(material_id, {})
        base_prompt_text = _still_prompt_text(render_item)
        base_prompt_text = _apply_anchor_identity_prompt(base_prompt_text, render_item, anchor_identity_prompt)
        prompt_text = _apply_still_constraint_policy(base_prompt_text, shot=shot, render_item=render_item)
        previous_image = str(prior_still_map.get(shot_id, {}).get("image", "")).strip()
        anchor_reference_image = _anchor_reference_image(render_item, generated_still_map, prior_still_map, anchor_still_map)
        render_count = _render_count(render_item)
        candidate_score_rows = render_item.get("still_candidate_scores") if isinstance(render_item.get("still_candidate_scores"), list) else []
        candidate_results: list[dict] = []
        for retry in range(render_count):
            item = {
                "shot_id": shot_id,
                "positive_prompt": prompt_text,
                "filename_prefix": still_prefix(stage_input.run_id, shot_id),
                "flux2_size": str(stage_input.config.get("render", {}).get("flux2_size", "")).strip(),
                "retry": retry,
            }
            seed = render_item.get("seed")
            if isinstance(seed, int) and seed >= 0:
                item["seed"] = seed + retry
            if previous_image and str(render_item.get("reference_mode", "")).strip() == "reuse_prior_still":
                item["reference_image"] = previous_image
            elif anchor_reference_image:
                item["reference_image"] = anchor_reference_image
            image_path = run_flux2_still(
                stage_input.config,
                item,
            )
            score_row = candidate_score_rows[retry] if retry < len(candidate_score_rows) and isinstance(candidate_score_rows[retry], dict) else {}
            candidate_results.append(
                {
                    "image": image_path,
                    "retry": retry,
                    "seed": item.get("seed"),
                    "continuity_score": _safe_score(score_row.get("continuity_score")),
                    "identity_score": _safe_score(score_row.get("identity_score")),
                    "world_score": _safe_score(score_row.get("world_score")),
                }
            )
        selected_candidate, selected_candidate_index, selection_policy = _select_still_candidate(candidate_results, render_item)
        candidate_images = [str(row.get("image", "")).strip() for row in candidate_results]
        image_path = str(selected_candidate.get("image", "")).strip()
        still_row = {
            "shot_id": shot_id,
            "material_id": material_id,
            "section_id": str(render_item.get("section_id", "") or shot.get("section_id", "") or material_row.get("section_id", "")).strip(),
            "image": image_path,
            "candidate_images": candidate_images,
            "candidate_count": len(candidate_images),
            "candidate_results": candidate_results,
            "selected_candidate": dict(selected_candidate),
            "selected_candidate_index": selected_candidate_index,
            "selection_policy": selection_policy,
            "prompt_seed": str(render_item.get("prompt_seed", "")).strip(),
            "prompt_text": prompt_text,
            "reference_mode": str(render_item.get("reference_mode", "")).strip(),
            "reference_source_shot_id": str(render_item.get("reference_source_shot_id", "")).strip(),
            "reference_image": anchor_reference_image or (previous_image if previous_image and str(render_item.get("reference_mode", "")).strip() == "reuse_prior_still" else ""),
            "reference_anchor_id": _reference_anchor_id(render_item, anchor_reference_image, anchor_still_map),
            "workflow_target": _still_workflow_target(render_item, anchor_reference_image),
            "identity_lock_strength": str(render_item.get("identity_lock_strength", "")).strip(),
            "selected_pose_anchor_id": str(render_item.get("selected_pose_anchor_id", "")).strip(),
            "pose_anchor_selection": dict(render_item.get("pose_anchor_selection", {})) if isinstance(render_item.get("pose_anchor_selection"), dict) else {},
            "status": "done",
        }
        still_row["still_qa"] = evaluate_still_for_ia2v(still_row=still_row, shot=shot, render_item=render_item)
        still_results.append(still_row)
        generated_still_map[shot_id] = still_row
    reference_coverage = _reference_anchor_coverage_summary(still_results)
    return StageOutput(
        "render_stills",
        "done",
        {
            "still_results": still_results,
            "anchor_results": anchor_results,
            "workflow_inputs": {
                **dict(stage_input.payload.get("workflow_inputs", {})),
                "stills": {
                    "count": len(still_results),
                    "anchor_count": len(anchor_results),
                    "pose_anchor_count": _pose_anchor_result_count(anchor_results),
                    **reference_coverage,
                },
            },
        },
        [],
    )


def _render_anchor_package(stage_input: StageInput) -> list[dict]:
    anchor_package = stage_input.payload.get("anchor_package")
    if not isinstance(anchor_package, dict):
        return []
    anchors = [
        row
        for row in anchor_package.get("anchors", [])
        if isinstance(row, dict) and not _is_world_reference_anchor(row)
    ]
    pose_anchors = [
        row
        for row in anchor_package.get("pose_anchor_bank", [])
        if isinstance(row, dict) and not _is_world_reference_anchor(row)
    ]
    anchors = [*anchors, *pose_anchors]
    anchor_results: list[dict] = []
    anchor_image_by_id: dict[str, str] = {}
    for anchor in anchors:
        anchor_id = str(anchor.get("anchor_id", "")).strip()
        prompt_text = str(anchor.get("prompt_text", "")).strip()
        if not anchor_id or not prompt_text:
            continue
        item = {
            "shot_id": anchor_id,
            "positive_prompt": prompt_text,
            "filename_prefix": still_prefix(stage_input.run_id, anchor_id),
            "flux2_size": str(stage_input.config.get("render", {}).get("flux2_size", "")).strip(),
            "retry": 0,
            "workflow_target": str(anchor.get("workflow_target", "")).strip(),
        }
        reference_image = _anchor_package_reference_image(anchor, anchor_image_by_id)
        if _anchor_requires_reference_image(anchor) and not reference_image:
            continue
        if reference_image:
            item["reference_image"] = reference_image
        image_path = run_flux2_still(stage_input.config, item)
        anchor_image_by_id[anchor_id] = image_path
        result_row = {
            "anchor_id": anchor_id,
            "anchor_type": str(anchor.get("anchor_type", "")).strip(),
            "material_class": str(anchor.get("material_class", "")).strip(),
            "workflow_target": str(anchor.get("workflow_target", "")).strip(),
            "image": image_path,
            "prompt_text": prompt_text,
            "status": "done",
        }
        for metadata_key in ("pose_family", "framing", "camera_angle"):
            metadata_value = str(anchor.get(metadata_key, "")).strip()
            if metadata_value:
                result_row[metadata_key] = metadata_value
        anchor_results.append(result_row)
    return anchor_results


def _is_world_reference_anchor(anchor: dict) -> bool:
    anchor_id = str(anchor.get("anchor_id", "")).strip().lower()
    anchor_type = str(anchor.get("anchor_type", "")).strip().lower()
    anchor_role = str(anchor.get("anchor_role", "")).strip().lower()
    material_class = str(anchor.get("material_class", "")).strip().lower()
    prompt_style = str(anchor.get("prompt_style", "")).strip().lower()
    return any(
        "world" in value
        for value in (anchor_id, anchor_type, anchor_role, material_class, prompt_style)
        if value
    )


def _pose_anchor_result_count(anchor_results: list[dict]) -> int:
    return sum(
        1
        for row in anchor_results
        if isinstance(row, dict)
        and (
            str(row.get("anchor_type", "")).strip() == "pose_variant"
            or str(row.get("material_class", "")).strip() == "pose_reference_anchor"
            or str(row.get("pose_family", "")).strip()
        )
    )


def _reference_anchor_coverage_summary(still_results: list[dict]) -> dict:
    reference_rows = [
        row
        for row in still_results
        if isinstance(row, dict) and str(row.get("workflow_target", "")).strip() == "image_flux2_reference_image"
    ]
    referenced_rows = [row for row in reference_rows if str(row.get("reference_anchor_id", "")).strip()]
    missing_shot_ids = [str(row.get("shot_id", "")).strip() for row in reference_rows if not str(row.get("reference_anchor_id", "")).strip()]
    total = len(reference_rows)
    return {
        "reference_keyframe_count": total,
        "referenced_keyframe_count": len(referenced_rows),
        "reference_anchor_coverage_ratio": round(len(referenced_rows) / total, 3) if total else 1.0,
        "missing_reference_anchor_shot_ids": [shot_id for shot_id in missing_shot_ids if shot_id],
    }



def _anchor_package_reference_image(anchor: dict, anchor_image_by_id: dict[str, str]) -> str:
    workflow_target = str(anchor.get("workflow_target", "")).strip().lower()
    if workflow_target not in {"image_flux2_reference_image", "image_flux2", "flux2_reference_image"}:
        return ""
    reference_anchor_ids = [str(value).strip() for value in anchor.get("reference_anchor_ids", []) if str(value).strip()] if isinstance(anchor.get("reference_anchor_ids"), list) else []
    for anchor_id in reference_anchor_ids:
        image = str(anchor_image_by_id.get(anchor_id, "")).strip()
        if image:
            return image
    if _is_pose_reference_anchor(anchor):
        return ""
    primary_identity = str(anchor_image_by_id.get("ANCHOR_CHARACTER_UPPER_BODY", "")).strip()
    if primary_identity:
        return primary_identity
    full_body_identity = str(anchor_image_by_id.get("ANCHOR_CHARACTER_FULL_BODY", "")).strip()
    if full_body_identity:
        return full_body_identity
    return ""



def _anchor_requires_reference_image(anchor: dict) -> bool:
    workflow_target = str(anchor.get("workflow_target", "")).strip().lower()
    if workflow_target not in {"image_flux2_reference_image", "image_flux2", "flux2_reference_image"}:
        return False
    return bool(str(anchor.get("anchor_id", "")).strip() or str(anchor.get("anchor_type", "")).strip())



def _is_pose_reference_anchor(anchor: dict) -> bool:
    return (
        str(anchor.get("anchor_type", "")).strip() == "pose_variant"
        or str(anchor.get("anchor_role", "")).strip() == "pose_variant"
        or str(anchor.get("material_class", "")).strip() == "pose_reference_anchor"
        or bool(str(anchor.get("pose_family", "")).strip())
    )



def _still_prompt_text(render_item: dict) -> str:
    for key in ("still_prompt_text", "prompt_polish", "prompt_draft", "prompt_seed"):
        value = str(render_item.get(key, "")).strip()
        if value:
            return value
    shot_id = str(render_item.get("shot_id", "")).strip() if isinstance(render_item, dict) else ""
    suffix = f" for shot {shot_id}" if shot_id else ""
    raise RuntimeError(f"missing still prompt contract{suffix}")


def _apply_anchor_identity_prompt(prompt_text: str, render_item: dict, anchor_identity_prompt: str) -> str:
    if not anchor_identity_prompt:
        return str(prompt_text).strip()
    if not _should_apply_anchor_identity_prompt(render_item):
        return str(prompt_text).strip()
    base = _remove_anchor_identity_contradictions(str(prompt_text).strip(), anchor_identity_prompt)
    existing = base.lower()
    tokens: list[str] = [base] if base else []
    for token in [part.strip() for part in anchor_identity_prompt.split(",") if part.strip()]:
        if token.lower() not in existing and token not in tokens:
            tokens.append(token)
    return ", ".join(token for token in tokens if token)


def _remove_anchor_identity_contradictions(prompt_text: str, anchor_identity_prompt: str) -> str:
    anchor_text = anchor_identity_prompt.lower()
    if not ("bright red" in anchor_text and "raincoat" in anchor_text):
        return str(prompt_text).strip()
    blocked_exact = {
        "stable dark outerwear silhouette",
        "stable outfit silhouette",
        "stable bright stage outfit silhouette",
    }
    replacement_tokens = [
        "preserve visible bright red raincoat as the outerwear continuity marker",
        "bright red raincoat remains visible in this shot",
    ]
    tokens: list[str] = []
    for token in [part.strip() for part in str(prompt_text).split(",") if part.strip()]:
        if token.lower() in blocked_exact:
            continue
        if token not in tokens:
            tokens.append(token)
    for token in replacement_tokens:
        if token not in tokens:
            tokens.append(token)
    return ", ".join(tokens)


def _should_apply_anchor_identity_prompt(render_item: dict) -> bool:
    if not isinstance(render_item, dict):
        return False
    reference_mode = str(render_item.get("reference_mode", "")).strip().lower()
    if reference_mode in {"anchor_source", "performance_anchor_source", "use_anchor_still", "use_performance_anchor_still"}:
        return True
    continuity_contract = render_item.get("continuity_contract") if isinstance(render_item.get("continuity_contract"), dict) else {}
    return bool(str(continuity_contract.get("protagonist_anchor", "")).strip())


def _anchor_identity_prompt(anchor_still_map: dict[str, dict] | None) -> str:
    if not isinstance(anchor_still_map, dict):
        return ""
    anchor_row = _preferred_character_anchor_row(anchor_still_map)
    prompt_text = str(anchor_row.get("prompt_text", "")).strip() if isinstance(anchor_row, dict) else ""
    if not prompt_text:
        return ""
    blocked_markers = (
        "white background",
        "pure white",
        "seamless background",
        "identity reference card",
        "reference card",
        "full-body",
        "upper-body",
        "no street",
        "single clean",
        "stable dark outerwear silhouette",
    )
    identity_tokens: list[str] = [
        "preserve the exact same white-background character model identity",
        "do not change gender, face, hair, upper-body wardrobe, wardrobe color palette, or main outfit silhouette",
        "no unrelated male singer",
    ]
    lower_prompt = prompt_text.lower()
    explicit_markers: list[str] = []
    if "woman" in lower_prompt or " she " in f" {lower_prompt} ":
        explicit_markers.append("same young woman")
    if "short black bob" in lower_prompt and "bang" in lower_prompt:
        explicit_markers.append("short black bob with bangs")
    elif "short black bob" in lower_prompt:
        explicit_markers.append("short black bob")
    if "bright red" in lower_prompt and "raincoat" in lower_prompt:
        explicit_markers.append("bright red raincoat")
    elif "red" in lower_prompt and "raincoat" in lower_prompt:
        explicit_markers.append("red raincoat")
    for marker in explicit_markers:
        if marker not in identity_tokens:
            identity_tokens.append(marker)
    for token in [part.strip() for part in prompt_text.split(",") if part.strip()]:
        lower = token.lower()
        if any(marker in lower for marker in blocked_markers):
            continue
        if token not in identity_tokens:
            identity_tokens.append(token)
    return ", ".join(identity_tokens)


def _preferred_character_anchor_row(anchor_still_map: dict[str, dict]) -> dict:
    preferred_ids = ("ANCHOR_CHARACTER_UPPER_BODY", "ANCHOR_CHARACTER_FULL_BODY")
    for anchor_id in preferred_ids:
        row = anchor_still_map.get(anchor_id)
        if isinstance(row, dict) and str(row.get("image", "")).strip():
            return row
    for row in anchor_still_map.values():
        if not isinstance(row, dict):
            continue
        material_class = str(row.get("material_class", "")).strip().lower()
        anchor_type = str(row.get("anchor_type", "")).strip().lower()
        if str(row.get("image", "")).strip() and ("character" in material_class or "character" in anchor_type):
            return row
    for row in anchor_still_map.values():
        if isinstance(row, dict) and str(row.get("image", "")).strip():
            return row
    return {}


def _single_keyframe_prompt_text(prompt_text: str) -> str:
    base = _sanitize_still_prompt_text(prompt_text)
    if _should_use_soft_single_scene_constraint(base):
        return _soft_single_scene_constraint_prompt_text(base)
    constraints = [
        "photoreal live-action still frame",
        "single cinematic keyframe",
        "single continuous scene",
        "one camera shot",
        "one uninterrupted composition",
        "full-bleed frame",
        "continuous background perspective",
        "subject integrated into the environment",
        "natural skin texture",
        "physically plausible neon reflections",
        "reflections within the same shot",
        "diegetic reflections only",
        "no inset portrait",
        "no secondary frame",
        "no juxtaposed scenes",
        "no panel layout",
        "no collage",
        "no split screen",
        "no text",
        "not anime-stylized",
        "not illustrated",
    ]
    tokens: list[str] = []
    for block in [base, *constraints]:
        for token in [part.strip() for part in str(block).split(",") if part.strip()]:
            if token not in tokens:
                tokens.append(token)
    return ", ".join(tokens)


def _soft_single_scene_constraint_prompt_text(prompt_text: str) -> str:
    base = str(prompt_text).strip()
    suffix = (
        "Render it as one clean photoreal live-action still frame in a single continuous scene, "
        "with the subject integrated into the environment and no inset frame, collage, or split screen."
    )
    return f"{base} {suffix}".strip()


def _should_use_soft_single_scene_constraint(prompt_text: str) -> bool:
    text = str(prompt_text or "").lower()
    return any(marker in text for marker in _WIDE_STILL_PROMPT_MARKERS)


def _apply_still_constraint_policy(prompt_text: str, *, shot: dict, render_item: dict) -> str:
    if _resolve_still_constraint_mode(prompt_text, shot=shot, render_item=render_item) == "raw":
        return str(prompt_text).strip()
    return _single_keyframe_prompt_text(prompt_text)


def _resolve_still_constraint_mode(prompt_text: str, *, shot: dict, render_item: dict) -> str:
    explicit_mode = str(render_item.get("still_constraint_mode", "")).strip().lower()
    if explicit_mode in {"raw", "constrained"}:
        return explicit_mode
    visual_mode = str(shot.get("visual_mode", "")).strip().lower()
    if visual_mode in _RAW_STILL_VISUAL_MODES:
        return "raw"
    text = str(prompt_text or "").lower()
    if any(marker in text for marker in _RAW_STILL_PROMPT_MARKERS):
        return "raw"
    return "constrained"



def _render_count(render_item: dict) -> int:
    try:
        render_count = int(render_item.get("render_count", 1))
    except Exception:
        return 1
    return max(1, render_count)



def _anchor_reference_image(
    render_item: dict,
    generated_still_map: dict[str, dict],
    prior_still_map: dict[str, dict],
    anchor_still_map: dict[str, dict] | None = None,
) -> str:
    if not isinstance(render_item, dict):
        return ""
    reference_mode = str(render_item.get("reference_mode", "")).strip().lower()
    selected_pose_anchor_id = str(render_item.get("selected_pose_anchor_id", "")).strip()
    if selected_pose_anchor_id:
        selected_pose_image = ""
        if isinstance(anchor_still_map, dict):
            selected_pose_image = str(anchor_still_map.get(selected_pose_anchor_id, {}).get("image", "")).strip()
        if selected_pose_image:
            return selected_pose_image
        shot_id = str(render_item.get("shot_id", "")).strip() or "unknown_shot"
        raise RuntimeError(
            f"missing selected pose anchor image for shot {shot_id}: {selected_pose_anchor_id}"
        )
    if reference_mode == "reuse_prior_still":
        return ""
    if reference_mode == "":
        continuity_contract = render_item.get("continuity_contract") if isinstance(render_item.get("continuity_contract"), dict) else {}
        has_continuity_anchor = bool(
            str(continuity_contract.get("protagonist_anchor", "")).strip()
            or str(continuity_contract.get("world_anchor", "")).strip()
        )
        if not has_continuity_anchor:
            return ""
        anchor_reference = _primary_identity_anchor_image(anchor_still_map)
        if anchor_reference:
            return anchor_reference
        if isinstance(anchor_still_map, dict):
            return ""
        for still_map in (generated_still_map, prior_still_map):
            for row in still_map.values():
                image = str(row.get("image", "")).strip() if isinstance(row, dict) else ""
                if image:
                    return image
        return ""
    if reference_mode == "performance_anchor_source":
        anchor_reference = _primary_identity_anchor_image(anchor_still_map)
        if anchor_reference:
            return anchor_reference
        return ""
    if reference_mode in {"use_anchor_still", "use_performance_anchor_still"}:
        anchor_reference = _primary_identity_anchor_image(anchor_still_map)
        if anchor_reference:
            return anchor_reference
        if isinstance(anchor_still_map, dict):
            return ""
        reference_shot_id = str(render_item.get("reference_source_shot_id", "")).strip()
        if reference_shot_id:
            for still_map in (generated_still_map, prior_still_map):
                image = str(still_map.get(reference_shot_id, {}).get("image", "")).strip()
                if image:
                    return image
        preferred_source_mode = "performance_anchor_source" if reference_mode == "use_performance_anchor_still" else "anchor_source"
        for still_map in (generated_still_map, prior_still_map):
            candidates = list(still_map.values()) if isinstance(still_map, dict) else []
            for row in reversed(candidates):
                if not isinstance(row, dict):
                    continue
                row_mode = str(row.get("reference_mode", "")).strip().lower()
                image = str(row.get("image", "")).strip()
                if image and row_mode == preferred_source_mode:
                    return image
        if reference_mode == "use_anchor_still":
            anchor_reference = _primary_identity_anchor_image(anchor_still_map)
            if anchor_reference:
                return anchor_reference
            return ""
    return ""



def _primary_identity_anchor_image(anchor_still_map: dict[str, dict] | None) -> str:
    if not isinstance(anchor_still_map, dict):
        return ""
    for anchor_id in ("ANCHOR_CHARACTER_UPPER_BODY", "ANCHOR_CHARACTER_FULL_BODY"):
        row = anchor_still_map.get(anchor_id)
        image = str(row.get("image", "")).strip() if isinstance(row, dict) else ""
        if image:
            return image
    for row in anchor_still_map.values():
        if not isinstance(row, dict):
            continue
        material_class = str(row.get("material_class", "")).strip().lower()
        anchor_type = str(row.get("anchor_type", "")).strip().lower()
        if "world" in material_class or "world" in anchor_type:
            continue
        image = str(row.get("image", "")).strip()
        if image and ("character" in material_class or "character" in anchor_type):
            return image
    return ""


def _reference_anchor_id(render_item: dict, reference_image: str, anchor_still_map: dict[str, dict] | None) -> str:
    selected_pose_anchor_id = str(render_item.get("selected_pose_anchor_id", "")).strip() if isinstance(render_item, dict) else ""
    if selected_pose_anchor_id:
        return selected_pose_anchor_id
    if not reference_image or not isinstance(anchor_still_map, dict):
        return ""
    for anchor_id in ("ANCHOR_CHARACTER_UPPER_BODY", "ANCHOR_CHARACTER_FULL_BODY"):
        row = anchor_still_map.get(anchor_id)
        if isinstance(row, dict) and str(row.get("image", "")).strip() == reference_image:
            return anchor_id
    for anchor_id, row in anchor_still_map.items():
        if isinstance(row, dict) and str(row.get("image", "")).strip() == reference_image:
            return str(anchor_id).strip()
    return ""


def _still_workflow_target(render_item: dict, reference_image: str) -> str:
    explicit = str(render_item.get("workflow_target", "")).strip() if isinstance(render_item, dict) else ""
    if explicit:
        return explicit
    if str(reference_image).strip():
        return "image_flux2_reference_image"
    return "image_flux2_text_to_image"


def _select_still_candidate(candidate_results: list[dict], render_item: dict) -> tuple[dict, int, str]:
    candidates = [row for row in candidate_results if isinstance(row, dict) and str(row.get("image", "")).strip()]
    if not candidates:
        return {"image": "", "retry": 0, "seed": None}, 0, "first_candidate"
    explicit_index = render_item.get("still_selection_index") if isinstance(render_item, dict) else None
    try:
        selected_index = int(explicit_index)
    except Exception:
        selected_index = 0
    if 0 <= selected_index < len(candidates) and explicit_index is not None:
        return dict(candidates[selected_index]), selected_index, "explicit_index"
    ranked_candidates = _rank_continuity_candidates(candidates, render_item)
    if ranked_candidates:
        ranked_index, selected_candidate = ranked_candidates[0]
        if ranked_index != 0:
            return dict(selected_candidate), ranked_index, "continuity_score"
    return dict(candidates[0]), 0, "first_candidate"



def _rank_continuity_candidates(candidates: list[dict], render_item: dict) -> list[tuple[int, dict]]:
    if not isinstance(render_item, dict):
        return []
    continuity_contract = render_item.get("continuity_contract") if isinstance(render_item.get("continuity_contract"), dict) else {}
    has_continuity_anchor = bool(str(continuity_contract.get("protagonist_anchor", "")).strip() or str(continuity_contract.get("world_anchor", "")).strip())
    if not has_continuity_anchor:
        return []
    scored: list[tuple[int, dict]] = []
    for index, row in enumerate(candidates):
        continuity_score = _safe_score(row.get("continuity_score"))
        if continuity_score is None:
            return []
        scored.append((index, row))
    return sorted(
        scored,
        key=lambda item: (
            -(_safe_score(item[1].get("continuity_score")) or 0.0),
            -(_safe_score(item[1].get("identity_score")) or 0.0),
            -(_safe_score(item[1].get("world_score")) or 0.0),
            int(item[1].get("retry", 0) or 0),
        ),
    )



def _safe_score(value: object) -> float | None:
    try:
        score = float(value)
    except Exception:
        return None
    if score < 0.0:
        return 0.0
    if score > 1.0:
        return 1.0
    return score



def _should_keep_raw_still_prompt(prompt_text: str, *, shot: dict, render_item: dict) -> bool:
    return _resolve_still_constraint_mode(prompt_text, shot=shot, render_item=render_item) == "raw"

def _sanitize_still_prompt_text(prompt_text: str) -> str:
    blocked_exact_tokens = {
        "japanese 80s city pop music video",
        "bold graphic composition",
        "graphic reflective close-up styling",
    }
    tokens: list[str] = []
    for token in [part.strip() for part in str(prompt_text or "").split(",") if part.strip()]:
        lower = token.lower()
        if lower in blocked_exact_tokens:
            continue
        if lower.startswith("progression:"):
            continue
        if lower.startswith("scene event:"):
            continue
        if token not in tokens:
            tokens.append(token)
    return ", ".join(tokens)
