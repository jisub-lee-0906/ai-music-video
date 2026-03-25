import ai_mv.engines.flux_2_dev_ref.runner as flux2_ref_runner
from ai_mv.core.output_paths import ANCHOR_DIR, flux2_ref_frame_prefix


def test_flux2_ref_reanchors_every_shot_from_master_reference_but_renders_scene_specific_starts(monkeypatch):
    trace: list[tuple[str, str, str]] = []

    def _fake_render_frame(_config, item, *, frame_name, frame_idx):
        trace.append((str(item["shot_id"]), str(item["ref"]), str(frame_name)))
        return f"{flux2_ref_frame_prefix(item['shot_id'], frame_name)}.png"

    monkeypatch.setattr(flux2_ref_runner, "_render_frame", _fake_render_frame)

    plan = {
        "items": [
            {"shot_id": "S001", "ref": f"{ANCHOR_DIR}/master.png", "section_name": "verse", "duration_sec": 4.0, "shot_type": "CHAR_MASTER", "is_chorus": False, "clip_index": 1, "clip_count": 2},
            {"shot_id": "S002", "ref": f"{ANCHOR_DIR}/master.png", "section_name": "verse", "duration_sec": 4.0, "shot_type": "CHAR_MASTER", "is_chorus": False, "clip_index": 2, "clip_count": 2},
            {"shot_id": "S003", "ref": f"{ANCHOR_DIR}/master.png", "section_name": "chorus", "duration_sec": 4.0, "shot_type": "CHAR_MASTER", "is_chorus": True, "clip_index": 1, "clip_count": 3},
            {"shot_id": "S004", "ref": f"{ANCHOR_DIR}/master.png", "section_name": "chorus", "duration_sec": 4.0, "shot_type": "CHAR_MASTER", "is_chorus": True, "clip_index": 2, "clip_count": 3},
        ]
    }
    out = flux2_ref_runner.run_flux2_ref({}, plan)

    assert out[0]["start"] == f"{flux2_ref_frame_prefix('S001', 'start')}.png"
    assert out[1]["start"] == f"{flux2_ref_frame_prefix('S002', 'start')}.png"
    assert out[2]["start"] == f"{flux2_ref_frame_prefix('S003', 'start')}.png"
    assert out[3]["start"] == f"{flux2_ref_frame_prefix('S004', 'start')}.png"
    assert out[0]["start_source"] == "rendered_start"
    assert out[1]["start_source"] == "rendered_start"
    assert out[2]["start_source"] == "rendered_start"
    assert out[3]["start_source"] == "rendered_start"
    assert trace == [
        ("S001", f"{ANCHOR_DIR}/master.png", "start"),
        ("S001", f"{ANCHOR_DIR}/master.png", "end"),
        ("S002", f"{ANCHOR_DIR}/master.png", "start"),
        ("S002", f"{ANCHOR_DIR}/master.png", "end"),
        ("S003", f"{ANCHOR_DIR}/master.png", "start"),
        ("S003", f"{ANCHOR_DIR}/master.png", "end"),
        ("S004", f"{ANCHOR_DIR}/master.png", "start"),
        ("S004", f"{ANCHOR_DIR}/master.png", "end"),
    ]
