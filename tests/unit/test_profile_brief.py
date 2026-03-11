from ai_mv.core.profile_brief import build_profile_brief


def test_build_profile_brief_infers_citypop_world_hint():
    brief = build_profile_brief(
        ["japanese city pop", "female solo vocal", "glossy electric piano"],
        "refined nostalgic nightlife, elegant adult romance, warm polished texture",
    )
    hook = brief["hook_direction"].lower()
    assert "street" in hook or "glass" in hook or "last ride" in hook
