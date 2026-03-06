from ai_mv.engines.common.clip_timing import expand_anchor_clips


def test_expand_anchor_clips_keeps_chorus_segments_less_hurried():
    anchors = [{"shot_id": "S001", "duration_sec": 12.0, "section_name": "chorus"}]
    clips = expand_anchor_clips(anchors, fps=24, max_clip_sec=5.0)
    durations = [float(x["duration_sec"]) for x in clips]
    assert len(clips) == 4
    assert min(durations) >= 2.0
