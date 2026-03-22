import ai_mv.engines.flux_2_dev_ref.runner as ref_runner


def test_run_flux2_ref_uses_master_anchor_for_every_item(monkeypatch):
    calls = []

    def fake_stage(_config, path):
        return f"staged::{path}"

    def fake_run(_config, _workflow, bindings, _required, timeout_override=None):
        calls.append(bindings["node.inputs"]["46"]["image"])
        prefix = bindings["node.inputs"]["9"]["filename_prefix"]
        return {"files": [f"{prefix}.png"]}

    monkeypatch.setattr(ref_runner, "stage_image_for_comfy", fake_stage)
    monkeypatch.setattr(ref_runner, "run_workflow", fake_run)

    plan = {
        "items": [
            {
                "shot_id": "S001_C01",
                "ref": "master.png",
                "prompt_text": "The same anime girl, now steps forward. Off-center platform shot. Flat cel shading, thick clean outlines.",
                "duration_sec": 2.0,
                "clip_index": 1,
                "clip_count": 2,
                "section_name": "verse_1",
                "section_label": "Verse 1",
                "shot_type": "WORLD_EVENT",
            },
            {
                "shot_id": "S001_C02",
                "ref": "master.png",
                "prompt_text": "The same anime girl, now turns toward the gate. Off-center platform shot. Flat cel shading, thick clean outlines.",
                "duration_sec": 2.0,
                "clip_index": 2,
                "clip_count": 2,
                "section_name": "verse_1",
                "section_label": "Verse 1",
                "shot_type": "WORLD_EVENT",
            },
        ]
    }

    out = ref_runner.run_flux2_ref({"render": {"ref_size": "1024x576"}, "video": {"target": "1920x1080@24"}}, plan)

    assert calls[0] == "staged::master.png"
    assert calls[1] == "staged::master.png"
    assert out[0]["start_source"] == "tti_start"
    assert out[1]["start_source"] == "tti_start"


def test_run_flux2_ref_keeps_master_anchor_across_sections(monkeypatch):
    calls = []

    def fake_stage(_config, path):
        return f"staged::{path}"

    def fake_run(_config, _workflow, bindings, _required, timeout_override=None):
        calls.append(bindings["node.inputs"]["46"]["image"])
        prefix = bindings["node.inputs"]["9"]["filename_prefix"]
        return {"files": [f"{prefix}.png"]}

    monkeypatch.setattr(ref_runner, "stage_image_for_comfy", fake_stage)
    monkeypatch.setattr(ref_runner, "run_workflow", fake_run)

    plan = {
        "items": [
            {
                "shot_id": "S001",
                "ref": "master.png",
                "prompt_text": "The same anime girl, now waits by the window. Wide shot. Flat cel shading, thick clean outlines.",
                "duration_sec": 2.0,
                "clip_index": 1,
                "clip_count": 1,
                "section_name": "intro",
                "section_label": "Intro",
                "shot_type": "WORLD_EVENT",
            },
            {
                "shot_id": "S002",
                "ref": "master.png",
                "prompt_text": "The same anime girl, now walks into verse space. Wide shot. Flat cel shading, thick clean outlines.",
                "duration_sec": 2.0,
                "clip_index": 1,
                "clip_count": 1,
                "section_name": "verse_1",
                "section_label": "Verse 1",
                "shot_type": "WORLD_EVENT",
            },
        ]
    }

    out = ref_runner.run_flux2_ref({"render": {"ref_size": "1024x576"}, "video": {"target": "1920x1080@24"}}, plan)

    assert calls[0] == "staged::master.png"
    assert calls[1] == "staged::master.png"
    assert out[1]["start_source"] == "tti_start"
