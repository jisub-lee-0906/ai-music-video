from __future__ import annotations

from ai_mv.core.contracts.stage_io import StageInput, StageOutput
from ai_mv.core.stages.payload_views import merge_planner_prompt
from ai_mv.utils.text_utils import parse_target


def run_shot_density_refiner(stage_input: StageInput) -> StageOutput:
    plan = build_wan_safe_scene_outline(stage_input.config, stage_input.payload)
    return StageOutput("shot_density_refiner", "done", _build_payload(stage_input.payload, plan, stage_input.config), [])


def build_shot_density_refiner_preview_payload(config: dict, payload: dict) -> dict:
    plan = build_wan_safe_scene_outline(config, payload)
    return _build_payload(payload, plan, config)


def _build_payload(payload: dict, plan: dict, config: dict) -> dict:
    workflow_inputs = dict(payload.get("workflow_inputs", {}))
    workflow_inputs["shot_density_refiner"] = {
        "max_gap_sec": _max_gap_sec(config),
        "shot_packages": list(plan.get("shot_packages", [])),
    }
    return {
        "wan_safe_scene_outline": plan,
        "workflow_inputs": workflow_inputs,
        "planner_prompts": merge_planner_prompt(
            payload,
            "shot_density_refiner",
            {
                "prompt": (
                    "Split long scene-outline shots into WAN-safe sub-shots while preserving the parent event family, "
                    "world zone, and story goal. Keep every adjacent REF gap at or below the WAN-safe duration cap."
                )
            },
        ),
    }


def build_wan_safe_scene_outline(config: dict, payload: dict) -> dict:
    outline = dict(payload.get("scene_outline", {}))
    shots = [dict(row) for row in outline.get("shot_packages", []) if isinstance(row, dict)]
    if not shots:
        return outline
    dense: list[dict] = []
    max_gap = _max_gap_sec(config)
    for shot in shots:
        dense.extend(_split_shot(shot, max_gap))
    out = dict(outline)
    out["shot_packages"] = dense
    return out


