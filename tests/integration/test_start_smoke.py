from pathlib import Path

import yaml

import ai_mv.entrypoints.start as start_mod
from ai_mv.entrypoints.start import run_start


def test_start_smoke(monkeypatch):
    monkeypatch.setattr(start_mod, "run_doctor", lambda _cfg: 0)
    monkeypatch.setattr(start_mod, "run_pipeline", lambda _cfg, _rid: "test-start")
    monkeypatch.setattr(
        start_mod,
        "read_snapshot",
        lambda _rid: {"status": "done", "failure_reason": "", "completed_stages": []},
    )
    cfg = yaml.safe_load(Path("configs/default.yaml").read_text(encoding="utf-8"))
    cfg["runtime"]["template_hash_lock"] = False
    cfg.setdefault("audio", {})
    cfg["audio"]["lyrics"] = "test lyric block"
    temp_cfg = Path("artifacts/reports/test-start-config.yaml")
    temp_cfg.write_text(yaml.safe_dump(cfg), encoding="utf-8")
    assert run_start(str(temp_cfg), "test-start") == 0
