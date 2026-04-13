from ai_mv.engines.common.clip_timing import expand_anchor_clips


def test_expand_anchor_clips_keeps_chorus_segments_less_hurried():
    anchors = [{"shot_id": "S001", "duration_sec": 12.0, "section_name": "chorus"}]
    clips = expand_anchor_clips(anchors, fps=24, max_clip_sec=5.0)
    durations = [float(x["duration_sec"]) for x in clips]
    assert len(clips) == 3
    assert min(durations) >= 3.2


def test_expand_anchor_clips_respects_hard_max_cap():
    anchors = [{"shot_id": "S001", "duration_sec": 6.0, "section_name": "intro"}]
    clips = expand_anchor_clips(anchors, fps=24, max_clip_sec=5.0)
    durations = [float(x["duration_sec"]) for x in clips]
    assert len(clips) == 2
    assert max(durations) <= 5.0


def test_expand_anchor_clips_assigns_clip_index_and_count():
    anchors = [{"shot_id": "S001", "duration_sec": 12.0, "section_name": "chorus"}]
    clips = expand_anchor_clips(anchors, fps=24, max_clip_sec=5.0)
    assert [x["clip_index"] for x in clips] == [1, 2, 3]
    assert [x["clip_count"] for x in clips] == [3, 3, 3]


def test_expand_anchor_clips_barely_over_cap_does_not_over_split():
    anchors = [{"shot_id": "S001", "duration_sec": 5.1, "section_name": "verse"}]
    clips = expand_anchor_clips(anchors, fps=24, max_clip_sec=5.0)
    assert len(clips) == 2
    assert min(float(x["duration_sec"]) for x in clips) >= 2.5
