from ai_mv.utils.text_utils import ensure_16_9, parse_target
from ai_mv.utils.time_utils import ffprobe_duration


def test_parse_target():
    w, h, fps = parse_target("1920x1080@24")
    assert (w, h, fps) == (1920, 1080, 24)


def test_ensure_16_9_ok():
    ensure_16_9(1024, 576)


def test_ensure_16_9_fail():
    try:
        ensure_16_9(1000, 1000)
        assert False
    except ValueError:
        assert True


def test_ffprobe_duration_returns_float():
    value = ffprobe_duration("not_found.wav")
    assert isinstance(value, float)
