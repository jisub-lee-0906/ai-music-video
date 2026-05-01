from ai_mv.core.planning.prompt_assembly import build_prompt_bundle, polish_prompt
from ai_mv.styles.citypop.bible import get_citypop_bible



def test_prompt_assembly_module_deduplicates_tokens_while_preserving_order():
    out = polish_prompt(
        "Japanese 80s city pop music video, film grain, reflective glass",
        "reflective glass, bold portrait framing, film grain",
    )

    assert out == "Japanese 80s city pop music video, film grain, reflective glass, bold portrait framing"



def test_prompt_assembly_module_builds_prompt_bundle_with_nonempty_fields():
    shot = {
        "shot_id": "S001",
        "render_mode": "ia2v",
        "shot_role": "verse_setup",
        "section_type": "verse",
        "section_name": "Verse 1",
        "visual_mode": "night_drive",
        "start_sec": 3.0,
        "duration_sec": 5.0,
        "protagonist_anchor": "same lone night-walk protagonist, stable dark outerwear silhouette, no competing bystanders",
        "world_anchor": "same rain-slick neon boulevard world, wet asphalt reflections, dense urban signage",
    }

    out = build_prompt_bundle(
        "citypop",
        "late-night city pop walk under wet neon lights",
        get_citypop_bible(),
        shot,
    )

    assert out["prompt_seed"]
    assert out["prompt_draft"]
    assert out["prompt_polish"]
    assert len(out["prompt_polish"].split(", ")) == len(set(out["prompt_polish"].split(", ")))
