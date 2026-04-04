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
    "reach",
    "enter",
    "follow",
    "carry",
    "run",
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

_TRACE_TOKENS = ("footprint", "footprints", "trail", "trace")
_SECONDARY_DETAIL_TOKENS = ("one arm swinging free", "free arm", "handrail", "rail", "curb line")


def build_visual_prompt_evaluation(payload: dict) -> dict:
    workflow_inputs = payload.get("workflow_inputs_preview", {})
    backend = workflow_inputs.get("backend_preview", {}) if isinstance(workflow_inputs, dict) else {}
    if not backend and isinstance(payload.get("backend_preview"), dict):
        backend = payload.get("backend_preview", {})
    ref_rows = [row for row in backend.get("ref_adapter", []) if isinstance(row, dict)]
    wan_rows = [row for row in backend.get("wan_adapter", []) if isinstance(row, dict)]
    if not ref_rows and not wan_rows:
        return {}
    return {
        "prompt_execution_review": _evaluate_ref_rows(ref_rows),
        "visual_generation_contracts": _evaluate_wan_rows(wan_rows),
    }


def _evaluate_ref_rows(rows: list[dict]) -> dict:
    total = len(rows) or 1
    story_function_match = 0
    archetype_match = 0
    prompt_shape_match = 0
    surface_anchor_strength = 0
    motion_readability = 0
    trace_detail_balance = 0
    single_heroine = 0
    optical_takeover = 0
    for row in rows:
        start = str(row.get("start_prompt_preview", "")).strip().lower()
        end = str(row.get("end_prompt_preview", "")).strip().lower()
        raw = dict(row.get("raw_prompt_clauses", {}))
        story_function = str(raw.get("story_function", "")).strip().lower()
        archetype = str(raw.get("ref_archetype", "")).strip().lower()
        surface = str(raw.get("primary_surface", "")).strip().lower()
        action = str(raw.get("dominant_action", "")).strip().lower()
        continuity = str(raw.get("continuity_delta", "")).strip().lower()
        trace = str(raw.get("content_trace", "")).strip().lower()
        selected_shape = str(raw.get("selected_prompt_shape", "")).strip().lower()
        text = f"{start} {end} {surface} {action} {continuity} {trace}"
        if _matches_story_function(story_function, action, continuity, surface):
            story_function_match += 1
        if _matches_ref_archetype(archetype, surface, action, continuity, trace):
            archetype_match += 1
        if _matches_prompt_shape(selected_shape, start, end, surface, action, trace):
            prompt_shape_match += 1
        if surface and (start.startswith(_SUBJECT_PREFIXES) or end.startswith(_SUBJECT_PREFIXES)) and surface in text:
            surface_anchor_strength += 1
        if any(token in action or token in continuity or token in text for token in _ACTION_TOKENS):
            motion_readability += 1
        if not trace or (
            any(token in trace for token in _TRACE_TOKENS + _SECONDARY_DETAIL_TOKENS)
            and any(token in surface for token in ("platform", "edge", "threshold", "crosswalk", "stairs", "passage", "gate", "sidewalk"))
        ):
            trace_detail_balance += 1
        if not any(token in text for token in _MULTI_SUBJECT_TOKENS):
            single_heroine += 1
        if any(token in text for token in _OPTICAL_TAKEOVER_TOKENS) and archetype != "window_contact":
            optical_takeover += 1
    metrics = {
        "story_function_match": round(story_function_match / float(total), 3),
        "archetype_selection_match": round(archetype_match / float(total), 3),
        "prompt_shape_match": round(prompt_shape_match / float(total), 3),
        "surface_anchor_strength": round(surface_anchor_strength / float(total), 3),
        "motion_readability": round(motion_readability / float(total), 3),
        "trace_detail_balance": round(trace_detail_balance / float(total), 3),
        "single_heroine_integrity": round(single_heroine / float(total), 3),
        "optical_takeover_ratio": round(optical_takeover / float(total), 3),
    }
    strengths = []
    risks = []
    if metrics["story_function_match"] >= 0.85:
        strengths.append("REF prompt lines preserve the intended story function in most shots.")
    else:
        risks.append("REF prompt lines still drift away from the intended story function.")
    if metrics["archetype_selection_match"] >= 0.85:
        strengths.append("REF prompt lines mostly execute the intended archetype contract.")
    else:
        risks.append("REF prompt lines still drift away from the chosen archetype.")
    if metrics["prompt_shape_match"] >= 0.85:
        strengths.append("REF prompt lines follow the chosen sentence shape instead of flattening into generic prose.")
    else:
        risks.append("REF prompt lines still flatten away from the selected sentence shape.")
    if metrics["surface_anchor_strength"] >= 0.9:
        strengths.append("REF prompt lines keep a readable surface anchor near the sentence head.")
    else:
        risks.append("REF prompt lines still lose surface geometry too often.")
    if metrics["motion_readability"] >= 0.85:
        strengths.append("REF prompt lines keep readable body-led action or locomotion change.")
    else:
        risks.append("REF prompt lines still contain weak motion phrasing.")
    if metrics["trace_detail_balance"] >= 0.85:
        strengths.append("Trace details mostly stay secondary to the route geometry and action.")
    else:
        risks.append("Trace details still compete with the main surface or action too often.")
    if metrics["single_heroine_integrity"] >= 0.95:
        strengths.append("REF prompts keep single-heroine continuity stable.")
    else:
        risks.append("REF prompts still risk multi-subject drift.")
    if metrics["optical_takeover_ratio"] <= 0.1:
        strengths.append("Optical motifs rarely take over the prompt nucleus.")
    else:
        risks.append("Optical motifs still replace the main action in some prompts.")
    return {
        "reasoning": "REF prompt previews were checked for story-function fit, archetype fit, selected prompt-shape execution, surface anchoring, motion readability, trace-detail balance, and single-heroine integrity.",
        "strengths": strengths,
        "risks": risks,
        "metrics": metrics,
    }


