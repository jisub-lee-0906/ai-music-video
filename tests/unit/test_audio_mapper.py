import json
from pathlib import Path

import pytest

import ai_mv.engines.acestep_1_5_aio.mapper as audio_mapper


def _acestep_workflow_prompt(tags: str = "Workflow-safe music tags") -> dict:
    return {"acestep": {"tags": tags}}


def test_map_audio_workflow_preserves_blank_language_when_unset():
    out = audio_mapper.map_audio_workflow(
        {},
        {
            "genre_description": "Synthwave: pulsing analog pads and a glossy nocturnal lead vocal.",
            "lyrics": "Streetlight flickers\nRearview ghosts",
            "seed": 41,
            "bpm": 112,
            "duration": 150,
            "language": "",
            "filename_prefix": "run_audio",
            "quality": "V0",
            "workflow_prompts": _acestep_workflow_prompt("Synthwave, glossy nocturnal lead vocal"),
        },
    )

    assert out["node.inputs"][audio_mapper.AUDIO_TEXT]["language"] == ""



def test_map_audio_workflow_preserves_explicit_supported_language():
    out = audio_mapper.map_audio_workflow(
        {},
        {
            "genre_description": "K-Indie: shimmering guitars and a warm intimate vocal.",
            "lyrics": "불빛 사이로\n천천히 걸어가",
            "seed": 52,
            "bpm": 96,
            "duration": 165,
            "language": "ko",
            "filename_prefix": "run_audio_ko",
            "quality": "V0",
            "workflow_prompts": _acestep_workflow_prompt("K-Indie, warm intimate vocal"),
        },
    )

    assert out["node.inputs"][audio_mapper.AUDIO_TEXT]["language"] == "ko"


def test_map_audio_workflow_targets_current_checkpoint_workflow_save_node():
    out = audio_mapper.map_audio_workflow(
        {},
        {
            "genre_description": "City Pop: glossy synths and warm live drums.",
            "lyrics": "late night signs glow",
            "seed": 7,
            "bpm": 108,
            "duration": 120,
            "language": "en",
            "filename_prefix": "audio/run-7",
            "quality": "V0",
            "workflow_prompts": _acestep_workflow_prompt("City Pop, glossy synths, warm live drums"),
        },
    )

    assert out["node.inputs"][audio_mapper.AUDIO_SAVE]["filename_prefix"] == "audio/run-7"
    assert out["node.inputs"][audio_mapper.AUDIO_SAVE]["quality"] == "V0"



def test_map_audio_workflow_publishes_acestep_quality_controls():
    out = audio_mapper.map_audio_workflow(
        {},
        {
            "genre_description": "Synthwave: analog polysynths, pulsing sidechain bass, crisp gated drums, and an intimate lead vocal.",
            "lyrics": "[Verse 1]\nChrome on the dash\n[Chorus]\nStay in the neon",
            "seed": 31,
            "bpm": 118,
            "duration": 31,
            "language": "en",
            "filename_prefix": "audio/songlet",
            "quality": "V0",
            "timesignature": "4",
            "generate_audio_codes": True,
            "cfg_scale": 2.0,
            "temperature": 0.85,
            "top_p": 0.9,
            "top_k": 0,
            "min_p": 0.0,
            "sampler_steps": 12,
            "sampler_cfg": 1.3,
            "sampler_name": "euler",
            "scheduler": "simple",
            "workflow_prompts": _acestep_workflow_prompt("Synthwave, intimate lead vocal"),
        },
    )

    text_inputs = out["node.inputs"][audio_mapper.AUDIO_TEXT]
    assert text_inputs["timesignature"] == "4"
    assert text_inputs["generate_audio_codes"] is True
    assert text_inputs["cfg_scale"] == 2.0
    assert text_inputs["temperature"] == 0.85
    assert text_inputs["top_p"] == 0.9
    assert text_inputs["top_k"] == 0
    assert text_inputs["min_p"] == 0.0
    sampler_inputs = out["node.inputs"][audio_mapper.AUDIO_KSAMPLER]
    assert sampler_inputs["steps"] == 12
    assert sampler_inputs["cfg"] == 1.3
    assert sampler_inputs["sampler_name"] == "euler"
    assert sampler_inputs["scheduler"] == "simple"


