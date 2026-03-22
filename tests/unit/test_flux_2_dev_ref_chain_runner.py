import ai_mv.engines.flux_2_dev_ref.runner as flux2_ref_runner
from ai_mv.core.output_paths import ANCHOR_DIR, flux2_ref_frame_prefix


def test_flux2_ref_reanchors_every_shot_from_master_reference(monkeypatch):
    trace: list[tuple[str, str]] = []

    def _fake_render_end(_config, item):
        trace.append((str(item["shot_id"]), str(item["ref"])))
        return f"{flux2_ref_frame_prefix(item['shot_id'], 'end')}.png"

    monkeypatch.setattr(flux2_ref_runner, "_render_end", _fake_render_end)
    monkeypatch.setattr(flux2_ref_runner, "stage_image_for_comfy", lambda _config, path: str(path))

    plan = {
        "items": [
            {"shot_id": "S001", "ref": f"{ANCHOR_DIR}/master.png", "section_name": "verse", "duration_sec": 4.0, "shot_type": "CHAR_MASTER", "is_chorus": False, "clip_index": 1, "clip_count": 2},
            {"shot_id": "S002", "ref": f"{ANCHOR_DIR}/master.png", "section_name": "verse", "duration_sec": 4.0, "shot_type": "CHAR_MASTER", "is_chorus": False, "clip_index": 2, "clip_count": 2},
            {"shot_id": "S003", "ref": f"{ANCHOR_DIR}/master.png", "section_name": "chorus", "duration_sec": 4.0, "shot_type": "CHAR_MASTER", "is_chorus": True, "clip_index": 1, "clip_count": 3},
            {"shot_id": "S004", "ref": f"{ANCHOR_DIR}/master.png", "section_name": "chorus", "duration_sec": 4.0, "shot_type": "CHAR_MASTER", "is_chorus": True, "clip_index": 2, "clip_count": 3},
        ]
    }
    out = flux2_ref_runner.run_flux2_ref({}, plan)

    assert out[0]["start"] == f"{ANCHOR_DIR}/master.png"
    assert out[1]["start"] == f"{ANCHOR_DIR}/master.png"
    assert out[2]["start"] == f"{ANCHOR_DIR}/master.png"
    assert out[3]["start"] == f"{ANCHOR_DIR}/master.png"
    assert out[0]["start_source"] == "tti_start"
    assert out[1]["start_source"] == "tti_start"
    assert out[2]["start_source"] == "tti_start"
    assert out[3]["start_source"] == "tti_start"
    assert trace == [
        ("S001", f"{ANCHOR_DIR}/master.png"),
        ("S002", f"{ANCHOR_DIR}/master.png"),
        ("S003", f"{ANCHOR_DIR}/master.png"),
        ("S004", f"{ANCHOR_DIR}/master.png"),
    ]
