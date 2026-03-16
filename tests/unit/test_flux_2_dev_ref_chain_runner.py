import ai_mv.engines.flux_2_dev_ref.runner as flux2_ref_runner
from ai_mv.core.output_paths import ANCHOR_DIR, flux2_ref_frame_prefix


def test_flux2_ref_reanchors_every_shot_from_master_reference(monkeypatch):
    trace: list[tuple[str, str]] = []

    def _fake_render_start(_config, item):
        return f"{flux2_ref_frame_prefix(item['shot_id'], 'start')}.png"

    def _fake_render_end(_config, item):
        trace.append((str(item["shot_id"]), str(item["ref"])))
        return f"{flux2_ref_frame_prefix(item['shot_id'], 'end')}.png"

    monkeypatch.setattr(flux2_ref_runner, "_render_start", _fake_render_start)
    monkeypatch.setattr(flux2_ref_runner, "_render_end", _fake_render_end)

    plan = {
        "items": [
            {"shot_id": "S001", "ref": f"{ANCHOR_DIR}/master.png", "section_name": "verse", "duration_sec": 4.0, "shot_type": "CHAR_MASTER", "is_chorus": False},
            {"shot_id": "S002", "ref": f"{ANCHOR_DIR}/master.png", "section_name": "verse", "duration_sec": 4.0, "shot_type": "CHAR_MASTER", "is_chorus": False},
            {"shot_id": "S003", "ref": f"{ANCHOR_DIR}/master.png", "section_name": "chorus", "duration_sec": 4.0, "shot_type": "CHAR_MASTER", "is_chorus": True},
            {"shot_id": "S004", "ref": f"{ANCHOR_DIR}/master.png", "section_name": "chorus", "duration_sec": 4.0, "shot_type": "CHAR_MASTER", "is_chorus": True},
        ]
    }
    out = flux2_ref_runner.run_flux2_ref({}, plan)

    assert out[0]["start"] == f"{flux2_ref_frame_prefix('S001', 'start')}.png"
    assert out[1]["start"] == f"{flux2_ref_frame_prefix('S002', 'start')}.png"
    assert out[2]["start"] == f"{flux2_ref_frame_prefix('S003', 'start')}.png"
    assert out[3]["start"] == f"{flux2_ref_frame_prefix('S004', 'start')}.png"
    assert trace == [
        ("S001", f"{ANCHOR_DIR}/master.png"),
        ("S002", f"{ANCHOR_DIR}/master.png"),
        ("S003", f"{ANCHOR_DIR}/master.png"),
        ("S004", f"{ANCHOR_DIR}/master.png"),
    ]
