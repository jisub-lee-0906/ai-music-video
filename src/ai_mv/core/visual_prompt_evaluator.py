from __future__ import annotations


_SUBJECT_PREFIXES = (
    "the same korean female idol",
    "same heroine",
)

_MULTI_SUBJECT_TOKENS = (
    "another woman",
    "another man",
    "two women",
    "two people",
    "holding hands",
    "embrace",
    "hug",
    "them ",
    "their ",
)

_ACTION_TOKENS = (
    "walk",
    "step",
    "pass",
    "clear",
    "cross",
    "turn",
    "lean",
    "brace",
    "touch",
    "climb",
    "descend",
    "move",
    "shift",
)

_STATIC_ONLY_TOKENS = (
    "breathes",
    "waits",
    "watches",
    "looks toward",
    "gazes",
    "holds still",
    "remains",
    "stands still",
)

_OPTICAL_TAKEOVER_TOKENS = (
    "window light",
    "lit windows",
    "passing train window",
    "train window",
    "carriage window",
    "glass wall",
    "stopped clock",
    "clock above",
    "signal light",
)


def build_visual_prompt_evaluation(payload: dict) -> dict:
    workflow_inputs = payload.get("workflow_inputs_preview", {})
    backend = workflow_inputs.get("backend_preview_v2", {}) if isinstance(workflow_inputs, dict) else {}
    if not backend and isinstance(payload.get("backend_preview_v2"), dict):
        backend = payload.get("backend_preview_v2", {})
    ref_rows = [row for row in backend.get("ref_adapter_v2", []) if isinstance(row, dict)]
    wan_rows = [row for row in backend.get("wan_adapter_v2", []) if isinstance(row, dict)]
    if not ref_rows and not wan_rows:
        return {}
    ref_eval = _evaluate_ref_rows(ref_rows)
    wan_eval = _evaluate_wan_rows(wan_rows)
    return {
        "ref_prompt_contracts": ref_eval,
        "wan_prompt_contracts": wan_eval,
    }


def _evaluate_ref_rows(rows: list[dict]) -> dict:
    total = len(rows) or 1
    subject_first = 0
    single_heroine = 0
    readable_action = 0
    grounded_surface = 0
    optical_takeover = 0
    archetype_match = 0
    adjacent_state = 0
    for row in rows:
        start = str(row.get("start_prompt_preview", "")).strip().lower()
        end = str(row.get("end_prompt_preview", "")).strip().lower()
        raw = dict(row.get("raw_prompt_clauses", {}))
        primary_surface = str(raw.get("primary_surface", "")).strip().lower()
        archetype = str(raw.get("ref_archetype", "")).strip().lower()
        start_state = str(raw.get("start_state", "")).strip().lower()
        end_state = str(raw.get("end_state", "")).strip().lower()
        if start.startswith(_SUBJECT_PREFIXES):
            subject_first += 1
        if not any(token in start for token in _MULTI_SUBJECT_TOKENS) and not any(token in end for token in _MULTI_SUBJECT_TOKENS):
            single_heroine += 1
        if any(token in start_state or token in end_state for token in _ACTION_TOKENS) and not (
            any(token in start_state for token in _STATIC_ONLY_TOKENS) and not any(token in start_state for token in _ACTION_TOKENS)
        ):
            readable_action += 1
        if primary_surface:
            grounded_surface += 1
        if any(token in start or token in end or token in primary_surface for token in _OPTICAL_TAKEOVER_TOKENS):
            if archetype != "window_contact":
                optical_takeover += 1
        if _matches_ref_archetype(archetype, primary_surface, start_state, end_state):
            archetype_match += 1
        if start_state and end_state and start_state != end_state:
            adjacent_state += 1
    subject_ratio = round(subject_first / float(total), 3)
    single_ratio = round(single_heroine / float(total), 3)
    action_ratio = round(readable_action / float(total), 3)
    surface_ratio = round(grounded_surface / float(total), 3)
    archetype_ratio = round(archetype_match / float(total), 3)
    adjacency_ratio = round(adjacent_state / float(total), 3)
    takeover_ratio = round(optical_takeover / float(total), 3)
    strengths = []
    risks = []
    if subject_ratio >= 0.8:
        strengths.append("REF prompts stay subject-first in most shots.")
    else:
        risks.append("REF prompts still bury the heroine behind setup in too many shots.")
    if single_ratio >= 0.95:
        strengths.append("REF prompts keep single-heroine continuity stable.")
    else:
        risks.append("REF prompts still risk multi-subject drift.")
    if action_ratio >= 0.8:
        strengths.append("REF prompts use readable body-led actions instead of mood-only phrasing.")
    else:
        risks.append("REF prompts still contain too many weak or static action lines.")
    if surface_ratio >= 0.9:
        strengths.append("REF prompts keep a concrete playable surface in view.")
    else:
        risks.append("REF prompts still lose the grounded surface too often.")
    if takeover_ratio <= 0.1:
        strengths.append("Optical motifs rarely take over the REF prompt nucleus.")
    else:
        risks.append("Optical motifs still replace the main action in some REF prompts.")
    if archetype_ratio >= 0.75:
        strengths.append("REF prompts mostly match their archetype contract.")
    else:
        risks.append("REF prompts still drift away from the intended archetype pattern.")
    if adjacency_ratio >= 0.8:
        strengths.append("REF start/end states usually read as adjacent keyframes.")
    else:
        risks.append("REF start/end states still collapse into too-similar or too-generic phrasing.")
    return {
        "reasoning": "REF prompt previews were checked for subject priority, single-heroine continuity, readable action, grounded surface, optical takeover, archetype match, and adjacent-state continuity.",
        "strengths": strengths,
        "risks": risks,
        "metrics": {
            "subject_first_ratio": subject_ratio,
            "single_heroine_ratio": single_ratio,
            "readable_action_ratio": action_ratio,
            "grounded_surface_ratio": surface_ratio,
            "optical_takeover_ratio": takeover_ratio,
            "archetype_match_ratio": archetype_ratio,
            "adjacent_state_ratio": adjacency_ratio,
        },
    }


