from pathlib import Path

import yaml

from ai_mv.core.orchestration.pipeline import run_pipeline


def test_pipeline_smoke():
    cfg = yaml.safe_load(Path("configs/default.yaml").read_text(encoding="utf-8"))
    cfg.setdefault("integrations", {})["strict_remote"] = False
    cfg.setdefault("limits", {})["strict_failure"] = False
    temp_cfg = Path("artifacts/reports/test-smoke-config.yaml")
    temp_cfg.parent.mkdir(parents=True, exist_ok=True)
    temp_cfg.write_text(yaml.safe_dump(cfg), encoding="utf-8")
    rid = run_pipeline(str(temp_cfg), "test-smoke")
    assert rid == "test-smoke"
