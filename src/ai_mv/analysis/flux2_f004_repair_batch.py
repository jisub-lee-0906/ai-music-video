from __future__ import annotations

from ai_mv.analysis.batch_common import pending_runs, save_results


CASE_ID = "F004"
VARIANTS = ["R1", "R2", "R3"]
SEEDS = [1001, 1002, 1003]
WORKFLOW_NAME = "image_flux2_text_to_image.json"
WORKFLOW_TARGET = "flux2_f004_repair_base_still"
NEGATIVE_MODE = "none"
REPO_CONSTRAINTS_MODE = "raw_workflow_only"

PROMPT_TEXT = {
    "R1": "single subject under station light, repair fragile face structure, stable environment",
    "R2": "single subject with reflective glass nearby, repair identity drift, one coherent scene",
    "R3": "single subject portrait with no panel layout, no collage, no split screen",
}



def build_f004_repair_runs() -> list[dict]:
    runs: list[dict] = []
    for variant_id in VARIANTS:
        for seed in SEEDS:
            runs.append(
                {
                    "run_id": f"{CASE_ID}_{variant_id}_s{seed}",
                    "case_id": CASE_ID,
                    "variant_id": variant_id,
                    "seed": seed,
                    "prompt_text": PROMPT_TEXT[variant_id],
                    "workflow_name": WORKFLOW_NAME,
                    "workflow_target": WORKFLOW_TARGET,
                    "repo_constraints_mode": REPO_CONSTRAINTS_MODE,
                }
            )
    return runs



def build_batch_metadata(*, batch_id: str) -> dict:
    return {
        "batch_id": batch_id,
        "workflow_name": WORKFLOW_NAME,
        "workflow_target": WORKFLOW_TARGET,
        "case": CASE_ID,
        "variants": list(VARIANTS),
        "seeds": list(SEEDS),
        "negative_mode": NEGATIVE_MODE,
    }
