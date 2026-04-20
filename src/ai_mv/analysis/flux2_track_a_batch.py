from __future__ import annotations

from ai_mv.analysis.batch_common import pending_runs, save_results


CASES = ["F001", "F002", "F003", "F004"]
VARIANTS = ["A1", "A2", "A3"]
SEEDS = [1001, 1002, 1003]
WORKFLOW_NAME = "image_flux2_text_to_image.json"
WORKFLOW_TARGET = "flux2_track_a_base_still"
SIZE = "1280x720"
NEGATIVE_MODE = "none"
REPO_CONSTRAINTS_MODE = "raw_workflow_only"


PROMPT_TEXT = {
    ("F001", "A1"): "lonely night drive boulevard, soft analog neon, wistful motion",
    ("F001", "A2"): "station-side walk under reflected light, cinematic stillness",
    ("F001", "A3"): "rainy curbside silhouette with passing headlights, quiet longing",
    ("F002", "A1"): "wet platform departure under sodium vapor light, held breath",
    ("F002", "A2"): "overpass window reflection with blurred taillights, bittersweet pause",
    ("F002", "A3"): "retro coupe crossing a neon arterial road, emotional release",
    ("F003", "A1"): "sea-wind overlook at blue dusk, unresolved romance",
    ("F003", "A2"): "convenience-store light and drifting air, intimate waiting",
    ("F003", "A3"): "city-edge pedestrian bridge with reflective glass, restrained yearning",
    ("F004", "A1"): "front-facing heroine under station light with reflective glass",
    ("F004", "A2"): "single-subject close framing near rain-streaked window, same world",
    ("F004", "A3"): "quiet underpass portrait with neon spill and stable composition",
}



def build_track_a_runs() -> list[dict]:
    runs: list[dict] = []
    for case_id in CASES:
        for variant_id in VARIANTS:
            prompt_text = PROMPT_TEXT[(case_id, variant_id)]
            for seed in SEEDS:
                runs.append(
                    {
                        "run_id": f"{case_id}_{variant_id}_s{seed}",
                        "case_id": case_id,
                        "variant_id": variant_id,
                        "seed": seed,
                        "prompt_text": prompt_text,
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
        "size": SIZE,
        "negative_mode": NEGATIVE_MODE,
        "repo_constraints_mode": REPO_CONSTRAINTS_MODE,
        "cases": list(CASES),
        "variants": list(VARIANTS),
        "seeds": list(SEEDS),
    }
