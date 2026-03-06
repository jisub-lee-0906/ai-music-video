import ai_mv.engines.flux_1_dev_uso.runner as uso_runner


def test_uso_chains_within_section_and_reanchors_on_section_change(monkeypatch):
    trace: list[tuple[str, str]] = []

    def _fake_render_start(_config, item):
        return f"uso/{item['shot_id']}_start.png"

    def _fake_render_end(_config, item, start_ref):
        trace.append((str(item["shot_id"]), str(start_ref)))
        return f"uso/{item['shot_id']}_end.png"

    monkeypatch.setattr(uso_runner, "_render_start", _fake_render_start)
    monkeypatch.setattr(uso_runner, "_render_end", _fake_render_end)

    plan = {
        "items": [
            {"shot_id": "S001", "section_name": "verse", "duration_sec": 4.0, "shot_type": "CHAR_MASTER", "is_chorus": False},
            {"shot_id": "S002", "section_name": "verse", "duration_sec": 4.0, "shot_type": "CHAR_MASTER", "is_chorus": False},
            {"shot_id": "S003", "section_name": "chorus", "duration_sec": 4.0, "shot_type": "CHAR_MASTER", "is_chorus": True},
            {"shot_id": "S004", "section_name": "chorus", "duration_sec": 4.0, "shot_type": "CHAR_MASTER", "is_chorus": True},
        ]
    }
    out = uso_runner.run_uso({}, plan)

    assert out[0]["start"] == "uso/S001_start.png"
    assert out[1]["start"] == "uso/S001_end.png"
    assert out[2]["start"] == "uso/S003_start.png"
    assert out[3]["start"] == "uso/S003_end.png"
    assert trace == [
        ("S001", "uso/S001_start.png"),
        ("S002", "uso/S001_end.png"),
        ("S003", "uso/S003_start.png"),
        ("S004", "uso/S003_end.png"),
    ]
