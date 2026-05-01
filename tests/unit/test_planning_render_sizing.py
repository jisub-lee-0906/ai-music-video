from ai_mv.core.planning.render_sizing import calculate_render_count



def test_calculate_render_count_steps_up_by_duration_bucket_and_caps_long_shots():
    assert calculate_render_count(0.0) == 1
    assert calculate_render_count(6.5) == 1
    assert calculate_render_count(6.6) == 2
    assert calculate_render_count(13.0) == 2
    assert calculate_render_count(13.1) == 3
    assert calculate_render_count(19.5) == 3
    assert calculate_render_count(25.0) == 4
    assert calculate_render_count(60.0) == 4
