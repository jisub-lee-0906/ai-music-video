from __future__ import annotations


def lane_mode_priors() -> dict:
    return {'intro': {'anchor': 0.5, 'drive_travel': 0.2, 'general_narrative': 0.3}, 'verse': {'general_narrative': 0.4, 'drive_travel': 0.35, 'intimate_closeup': 0.25}, 'pre_chorus': {'drive_travel': 0.4, 'general_narrative': 0.3, 'intimate_closeup': 0.3}, 'chorus': {'performance': 0.45, 'drive_travel': 0.3, 'anchor': 0.25}, 'bridge': {'bridge_transition': 0.65, 'anchor': 0.2, 'intimate_closeup': 0.15}, 'outro': {'anchor': 0.45, 'drive_travel': 0.35, 'general_narrative': 0.2}}
