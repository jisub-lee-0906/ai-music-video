from time import perf_counter

from ai_mv.engines.common.clip_timing import expand_anchor_clips


def test_expand_anchor_clips_large_batch_stays_fast():
    anchors = [_anchor(i) for i in range(400)]
    start = perf_counter()
    clips = expand_anchor_clips(anchors, fps=24, max_clip_sec=5.0)
    elapsed = perf_counter() - start
    assert len(clips) > len(anchors)
    assert elapsed < 0.5


def _anchor(idx: int) -> dict:
    return {
        "shot_id": f"S{idx:03d}",
        "duration_sec": 12.0,
        "section_name": "chorus",
        "shot_type": "CHAR_MASTER",
    }
