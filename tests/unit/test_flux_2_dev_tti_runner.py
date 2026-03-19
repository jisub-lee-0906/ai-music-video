import ai_mv.engines.flux_2_dev_tti.runner as tti_runner
from ai_mv.core.output_paths import master_anchor_prefix


def test_run_tti_generates_master_and_shot_anchors(monkeypatch):
    calls = {"n": 0}

    def _fake_run(_config, _workflow, bindings, _required):
        calls["n"] += 1
        prefix = bindings["node.inputs"]["9"]["filename_prefix"]
        return {"files": [f"{prefix}.png"]}

    monkeypatch.setattr(tti_runner, "run_workflow", _fake_run)
    cfg = {"render": {"tti_size": "1024x1024"}}
    plan = {
        "master_anchor": {
            "prompt_text": "hero portrait, silver earrings, satin blouse, wet neon street, chrome reflections",
            "seed": 101,
        },
        "shots": [
            {"shot_id": "S001", "shot_type": "CHAR_MASTER", "section_name": "verse", "duration_sec": 4.0, "is_chorus": False, "prompt_text": "same heroine, verse frame", "seed": 201},
            {"shot_id": "S002", "shot_type": "PERF_WIDE", "section_name": "chorus", "duration_sec": 4.0, "is_chorus": True, "prompt_text": "same heroine, chorus frame", "seed": 202},
        ],
    }
    out = tti_runner.run_tti(cfg, plan)
    assert calls["n"] == 3
    assert out[0]["anchor"] != out[1]["anchor"]
    assert out[0]["identity_anchor"] == f"{master_anchor_prefix()}.png"
    assert out[0]["shot_anchor"].endswith("anchors/S001.png")