def _evaluate_wan_rows(rows: list[dict]) -> dict:
    total = len(rows) or 1
    bridge_integrity = 0
    subject_first = 0
    optical_takeover = 0
    for row in rows:
        positive = str(row.get("positive_prompt_preview", "")).strip().lower()
        raw = dict(row.get("raw_prompt_clauses", {}))
        bridge_action = str(raw.get("bridge_action", "")).strip().lower()
        if positive.startswith(_SUBJECT_PREFIXES):
            subject_first += 1
        if bridge_action and any(token in bridge_action for token in _ACTION_TOKENS) and "camera" not in positive:
            bridge_integrity += 1
        if any(token in positive for token in _OPTICAL_TAKEOVER_TOKENS):
            if str(raw.get("ref_archetype", "")).strip().lower() != "window_contact":
                optical_takeover += 1
    bridge_ratio = round(bridge_integrity / float(total), 3)
    subject_ratio = round(subject_first / float(total), 3)
    takeover_ratio = round(optical_takeover / float(total), 3)
    strengths = []
    risks = []
    if bridge_ratio >= 0.8:
        strengths.append("WAN prompts read as visible bridges instead of new scenes.")
    else:
        risks.append("WAN prompts still drift toward generic scene description instead of transition.")
    if subject_ratio >= 0.8:
        strengths.append("WAN prompts keep the heroine readable as the acting subject.")
    else:
        risks.append("WAN prompts do not stay consistently subject-first.")
    if takeover_ratio <= 0.1:
        strengths.append("WAN prompts mostly keep optical details subordinate to the bridge action.")
    else:
        risks.append("WAN prompts still let optical motifs overshadow the bridge.")
    return {
        "reasoning": "WAN prompt previews were checked for subject priority, bridge integrity, and optical takeover.",
        "strengths": strengths,
        "risks": risks,
        "metrics": {
            "subject_first_ratio": subject_ratio,
            "bridge_integrity_ratio": bridge_ratio,
            "optical_takeover_ratio": takeover_ratio,
        },
    }


def _matches_ref_archetype(archetype: str, primary_surface: str, start_state: str, end_state: str) -> bool:
    if not archetype:
        return False
    text = f"{primary_surface} {start_state} {end_state}"
    if archetype == "threshold_crossing":
        return any(token in text for token in ("threshold", "exit line", "street edge", "clear", "cross", "beyond"))
    if archetype == "stair_descent":
        return any(token in text for token in ("stairs", "stairwell", "handrail", "step", "lower"))
    if archetype == "passage_compression":
        return any(token in text for token in ("passage", "wall", "close", "rail"))
    if archetype == "platform_edge":
        return any(token in text for token in ("platform edge", "yellow line", "platform"))
    if archetype == "gate_pass":
        return any(token in text for token in ("gate", "turnstile", "beyond"))
    if archetype == "window_contact":
        return any(token in text for token in ("window", "glass", "shoulder", "touch", "trace", "press", "brush"))
    if archetype == "curb_crossing":
        return any(token in text for token in ("crosswalk", "curb", "far curb"))
    if archetype == "sidewalk_continuation":
        return any(token in text for token in ("sidewalk", "pavement", "street edge", "moves forward"))
    if archetype == "doorway_handoff":
        return any(token in text for token in ("doorway", "door edge", "threshold", "beyond"))
    if archetype == "brace_pause":
        return any(token in text for token in ("brace", "rail", "wall", "pause"))
    if archetype == "ramp_descent":
        return any(token in text for token in ("ramp", "slope", "lower"))
    if archetype == "turn_back_once":
        return any(token in text for token in ("over one shoulder", "looks back", "turns back"))
    if archetype == "indoor_corridor":
        return any(token in text for token in ("corridor", "hall", "wall"))
    if archetype == "bench_rest":
        return any(token in text for token in ("bench", "seat", "rise again", "foot still planted"))
    return True
