from __future__ import annotations


def lane_mode_priors() -> dict:
    return {'intro': {'anchor': 0.45, 'intimate_closeup': 0.3, 'general_narrative': 0.25}, 'verse': {'general_narrative': 0.35, 'intimate_closeup': 0.4, 'anchor': 0.25}, 'pre_chorus': {'intimate_closeup': 0.35, 'drive_travel': 0.25, 'general_narrative': 0.4}, 'chorus': {'performance': 0.5, 'intimate_closeup': 0.25, 'general_narrative': 0.25}, 'bridge': {'bridge_transition': 0.45, 'intimate_closeup': 0.35, 'anchor': 0.2}, 'outro': {'anchor': 0.45, 'intimate_closeup': 0.35, 'general_narrative': 0.2}}
