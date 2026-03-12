import ai_mv.engines.flux_1_dev_uso.runner as uso_runner
from ai_mv.core.output_paths import ANCHOR_DIR, uso_frame_prefix


def test_uso_reanchors_every_shot_from_master_reference(monkeypatch):
    trace: list[tuple[str, str]] = []

    def _fake_render_start(_config, item):
        return f"{uso_frame_prefix(item['shot_id'], 'start')}.png"

    def _fake_render_end(_config, item):
        trace.append((str(item["shot_id"]), str(item["ref"])))
        return f"{uso_frame_prefix(item['shot_id'], 'end')}.png"

    monkeypatch.setattr(uso_runner, "_render_start", _fake_render_start)
    monkeypatch.setattr(uso_runner, "_render_end", _fake_render_end)

    plan = {
        "items": [
            {"shot_id": "S001", "ref": f"{ANCHOR_DIR}/master.png", "section_name": "verse", "duration_sec": 4.0, "shot_type": "CHAR_MASTER", "is_chorus": False},
            {"shot_id": "S002", "ref": f"{ANCHOR_DIR}/master.png", "section_name": "verse", "duration_sec": 4.0, "shot_type": "CHAR_MASTER", "is_chorus": False},
            {"shot_id": "S003", "ref": f"{ANCHOR_DIR}/master.png", "section_name": "chorus", "duration_sec": 4.0, "shot_type": "CHAR_MASTER", "is_chorus": True},
            {"shot_id": "S004", "ref": f"{ANCHOR_DIR}/master.png", "section_name": "chorus", "duration_sec": 4.0, "shot_type": "CHAR_MASTER", "is_chorus": True},
        ]
    }
    out = uso_runner.run_uso({}, plan)

    assert out[0]["start"] == f"{uso_frame_prefix('S001', 'start')}.png"
    assert out[1]["start"] == f"{uso_frame_prefix('S002', 'start')}.png"
    assert out[2]["start"] == f"{uso_frame_prefix('S003', 'start')}.png"
    assert out[3]["start"] == f"{uso_frame_prefix('S004', 'start')}.png"
    assert trace == [
        ("S001", f"{ANCHOR_DIR}/master.png"),
        ("S002", f"{ANCHOR_DIR}/master.png"),
        ("S003", f"{ANCHOR_DIR}/master.png"),
        ("S004", f"{ANCHOR_DIR}/master.png"),
    ]
