from ai_mv.engines.ltx_ia2v.common import ltx_timeout


def test_ltx_timeout_uses_full_run_safety_cap_when_config_disables_timeout():
    assert ltx_timeout({"limits": {"ltx_timeout_seconds": 0}}) == 1800


def test_ltx_timeout_preserves_explicit_positive_override():
    assert ltx_timeout({"limits": {"ltx_timeout_seconds": 45}}) == 45
