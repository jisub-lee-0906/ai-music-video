import ai_mv.engines.flux_1_dev_tti.runner as tti_runner
from ai_mv.core.output_paths import tti_anchor_prefix


def test_run_tti_uses_single_master_anchor(monkeypatch):
    calls = {"n": 0}

    def _fake_run(_config, _workflow, _bindings, _required):
        calls["n"] += 1
        return {"files": [f"{tti_anchor_prefix()}.png"]}

    monkeypatch.setattr(tti_runner, "run_workflow", _fake_run)
    cfg = {"limits": {"max_retries_per_shot": 1}, "render": {"tti_size": "1024x1024"}}
    plan = {
        "master_anchor": {
            "prompt_text": "hero portrait, silver earrings, satin blouse, wet neon street, chrome reflections",
            "seed": 101,
        },
        "shots": [
            {"shot_id": "S001", "shot_type": "CHAR_MASTER", "section_name": "verse", "duration_sec": 4.0, "is_chorus": False},
            {"shot_id": "S002", "shot_type": "PERF_WIDE", "section_name": "chorus", "duration_sec": 4.0, "is_chorus": True},
        ],
    }
    out = tti_runner.run_tti(cfg, plan)
    assert calls["n"] == 1
    assert out[0]["anchor"] == out[1]["anchor"]
    assert out[0]["identity_anchor"] == f"{tti_anchor_prefix()}.png"
