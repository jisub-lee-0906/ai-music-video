from __future__ import annotations

import json

from ai_mv.core.orchestration.bootstrap_guard import apply_director_brief, validate_sizes, validate_templates
from ai_mv.core.orchestration.config_defaults import apply_defaults, default_config
from ai_mv.engines.flux_2_dev_ref.runner import run_flux2_ref_probe
from ai_mv.entrypoints.doctor import run_doctor
from ai_mv.infra.single_flight_lock import acquire_lock, release_lock
from ai_mv.utils.project_root import project_root


def run_ref_probe(
    run_id: str | None = None,
    brief: str | None = None,
    ref: str | None = None,
    prompt: str | None = None,
    shot_id: str | None = None,
    frame_name: str | None = None,
) -> int:
    rid = str(run_id or "ref-probe").strip() or "ref-probe"
    lock = acquire_lock("ref-probe")
    try:
        cfg = _load_prepared_config(brief)
        if run_doctor(cfg) != 0:
            return 1
        image_path = run_flux2_ref_probe(
            cfg,
            ref=str(ref or "").strip(),
            prompt_text=str(prompt or "").strip(),
            shot_id=str(shot_id or "ref_probe").strip() or "ref_probe",
            frame_name=str(frame_name or "end").strip() or "end",
        )
        out_dir = project_root(__file__) / "artifacts" / "ref_probe" / rid
        out_dir.mkdir(parents=True, exist_ok=True)
        (out_dir / "prompt.txt").write_text(str(prompt or "").strip(), encoding="utf-8")
        (out_dir / "result.json").write_text(
            json.dumps(
                {
                    "brief": cfg["brief"],
                    "ref": str(ref or "").strip(),
                    "image_path": image_path,
                    "shot_id": str(shot_id or "ref_probe").strip() or "ref_probe",
                    "frame_name": str(frame_name or "end").strip() or "end",
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
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
