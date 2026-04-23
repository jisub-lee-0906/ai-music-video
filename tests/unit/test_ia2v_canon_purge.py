from pathlib import Path

from ai_mv.core.output_paths import ltx_clip_prefix
from ai_mv.core.planning.sections import _merged_render_mode
from ai_mv.core.review.publishability import _rerender_prescription
from ai_mv.core.workflow_names import WORKFLOW_FILES
from ai_mv.engines import __all__ as engine_exports
from ai_mv.styles.alt_pop.rules import alt_pop_section_shot_specs
from ai_mv.styles.citypop.rules import citypop_section_shot_specs
from ai_mv.styles.dream_pop.rules import dream_pop_section_shot_specs
from ai_mv.styles.j_rock.rules import j_rock_section_shot_specs
from ai_mv.styles.k_indie.rules import k_indie_section_shot_specs
from ai_mv.styles.synthwave.rules import synthwave_section_shot_specs


SRC_ROOT = Path(__file__).resolve().parents[2] / "src" / "ai_mv"



def test_workflow_registry_contains_only_current_canon_files():
    assert WORKFLOW_FILES == (
        "audio_ace_step_1_5_checkpoint.json",
        "image_flux2_text_to_image.json",
        "image_flux2.json",
        "video_ltx2_3_ia2v.json",
    )



def test_engine_package_exports_only_current_engine_families():
    assert engine_exports == ["common", "acestep_1_5_aio", "flux2_image", "ltx_ia2v"]



def test_only_one_ltx_engine_package_remains():
    ltx_dirs = sorted(path.name for path in (SRC_ROOT / "engines").glob("ltx_*") if path.is_dir())
    assert ltx_dirs == ["ltx_ia2v"]



def test_clip_prefix_defaults_to_ia2v_when_mode_is_blank():
    assert ltx_clip_prefix("run-1", "S001", "") == "ai_mv/runs/run-1/clips/shot-S001-ia2v"



def test_section_merge_normalizes_to_ia2v():
    assert _merged_render_mode({"render_mode": ""}, {"render_mode": ""}) == "ia2v"
    assert _merged_render_mode({"render_mode": "ia2v"}, {"render_mode": ""}) == "ia2v"



def test_style_rule_packs_emit_ia2v_specs_only():
    style_specs = [
        citypop_section_shot_specs("chorus", 8.0),
        synthwave_section_shot_specs("chorus", 8.0),
        alt_pop_section_shot_specs("chorus", 4.0),
        dream_pop_section_shot_specs("chorus", 4.0),
        j_rock_section_shot_specs("chorus", 4.0),
        k_indie_section_shot_specs("chorus", 4.0),
    ]
    assert all(item["render_mode"] == "ia2v" for specs in style_specs for item in specs)



def test_clip_rerender_prescriptions_focus_only_ia2v():
    assert _rerender_prescription("rerender_clips_with_terminal_frame_cleanup")["workflow_focus"] == ["ia2v"]
    assert _rerender_prescription(
        "rerender_motion_fragile_shots_with_safer_keyframes"
    )["workflow_focus"] == ["flux2_image", "ia2v"]
    assert _rerender_prescription(
        "rerender_weak_shots_with_prompt_tightening", ["identity_drift"]
    )["workflow_focus"] == ["flux2_image", "ia2v"]
    assert _rerender_prescription(
        "rerender_continuity_break_shots", ["continuity_break", "identity_drift"]
    )["workflow_focus"] == ["flux2_image", "ia2v"]