def _evaluate_wan_rows(rows: list[dict]) -> dict:
    total = len(rows) or 1
    adjacency = 0
    single_heroine = 0
    motion_readability = 0
    optical_takeover = 0
    for row in rows:
        positive = str(row.get("positive_prompt_preview", "")).strip().lower()
        raw = dict(row.get("raw_prompt_clauses", {}))
        bridge_action = str(raw.get("bridge_action", "")).strip().lower()
        start_ref = str(raw.get("start_ref_shot_id", "")).strip()
        end_ref = str(raw.get("end_ref_shot_id", "")).strip()
        if start_ref and end_ref and start_ref != end_ref:
            adjacency += 1
        if not any(token in positive for token in _MULTI_SUBJECT_TOKENS):
            single_heroine += 1
        if any(token in bridge_action or token in positive for token in _ACTION_TOKENS):
            motion_readability += 1
        if any(token in positive for token in _OPTICAL_TAKEOVER_TOKENS):
            optical_takeover += 1
    metrics = {
        "adjacent_transition_integrity": round(adjacency / float(total), 3),
        "single_heroine_integrity": round(single_heroine / float(total), 3),
        "motion_readability": round(motion_readability / float(total), 3),
        "optical_takeover_ratio": round(optical_takeover / float(total), 3),
    }
    strengths = []
    risks = []
    if metrics["adjacent_transition_integrity"] >= 0.9:
        strengths.append("WAN prompts preserve adjacent keyframe chaining.")
    else:
        risks.append("WAN prompts still lose adjacent keyframe integrity.")
    if metrics["single_heroine_integrity"] >= 0.95:
        strengths.append("WAN prompts keep single-heroine continuity stable.")
    else:
        risks.append("WAN prompts still risk multi-subject drift.")
    if metrics["motion_readability"] >= 0.8:
        strengths.append("WAN prompts keep the bridge action visible instead of collapsing into static mood wording.")
    else:
        risks.append("WAN prompts still weaken the bridge into low-motion prose.")
    if metrics["optical_takeover_ratio"] <= 0.1:
        strengths.append("WAN prompts mostly keep optical detail subordinate to the bridge action.")
    else:
        risks.append("WAN prompts still let optical motifs overshadow the bridge action.")
    return {
        "reasoning": "WAN prompt previews were checked for adjacent-keyframe chaining, single-heroine continuity, bridge motion readability, and optical takeover.",
        "strengths": strengths,
        "risks": risks,
        "metrics": metrics,
    }


