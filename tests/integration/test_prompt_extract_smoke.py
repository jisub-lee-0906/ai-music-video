import shutil
from pathlib import Path

import ai_mv.core.orchestration.prompt_extract as extract_mod
from ai_mv.core.orchestration.config_defaults import default_config


def test_prompt_extract_writes_preview_artifacts(monkeypatch):
    run_id = "test-prompt-extract"
    shutil.rmtree(Path("artifacts/preflight") / run_id, ignore_errors=True)
    shutil.rmtree(Path("artifacts/preflight_state") / run_id, ignore_errors=True)

    monkeypatch.setattr(extract_mod, "_add_audio", lambda stage_input: stage_input.payload.update({"audio_plan": {"duration": 1}, "audio_map": {"sections": [{"name": "chorus", "label": "Chorus"}]}, "profile_intent": {"audio_intent": {"brief": "brief"}}, "planner_prompts": {"audio": {"prompt": "audio"}}, "workflow_inputs_preview": {"audio": {"text_inputs": {"tags": "brief"}}}}))
    monkeypatch.setattr(extract_mod, "_add_lyrics_timeline", lambda stage_input: stage_input.payload.update({"lyrics_timeline": {"sections": [{"section_name": "chorus", "section_label": "Chorus", "lines": [{"line_index": 1, "text": "x"}], "hook_lines": [1], "lyric_beats": [{"beat_id": "LB01", "line_refs": [1], "visible_action": "step", "payoff_role": "release"}]}]}, "planner_prompts": dict(stage_input.payload.get("planner_prompts", {}), lyrics_timeline={"prompt": "lyrics"}), "workflow_inputs_preview": dict(stage_input.payload.get("workflow_inputs_preview", {}), lyrics_timeline={"sections": []})}))
    monkeypatch.setattr(extract_mod, "_add_story_bible", lambda stage_input: stage_input.payload.update({"visual_story_bible": {"lyric_beats": [{"beat_id": "LB01", "section_name": "chorus", "section_label": "Chorus", "line_refs": [1], "visible_action": "step", "literal_image": "light", "emotional_turn": "lift", "continuity_anchor": "center", "payoff_role": "release", "location_family": "threshold", "palette_hint": "white", "lighting_hint": "glow", "camera_commitment": "front"}]}, "planner_prompts": dict(stage_input.payload.get("planner_prompts", {}), visual_story_bible={"prompt": "story"}), "workflow_inputs_preview": dict(stage_input.payload.get("workflow_inputs_preview", {}), visual_story_bible={"story_bible_preview": {"hero_identity_lock": "hero"}})}))
    monkeypatch.setattr(extract_mod, "_add_shot_timeline", lambda stage_input: stage_input.payload.update({"anchors": [{"shot_id": "S001", "anchor": "a.png", "duration_sec": 1.0}], "shot_timeline": {"shots": [{"lyric_beat_id": "LB01"}]}, "planner_prompts": dict(stage_input.payload.get("planner_prompts", {}), shot_timeline={"prompt": "shots"}), "workflow_inputs_preview": dict(stage_input.payload.get("workflow_inputs_preview", {}), shot_timeline={"master_anchor": {"text": "anchor"}})}))
    monkeypatch.setattr(extract_mod, "_add_shot_router", lambda stage_input: stage_input.payload.update({"clip_routes": [{"shot_id": "S001", "anchor": "a.png", "duration_sec": 1.0, "use_ref": False}], "planner_prompts": dict(stage_input.payload.get("planner_prompts", {}), shot_router={"prompt": "router"}), "workflow_inputs_preview": dict(stage_input.payload.get("workflow_inputs_preview", {}), shot_router={"decisions": []})}))
    monkeypatch.setattr(extract_mod, "_add_flux2_ref", lambda stage_input: stage_input.payload.update({"planner_prompts": dict(stage_input.payload.get("planner_prompts", {}), flux2_ref_chain={"batches": [{"prompt": "ref"}]}), "workflow_inputs_preview": dict(stage_input.payload.get("workflow_inputs_preview", {}), flux2_ref_chain={"items": [{"start_text": "ref start"}]})}))
    monkeypatch.setattr(extract_mod, "_add_wan", lambda stage_input: stage_input.payload.update({"clips": [{"shot_id": "S001", "video": "clip.mp4"}], "planner_prompts": dict(stage_input.payload.get("planner_prompts", {}), wan_interpolation={"batches": [{"prompt": "wan"}]}), "workflow_inputs_preview": dict(stage_input.payload.get("workflow_inputs_preview", {}), wan_interpolation={"clips": [{"positive_prompt": "wan pos", "negative_prompt": "wan neg"}]})}))

    cfg = default_config()
    rid = extract_mod.run_prompt_extract(cfg, run_id)
    assert rid == run_id
    assert (Path("artifacts/preflight") / run_id / "prompt_preview.json").exists()
    assert (Path("artifacts/preflight") / run_id / "workflow_inputs_preview.json").exists()
    assert (Path("artifacts/preflight") / run_id / "prompt_extract_summary.json").exists()
