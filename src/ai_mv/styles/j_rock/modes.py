from __future__ import annotations


def lane_mode_priors() -> dict:
    return {'intro': {'anchor': 0.35, 'general_narrative': 0.3, 'performance': 0.35}, 'verse': {'general_narrative': 0.35, 'performance': 0.4, 'intimate_closeup': 0.25}, 'pre_chorus': {'performance': 0.35, 'drive_travel': 0.3, 'general_narrative': 0.35}, 'chorus': {'performance': 0.75, 'general_narrative': 0.15, 'intimate_closeup': 0.1}, 'bridge': {'bridge_transition': 0.35, 'intimate_closeup': 0.25, 'performance': 0.4}, 'outro': {'anchor': 0.3, 'performance': 0.45, 'general_narrative': 0.25}}
