from __future__ import annotations

import json
from pathlib import Path

from ai_mv.core.orchestration.bootstrap_guard import apply_director_brief, validate_sizes, validate_templates
from ai_mv.core.orchestration.config_defaults import apply_defaults, default_config
from ai_mv.engines.flux_2_dev_ref.runner import run_flux2_ref_probe
from ai_mv.entrypoints.doctor import run_doctor
from ai_mv.infra.single_flight_lock import acquire_lock, release_lock
from ai_mv.utils.project_root import project_root


def run_ref_v2_probe_batch(
    run_id: str | None = None,
    brief: str | None = None,
    ref: str | None = None,
    prompts_file: str | None = None,
    shot_id_prefix: str | None = None,
    frame_name: str | None = None,
) -> int:
    rid = str(run_id or "ref-v2-probe-batch").strip() or "ref-v2-probe-batch"
    lock = acquire_lock("ref-v2-probe-batch")
    try:
        cfg = _load_prepared_config(brief)
        if run_doctor(cfg) != 0:
            return 1
        ref_path = str(ref or "").strip()
        prompts_path = Path(str(prompts_file or "").strip())
        prompts = _load_prompts(prompts_path)
        if not prompts:
            raise RuntimeError("no prompts found in prompts file")
        prefix = str(shot_id_prefix or "ref_batch").strip() or "ref_batch"
        clean_frame_name = str(frame_name or "end").strip() or "end"
        out_dir = project_root(__file__) / "artifacts" / "ref_probe_batch" / rid
        out_dir.mkdir(parents=True, exist_ok=True)
        results: list[dict] = []
        for idx, row in enumerate(prompts, start=1):
            label = str(row.get("label", f"v{idx:02d}")).strip() or f"v{idx:02d}"
            prompt_text = str(row.get("prompt", "")).strip()
            if not prompt_text:
                continue
            shot_id = f"{prefix}_{label}"
            image_path = run_flux2_ref_probe(
                cfg,
                ref=ref_path,
                prompt_text=prompt_text,
                shot_id=shot_id,
                frame_name=clean_frame_name,
            )
            result_row = {
                "index": idx,
                "label": label,
                "shot_id": shot_id,
                "frame_name": clean_frame_name,
                "prompt": prompt_text,
                "image_path": image_path,
            }
            results.append(result_row)
            print(f"[{idx}/{len(prompts)}] {label} -> {image_path}")
        manifest = {
            "brief": cfg["brief"],
            "ref": ref_path,
            "prompts_file": prompts_path.as_posix(),
            "frame_name": clean_frame_name,
            "results": results,
        }
        (out_dir / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"run_id={rid}")
        print(f"manifest={(out_dir / 'manifest.json').as_posix()}")
        return 0 if results else 1
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


def _load_prompts(path: Path) -> list[dict]:
    if not path.exists():
        raise RuntimeError(f"prompts file not found: {path}")
    suffix = path.suffix.lower()
    if suffix == ".json":
        data = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(data, list):
            return [_normalize_prompt_row(idx, row) for idx, row in enumerate(data, start=1) if _normalize_prompt_row(idx, row)]
        raise RuntimeError("prompts json must be a list")
    rows: list[dict] = []
    for idx, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if "|" in line:
            label, prompt = line.split("|", 1)
            rows.append({"label": label.strip() or f"v{idx:02d}", "prompt": prompt.strip()})
        else:
            rows.append({"label": f"v{idx:02d}", "prompt": line})
    return rows


def _normalize_prompt_row(idx: int, row: object) -> dict | None:
    if isinstance(row, str):
        text = row.strip()
        return {"label": f"v{idx:02d}", "prompt": text} if text else None
    if isinstance(row, dict):
        prompt = str(row.get("prompt", "")).strip()
        if not prompt:
            return None
        label = str(row.get("label", f"v{idx:02d}")).strip() or f"v{idx:02d}"
        return {"label": label, "prompt": prompt}
    return None
