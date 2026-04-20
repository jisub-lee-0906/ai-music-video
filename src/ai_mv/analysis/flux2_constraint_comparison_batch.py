from __future__ import annotations

from ai_mv.analysis.batch_common import save_results
from ai_mv.core.stages.render_stills import _single_keyframe_prompt_text


CASE_TO_PROMPT_FAMILY = {
    "F001": "A1",
    "F002": "A3",
    "F003": "A1",
    "F004": "R3",
}
CONSTRAINT_MODES = ["raw", "constrained"]
SEEDS = [1001, 1002, 1003]
WORKFLOW_NAME = "image_flux2_text_to_image.json"
WORKFLOW_TARGET = "flux2_repo_constraint_comparison"
PROMPT_TEXT = {
    "F001": "lonely boulevard with soft neon and distant headlights",
    "F002": "retro coupe crossing an elevated road under analog glow",
    "F003": "quiet seaside overlook with reflected city light and blue dusk",
    "F004": "young woman under station light with reflective glass",
}



def build_constraint_prompt(prompt_text: str) -> str:
    return _single_keyframe_prompt_text(prompt_text)



def build_constraint_comparison_runs() -> list[dict]:
    runs: list[dict] = []
    for case_id, prompt_family in CASE_TO_PROMPT_FAMILY.items():
        raw_prompt = PROMPT_TEXT[case_id]
        for constraint_mode in CONSTRAINT_MODES:
            prompt_text = build_constraint_prompt(raw_prompt) if constraint_mode == "constrained" else raw_prompt
            for seed in SEEDS:
                runs.append(
                    {
                        "run_id": f"{case_id}_{prompt_family}_{constraint_mode}_s{seed}",
                        "case_id": case_id,
                        "prompt_family": prompt_family,
                        "constraint_mode": constraint_mode,
                        "seed": seed,
                        "prompt_text": prompt_text,
                        "workflow_name": WORKFLOW_NAME,
                        "workflow_target": WORKFLOW_TARGET,
                    }
                )
    return runs



def build_batch_metadata(*, batch_id: str) -> dict:
    return {
        "batch_id": batch_id,
        "workflow_name": WORKFLOW_NAME,
        "workflow_target": WORKFLOW_TARGET,
        "constraint_modes": list(CONSTRAINT_MODES),
        "cases": list(CASE_TO_PROMPT_FAMILY.keys()),
        "prompt_families": dict(CASE_TO_PROMPT_FAMILY),
    }
