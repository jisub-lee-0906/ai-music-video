from pathlib import Path

import yaml

from ai_mv.entrypoints.start import run_start


def test_start_smoke():
    cfg = yaml.safe_load(Path("configs/default.yaml").read_text(encoding="utf-8"))
    cfg.setdefault("integrations", {})["strict_remote"] = False
    cfg.setdefault("limits", {})["strict_failure"] = False
    cfg.setdefault("runtime", {})["template_hash_lock"] = False
    cfg["audio"]["lyrics_file"] = "artifacts/reports/test-start-lyrics.txt"
    cfg["consistency"]["reference_images"] = []
    temp_cfg = Path("artifacts/reports/test-start-config.yaml")
    temp_cfg.write_text(yaml.safe_dump(cfg), encoding="utf-8")
    assert run_start(str(temp_cfg), "test-start") == 0