def test_map_audio_workflow_omits_non_positive_sampler_controls_from_planner_defaults():
    out = audio_mapper.map_audio_workflow(
        {},
        {
            "genre_description": "City Pop: warm drums and soft lead vocal.",
            "lyrics": "[Chorus]\nRun with me through the glow",
            "seed": 31,
            "bpm": 118,
            "duration": 30,
            "language": "en",
            "filename_prefix": "audio/planner-defaults",
            "quality": "V0",
            "sampler_steps": 0,
            "sampler_cfg": 0.0,
            "sampler_name": "",
            "scheduler": "",
            "workflow_prompts": _acestep_workflow_prompt("City Pop, soft lead vocal"),
        },
    )

    sampler_inputs = out["node.inputs"][audio_mapper.AUDIO_KSAMPLER]
    assert sampler_inputs == {"seed": sampler_inputs["seed"]}


def test_map_audio_workflow_omits_acestep_quality_controls_when_plan_uses_official_defaults():
    out = audio_mapper.map_audio_workflow(
        {},
        {
            "genre_description": "Synthwave: analog pads and a clean lead vocal.",
            "lyrics": "[Chorus]\nNeon heart, don't let go",
            "seed": 31,
            "bpm": 118,
            "duration": 31,
            "language": "en",
            "filename_prefix": "audio/default-parity",
            "quality": "V0",
            "timesignature": "4",
            "workflow_prompts": _acestep_workflow_prompt("Synthwave, clean lead vocal"),
        },
    )

    text_inputs = out["node.inputs"][audio_mapper.AUDIO_TEXT]
    assert "generate_audio_codes" not in text_inputs
    assert "cfg_scale" not in text_inputs
    assert "temperature" not in text_inputs
    assert "top_p" not in text_inputs
    assert "top_k" not in text_inputs
    assert "min_p" not in text_inputs


def test_audio_checkpoint_workflow_template_carries_required_official_advanced_text_defaults():
    workflow_path = Path(__file__).resolve().parents[2] / "workflows" / "audio_ace_step_1_5_checkpoint.json"
    workflow = json.loads(workflow_path.read_text(encoding="utf-8"))
    text_inputs = workflow[audio_mapper.AUDIO_TEXT]["inputs"]

    assert text_inputs["generate_audio_codes"] is True
    assert text_inputs["cfg_scale"] == 2
    assert text_inputs["temperature"] == 0.85
    assert text_inputs["top_p"] == 0.9
    assert text_inputs["top_k"] == 0
    assert text_inputs["min_p"] == 0


def test_map_audio_workflow_prefers_acestep_workflow_prompt_tags():
    out = audio_mapper.map_audio_workflow(
        {},
        {
            "genre_description": "Legacy visual prompt, city, neon, no crowd",
            "lyrics": "[Chorus]\nFollow the signal",
            "seed": 31,
            "bpm": 108,
            "duration": 30,
            "language": "en",
            "filename_prefix": "audio/workflow-tags",
            "quality": "V0",
            "workflow_prompts": {
                "acestep": {
                    "tags": "Alt Pop, intimate solo vocal, warm analog pulse, calm resolve",
                }
            },
        },
    )

    text_inputs = out["node.inputs"][audio_mapper.AUDIO_TEXT]
    assert text_inputs["tags"] == "Alt Pop, intimate solo vocal, warm analog pulse, calm resolve"
    assert "city" not in text_inputs["tags"].lower()
    assert "neon" not in text_inputs["tags"].lower()


def test_map_audio_workflow_fails_closed_when_acestep_workflow_prompt_missing():
    with pytest.raises(RuntimeError, match="missing acestep workflow prompt"):
        audio_mapper.map_audio_workflow(
            {},
            {
                "genre_description": "Legacy visual prompt, city, neon, no crowd",
                "lyrics": "[Chorus]\nFollow the signal",
                "seed": 31,
                "bpm": 108,
                "duration": 30,
                "language": "en",
                "filename_prefix": "audio/legacy-tags",
                "quality": "V0",
            },
        )
