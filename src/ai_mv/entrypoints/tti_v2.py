from __future__ import annotations

import json

from ai_mv.core.orchestration.bootstrap_guard import apply_director_brief, validate_sizes, validate_templates
from ai_mv.core.orchestration.config_defaults import apply_defaults, default_config
from ai_mv.core.stages.tti_anchor_v2 import build_tti_anchor_v2_master_prompt
from ai_mv.core.workflow_names import TTI_WORKFLOW
from ai_mv.engines.flux_2_dev_tti.runner import run_tti
from ai_mv.entrypoints.doctor import run_doctor
from ai_mv.infra.single_flight_lock import acquire_lock, release_lock
from ai_mv.utils.project_root import project_root


def run_tti_v2(run_id: str | None = None, brief: str | None = None) -> int:
    rid = str(run_id or "tti-v2-probe").strip() or "tti-v2-probe"
    lock = acquire_lock("tti-v2")
    try:
        cfg = _load_prepared_config(brief)
        if run_doctor(cfg) != 0:
            return 1
        prompt_text = build_tti_anchor_v2_master_prompt(cfg)
        plan = {
            "master_anchor": {
                "prompt_text": prompt_text,
                "seed": 1,
                "kinetic_transition": "anchor",
            },
            "shots": [
                {
                    "shot_id": "tti_probe",
                    "shot_type": "CHAR_MASTER",
                    "section_name": "probe",
                    "section_label": "TTI Probe",
                    "duration_sec": 1.0,
                    "is_chorus": False,
                }
            ],
        }
        anchors = run_tti(cfg, plan)
        image_path = str(anchors[0]["identity_anchor"]) if anchors else ""
        out_dir = project_root(__file__) / "artifacts" / "tti_probe" / rid
        out_dir.mkdir(parents=True, exist_ok=True)
        (out_dir / "prompt.txt").write_text(prompt_text, encoding="utf-8")
        (out_dir / "result.json").write_text(json.dumps({"brief": cfg["brief"], "image_path": image_path}, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"run_id={rid}")
        print(f"brief={cfg['brief']}")
        print(f"image_path={image_path}")
        print(f"prompt_file={(out_dir / 'prompt.txt').as_posix()}")
        return 0 if image_path else 1
    finally:
        release_lock(lock)


def _load_prepared_config(brief: str | None) -> dict:
    cfg = default_config()
    cfg["brief"] = str(brief or "director_brief_example").strip() or "director_brief_example"
    apply_defaults(cfg)
    apply_director_brief(cfg)
    validate_sizes(cfg)
    validate_templates(cfg)
    return cfg
