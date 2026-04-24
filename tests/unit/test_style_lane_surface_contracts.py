import importlib


def _assert_lane_surface(lane_name: str, expected_style_lane: str):
    signals = importlib.import_module(f'ai_mv.styles.{lane_name}.signals')
    modes = importlib.import_module(f'ai_mv.styles.{lane_name}.modes')
    materials = importlib.import_module(f'ai_mv.styles.{lane_name}.materials')
    review = importlib.import_module(f'ai_mv.styles.{lane_name}.review')

    signal_map = signals.lane_match_signals()
    mode_priors = modes.lane_mode_priors()
    material_priors = materials.lane_material_priors()
    review_profile = review.lane_review_profile()

    assert signal_map['style_lane'] == expected_style_lane
    assert signal_map['style']
    assert isinstance(signal_map['style_aliases'], list) and signal_map['style_aliases']
    assert isinstance(signal_map['motifs'], list) and signal_map['motifs']
    assert isinstance(signal_map['camera_rules'], list) and signal_map['camera_rules']
    assert isinstance(signal_map['negative_rules'], list) and signal_map['negative_rules']
    assert 'chorus' in mode_priors
    assert 'performance' in mode_priors['chorus']
    assert 'world_continuity' in material_priors
    assert 'max_slideshow_risk_score' in review_profile
    assert 'min_lane_identity_score' in review_profile

def test_citypop_lane_surface_contract():
    _assert_lane_surface('citypop', 'citypop')

def test_idol_pop_lane_surface_contract():
    _assert_lane_surface('idol_pop', 'idol_pop')

def test_synthwave_lane_surface_contract():
    _assert_lane_surface('synthwave', 'synthwave')

def test_dream_pop_lane_surface_contract():
    _assert_lane_surface('dream_pop', 'dream_pop')

def test_alt_pop_lane_surface_contract():
    _assert_lane_surface('alt_pop', 'alt_pop')

def test_k_indie_lane_surface_contract():
    _assert_lane_surface('k_indie', 'k_indie')

def test_j_rock_lane_surface_contract():
    _assert_lane_surface('j_rock', 'j_rock')