def _split_shot(shot: dict, max_gap_sec: float) -> list[dict]:
    duration = float(shot.get("duration_sec", 2.0) or 2.0)
    count = max(1, int(-(-duration // max_gap_sec)))
    if count <= 1:
        return [dict(shot)]
    family = _event_family(shot)
    functions = _micro_functions(str(shot.get("story_function", "")).strip(), count)
    out: list[dict] = []
    for index in range(count):
        current = dict(shot)
        event = _micro_event_step(family, functions[index], index, count)
        current["shot_id"] = f"{str(shot.get('shot_id', '')).strip()}_S{index + 1:02d}"
        current["story_event"] = event
        current["story_function"] = functions[index]
        current["heroine_state"] = event
        current["duration_sec"] = round(duration / float(count), 3)
        current["why"] = (
            f"{shot.get('why', '')} WAN-safe split {index + 1}/{count} inside the same {family} family."
        ).strip()
        current["story_visual_intent"] = _story_visual_intent_step(str(shot.get("story_visual_intent", "")).strip(), family, index, count)
        current["transition_need"] = _transition_need_step(functions[index], family, index, count)
        out.append(current)
    return out


def _max_gap_sec(config: dict) -> float:
    render = config.get("render", {}) if isinstance(config, dict) else {}
    raw = render.get("wan_safe_max_gap_sec", 4.0) if isinstance(render, dict) else 4.0
    try:
        value = float(raw)
    except Exception:
        value = 4.0
    return max(1.0, min(4.0, value))


def _event_family(shot: dict) -> str:
    event = str(shot.get("story_event", "")).lower()
    zone = str(shot.get("world_zone", "")).lower()
    if any(token in event for token in ("window", "glass", "palm", "metal edge", "rail")):
        return "window_contact"
    if any(token in event for token in ("bench", "seat", "sit", "rise")):
        return "bench_rest"
    if "threshold" in event or "gate" in event or zone == "edge":
        return "threshold_crossing"
    if "platform" in event or zone == "compression":
        return "platform_edge"
    if "crossing" in event or "crosswalk" in event or zone in {"open_route", "open_peak"}:
        return "curb_crossing"
    return "sidewalk_continuation"


def _micro_functions(parent_function: str, count: int) -> list[str]:
    parent = str(parent_function).strip()
    if count <= 1:
        return [parent or "continuation"]
    if parent == "entry":
        return ["entry"] + ["continuation"] * max(0, count - 2) + ["handoff"]
    if parent == "handoff":
        return ["continuation"] * max(0, count - 1) + ["handoff"]
    if parent == "payoff":
        return ["continuation"] * max(0, count - 1) + ["payoff"]
    if parent == "pressure":
        return ["pressure"] * max(1, count - 1) + ["handoff"]
    return ["continuation"] * count


def _micro_event_step(family: str, story_function: str, index: int, count: int) -> str:
    templates = {
        ("window_contact", "entry"): [
            "She keeps one empty palm on the station window and steadies her breath without fully stopping.",
            "She softens the empty-palm contact on the station window while the next commitment gathers.",
            "She lets the empty palm leave the station window and keeps the threshold commitment ready.",
        ],
        ("window_contact", "continuation"): [
            "She keeps close to the station window with one empty palm resting on the lower rail as she moves past it.",
            "She keeps the empty palm on the station window rail while the forward carry stays alive.",
            "She lets the empty palm lift from the station window rail and keeps moving past the edge.",
        ],
        ("window_contact", "handoff"): [
            "She keeps close to the station window with one empty palm resting on the lower rail as the next step gathers.",
            "She lets the empty palm lift from the station window rail and leaves the next step already forming.",
        ],
        ("bench_rest", "entry"): [
            "She reaches the wet bench seat and sits with one foot still planted on the ground.",
            "She holds one compressed seated beat on the wet bench seat with one foot still planted.",
            "She stays on the wet bench seat with one foot planted and the route still waiting in front of her.",
        ],
        ("bench_rest", "continuation"): [
            "She holds one compressed seated beat on the wet bench seat with one foot still planted.",
            "She keeps the compressed seat on the wet bench seat with one foot still planted to rise again.",
            "She leans forward from the wet bench seat with one foot still planted as the rise gathers.",
        ],
        ("bench_rest", "handoff"): [
            "She leans forward from the wet bench seat with one foot still planted as the rise gathers.",
            "She tips away from the wet bench seat and leaves the rise already forming.",
        ],
        ("bench_rest", "pressure"): [
            "She sits on the wet bench seat for one compressed beat with one foot still planted on the ground.",
            "She holds the compressed seat on the wet bench seat and keeps the rise possible.",
            "She leans forward from the wet bench seat with one foot still planted as the release gathers.",
        ],
        ("threshold_crossing", "entry"): [
            "She approaches the station threshold and keeps the opening directly in front of her.",
            "She sets one committed step through the station threshold into the wet passage.",
            "She leaves the station threshold behind and keeps the next step moving inside the wet passage.",
        ],
        ("threshold_crossing", "continuation"): [
            "She keeps one committed step moving through the station threshold into the wet passage.",
            "She carries the threshold crossing one beat farther into the wet passage.",
            "She keeps the next step already moving beyond the station threshold inside the wet passage.",
        ],
        ("threshold_crossing", "handoff"): [
            "She clears the station threshold into the wet passage with the next step already committed beyond it.",
            "She leaves the station threshold behind and keeps the next step moving inside the wet passage.",
        ],
        ("platform_edge", "pressure"): [
            "She shortens one step along the wet platform edge with the yellow tactile line close at her feet.",
            "She keeps one compressed beat on the wet platform edge with the yellow tactile line still close at her feet.",
            "She takes the next longer step along the wet platform edge while the track still runs beside her.",
        ],
        ("curb_crossing", "entry"): [
            "She enters the wet crosswalk from the left side and opens the crossing in front of her.",
            "She carries the crossing through the middle of the wet crosswalk without falling back to center.",
            "She keeps the crossing near the right edge of the wet crosswalk with the open road held to her left.",
        ],
        ("curb_crossing", "continuation"): [
            "She carries the crossing through the middle of the wet crosswalk without falling back to center.",
            "She keeps the crossing through the middle-right side of the wet crosswalk without falling back to center.",
            "She keeps the crossing near the right edge of the wet crosswalk with the open road held to her left.",
        ],
        ("curb_crossing", "handoff"): [
            "She keeps the crossing near the right edge of the wet crosswalk with the open road held to her left.",
            "She leaves the next crossing state already formed at the right edge of the wet crosswalk.",
        ],
        ("curb_crossing", "payoff"): [
            "She leaves the wet crosswalk behind and lets the wider street open around her.",
            "She keeps moving away from the wet crosswalk as the wider street opens around her.",
        ],
        ("sidewalk_continuation", "entry"): [
            "She takes the next committed stride along the wet sidewalk edge with the road still beside her.",
            "She keeps the same sidewalk-side carry alive one beat farther along the wet sidewalk edge.",
            "She leaves the next sidewalk-side stride already formed with the road still riding beside her.",
        ],
        ("sidewalk_continuation", "continuation"): [
            "She keeps the same sidewalk-side carry alive one beat farther along the wet sidewalk edge.",
            "She carries the same stride one beat farther along the wet sidewalk edge with the road still beside her.",
            "She leaves the next sidewalk-side stride already formed with the road still riding beside her.",
        ],
        ("sidewalk_continuation", "handoff"): [
            "She sets the next sidewalk-side stride along the wet sidewalk edge with the road clearly to her right.",
            "She leaves the next sidewalk-side stride already formed with the road still riding beside her.",
        ],
    }
    fallback = templates[("sidewalk_continuation", "continuation")]
    base = list(templates.get((family, story_function), templates.get((family, "continuation"), fallback)))
    if count <= 1:
        return base[min(1, len(base) - 1)]
    idx = min(len(base) - 1, int(round(index * (len(base) - 1) / float(max(1, count - 1)))))
    return base[idx]


def _story_visual_intent_step(base: str, family: str, index: int, count: int) -> str:
    prefix = f"{family} micro-step {index + 1}/{count}."
    return f"{prefix} {base}".strip()


def _transition_need_step(story_function: str, family: str, index: int, count: int) -> str:
    if story_function == "entry":
        return f"start the {family} progression"
    if story_function == "handoff":
        return f"leave the {family} next-state already formed"
    if story_function == "payoff":
        return f"land the {family} release"
    if story_function == "pressure":
        return f"hold the {family} compression without stopping"
    return f"carry the {family} progression forward"
