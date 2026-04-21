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
    render_plan = [row for row in stage_input.payload.get("render_plan", []) if isinstance(row, dict)]
    prior_stills = [row for row in stage_input.payload.get("still_results", []) if isinstance(row, dict)]
    render_map = {str(row.get("shot_id", "")).strip(): row for row in render_plan}
    prior_still_map = {str(row.get("shot_id", "")).strip(): row for row in prior_stills}
    still_results = []
    for shot in shot_plan:
        shot_id = str(shot.get("shot_id", "")).strip()
        render_item = render_map.get(shot_id, {})
        base_prompt_text = _still_prompt_text(render_item)
        prompt_text = _apply_still_constraint_policy(base_prompt_text, shot=shot, render_item=render_item)
        previous_image = str(prior_still_map.get(shot_id, {}).get("image", "")).strip()
        render_count = _render_count(render_item)
        candidate_images: list[str] = []
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
            candidate_images.append(
                run_flux2_still(
                    stage_input.config,
                    item,
                )
            )
        image_path = candidate_images[0]
        still_results.append(
            {
                "shot_id": shot_id,
                "image": image_path,
                "candidate_images": candidate_images,
                "candidate_count": len(candidate_images),
                "prompt_seed": str(render_item.get("prompt_seed", "")).strip(),
                "prompt_text": prompt_text,
                "status": "done",
            }
        )
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
    return "anime illustration, neon-lit night street, cinematic mood, bittersweet atmosphere"


def _single_keyframe_prompt_text(prompt_text: str) -> str:
    base = _sanitize_still_prompt_text(prompt_text)
    if _should_use_soft_single_scene_constraint(base):
        return _soft_single_scene_constraint_prompt_text(base)
    constraints = [
        "anime film still",
        "single cinematic keyframe",
        "single continuous scene",
        "one camera shot",
        "one uninterrupted composition",
        "full-bleed frame",
        "continuous background perspective",
        "subject integrated into the environment",
        "reflections within the same shot",
        "diegetic reflections only",
        "no inset portrait",
        "no secondary frame",
        "no juxtaposed scenes",
        "no panel layout",
        "no collage",
        "no split screen",
        "no text",
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
        "Render it as one clean anime film still in a single continuous scene, "
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
