from __future__ import annotations

from ai_mv.core.contracts.stage_io import StageInput, StageOutput
from ai_mv.core.output_paths import still_prefix
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
    still_results = []
    for shot in shot_plan:
        shot_id = str(shot.get("shot_id", "")).strip()
        render_item = render_map.get(shot_id, {})
        material_id = str(render_item.get("material_id", "") or shot.get("material_id", "")).strip()
        material_row = material_map.get(material_id, {})
        base_prompt_text = _still_prompt_text(render_item)
        prompt_text = _apply_still_constraint_policy(base_prompt_text, shot=shot, render_item=render_item)
        previous_image = str(prior_still_map.get(shot_id, {}).get("image", "")).strip()
        anchor_reference_image = _anchor_reference_image(render_item, generated_still_map, prior_still_map)
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
        still_results.append(
            {
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
                "identity_lock_strength": str(render_item.get("identity_lock_strength", "")).strip(),
                "status": "done",
            }
        )
        generated_still_map[shot_id] = still_results[-1]
    return StageOutput(
        "render_stills",
        "done",
        {
            "still_results": still_results,
            "workflow_inputs": {
                **dict(stage_input.payload.get("workflow_inputs", {})),
                "stills": {"count": len(still_results)},
            },
        },
        [],
    )


def _still_prompt_text(render_item: dict) -> str:
    for key in ("still_prompt_text", "prompt_polish", "prompt_draft", "prompt_seed"):
        value = str(render_item.get(key, "")).strip()
        if value:
            return value
    return "photoreal live-action still frame, neon-lit night street, cinematic mood, bittersweet atmosphere"


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



def _anchor_reference_image(render_item: dict, generated_still_map: dict[str, dict], prior_still_map: dict[str, dict]) -> str:
    if not isinstance(render_item, dict):
        return ""
    reference_mode = str(render_item.get("reference_mode", "")).strip().lower()
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
        for still_map in (generated_still_map, prior_still_map):
            for row in still_map.values():
                image = str(row.get("image", "")).strip() if isinstance(row, dict) else ""
                if image:
                    return image
        return ""
    if reference_mode in {"use_anchor_still", "use_performance_anchor_still"}:
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
            return ""
    return ""



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
