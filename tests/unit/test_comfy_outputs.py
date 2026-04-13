import pytest

from ai_mv.core.contracts.errors import ComfyRequestError
from ai_mv.infra.comfy_outputs import pick_image_file, pick_video_file


def test_pick_image_file_requires_single_match():
    with pytest.raises(ComfyRequestError, match="count mismatch"):
        pick_image_file(["a.png", "b.png"], "TTI")


def test_pick_video_file_returns_single_match():
    assert pick_video_file(["clips/a.mp4"], "WAN") == "clips/a.mp4"
