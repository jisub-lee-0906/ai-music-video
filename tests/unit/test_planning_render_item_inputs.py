from ai_mv.core.planning.render_item_inputs import resolve_render_item_inputs
from ai_mv.styles.citypop.bible import get_citypop_bible



def test_resolve_render_item_inputs_derives_style_name_from_config_default_when_shot_is_implicit():
    shot = {"shot_id": "S001", "render_mode": "ia2v"}

    out = resolve_render_item_inputs(
        {"planning": {"default_style_name": "citypop"}},
        "lonely cinematic road at dusk",
        get_citypop_bible(),
        shot,
    )

    assert out["style_name"] == "citypop"
    assert out["style_bible"] == get_citypop_bible()
    assert out["shot"] is shot



def test_resolve_render_item_inputs_preserves_explicit_style_name_and_shot_argument():
    shot = {"shot_id": "S006", "render_mode": "ia2v"}
    style_bible = get_citypop_bible()

    out = resolve_render_item_inputs(
        {},
        "late-night city walk under wet neon lights",
        "citypop",
        style_bible,
        shot,
    )

    assert out == {"style_name": "citypop", "style_bible": style_bible, "shot": shot}
