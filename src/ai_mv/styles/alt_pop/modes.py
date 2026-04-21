from __future__ import annotations


def lane_mode_priors() -> dict:
    return {'intro': {'anchor': 0.35, 'general_narrative': 0.4, 'intimate_closeup': 0.25}, 'verse': {'general_narrative': 0.45, 'intimate_closeup': 0.3, 'drive_travel': 0.25}, 'pre_chorus': {'general_narrative': 0.3, 'intimate_closeup': 0.35, 'drive_travel': 0.35}, 'chorus': {'performance': 0.55, 'general_narrative': 0.25, 'intimate_closeup': 0.2}, 'bridge': {'bridge_transition': 0.45, 'intimate_closeup': 0.3, 'general_narrative': 0.25}, 'outro': {'anchor': 0.35, 'general_narrative': 0.4, 'intimate_closeup': 0.25}}
