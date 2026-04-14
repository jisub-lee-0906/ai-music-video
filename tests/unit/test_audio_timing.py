from __future__ import annotations

import numpy as np

from ai_mv.utils.audio_timing import _tempo_scalar


def test_tempo_scalar_accepts_plain_float():
    assert _tempo_scalar(107.66) == 107.66


def test_tempo_scalar_accepts_single_value_numpy_array():
    assert _tempo_scalar(np.array([107.66601562])) == 107.66601562


def test_tempo_scalar_falls_back_to_zero_for_empty_sequence():
    assert _tempo_scalar([]) == 0.0