def _matches_story_function(story_function: str, action: str, continuity: str, surface: str) -> bool:
    text = f"{surface} {action} {continuity}"
    mapping = {
        "entry": ("enter", "inside", "cross", "clear", "gate", "threshold", "takes the route", "steps onto", "sets her line", "commits to", "first committed stride", "path feel established", "steps in from", "entry side", "road opening ahead"),
        "continuation": ("keep", "move", "step", "along", "forward", "next step", "same stride", "one step farther", "still aimed", "keeps crossing", "middle-right side", "keeps the crossing live", "road staying beside", "road still beside", "road still riding to her right"),
        "pressure": ("shorter step", "brace", "tight", "close", "smaller", "compress", "yellow tactile line close", "edge geometry close"),
        "handoff": ("beyond", "through", "clear", "pass", "carries the next", "hands the route", "following beat", "next stride", "next step", "route forward", "immediate passage", "already formed", "already committed", "keeps close to", "same crossing stride carries forward", "traffic opening", "right edge", "open road held", "road still held beside", "road clearly beside", "curb held under", "road to her right", "road clearly to her right"),
        "payoff": ("far side", "opens", "release", "wider", "drive forward", "final", "far curb", "full release", "widest", "moves away", "open street surrounding"),
        "reflection": ("looks back", "over one shoulder", "turns back"),
    }
    wanted = mapping.get(story_function, ())
    return bool(wanted) and any(token in text for token in wanted)


def _matches_prompt_shape(shape: str, start: str, end: str, surface: str, action: str, trace: str) -> bool:
    text = f"{start} {end}"
    if shape == "compact_natural_prose":
        return bool(surface) and bool(action)
    if shape == "surface_first_crossing":
        return bool(surface) and any(token in text for token in ("cross", "clear", "beyond", "far side"))
    if shape == "geometry_first_directional_step":
        has_surface = any(token in surface for token in ("platform", "edge", "yellow", "tactile"))
        has_step = any(token in action or token in text for token in ("crossing step", "shorter step", "next step", "longer step"))
        return has_surface and has_step
    return bool(surface) and bool(action)


def _matches_ref_archetype(archetype: str, surface: str, action: str, continuity: str, trace: str) -> bool:
    text = f"{surface} {action} {continuity} {trace}"
    if archetype == "threshold_crossing":
        return any(token in text for token in ("threshold", "exit line", "street edge", "clear", "cross", "beyond", "far side"))
    if archetype == "stair_descent":
        return any(token in text for token in ("stairs", "stairwell", "handrail", "step", "lower"))
    if archetype == "passage_compression":
        return any(token in text for token in ("passage", "wall", "close", "rail", "lane", "tightens"))
    if archetype == "platform_edge":
        has_surface = any(token in text for token in ("platform edge", "yellow line", "yellow tactile line", "wet platform", "platform"))
        has_motion = any(token in text for token in ("crossing step", "shorter step", "next step", "longer step", "step along", "keeps moving", "drive forward"))
        return has_surface and has_motion
    if archetype == "gate_pass":
        return any(token in text for token in ("gate", "turnstile", "gate line", "turnstile lane", "inside the station", "beyond"))
    if archetype == "window_contact":
        return any(token in text for token in ("window", "glass", "shoulder", "touch", "trace", "press", "brush"))
    if archetype == "curb_crossing":
        return any(token in text for token in ("crosswalk", "curb", "far curb", "steps in from", "keeps close to", "moves away", "right edge", "middle-right side"))
    if archetype == "sidewalk_continuation":
        return any(token in text for token in ("sidewalk", "station-side sidewalk", "wet sidewalk", "wet sidewalk edge", "sidewalk edge", "pavement edge", "curb line", "pavement", "street edge", "path", "moves forward", "keeps moving", "moves along", "keeps running", "road beside", "road to her right", "road clearly to her right", "road still riding to her right"))
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
    return bool(archetype)
