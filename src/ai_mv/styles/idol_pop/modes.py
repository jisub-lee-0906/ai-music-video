from __future__ import annotations


def lane_mode_priors() -> dict:
    return {
        'intro': {'anchor': 0.25, 'general_narrative': 0.25, 'performance': 0.5},
        'verse': {'general_narrative': 0.25, 'performance': 0.5, 'drive_travel': 0.25},
        'pre_chorus': {'general_narrative': 0.2, 'intimate_closeup': 0.2, 'performance': 0.6},
        'chorus': {'performance': 0.75, 'general_narrative': 0.1, 'intimate_closeup': 0.15},
        'bridge': {'bridge_transition': 0.4, 'intimate_closeup': 0.35, 'performance': 0.25},
        'outro': {'anchor': 0.2, 'general_narrative': 0.2, 'performance': 0.6},
    }
