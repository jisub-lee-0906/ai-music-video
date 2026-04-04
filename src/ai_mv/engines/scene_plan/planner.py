from __future__ import annotations

from ai_mv.core.contracts.visual_plan_normalize import normalize_scene_outline
from ai_mv.core.director_brief import build_director_brief_intent


def build_scene_outline(config: dict, payload: dict) -> dict:
    brief = build_director_brief_intent(config)
    timeline = payload["lyrics_timeline"]
    sections = [row for row in timeline.get("sections", []) if isinstance(row, dict)]
    shot_packages: list[dict] = []
    section_progression: list[dict] = []
    event_scripts = brief.get("section_event_scripts", {})
    for section_index, section in enumerate(sections, start=1):
        section_name = str(section.get("section_name", "")).strip()
        section_label = str(section.get("section_label", section_name)).strip() or section_name or f"Section {section_index}"
        story_goal = brief["section_story_roles"].get(section_label, brief["section_story_roles"].get(section_name, ""))
        section_events = list(event_scripts.get(section_label, event_scripts.get(section_name, [])))
        world_zone = _world_zone_for_section(section_label, section_index)
        beats = [row for row in section.get("lyric_beats", []) if isinstance(row, dict)]
        section_progression.append(
            {
                "section_name": section_name,
                "section_label": section_label,
                "story_goal": story_goal,
                "world_zone": world_zone,
            }
        )
        for beat_index, beat in enumerate(beats, start=1):
            beat_id = str(beat.get("beat_id", "")).strip()
            if not beat_id:
                continue
            story_function = _story_function(section_label, beat_index, len(beats))
            story_event = _story_event(section_label, beat_index, beat_count=len(beats), section_events=section_events, story_function=story_function)
            transition_need = _transition_need(story_function)
            heroine_state = _heroine_state(section_label, story_function, story_event)
            shot_packages.append(
                {
                    "shot_id": beat_id,
                    "section_name": section_name,
                    "section_label": section_label,
                    "beat_refs": [beat_id],
                    "line_refs": [int(x) for x in beat.get("line_refs", []) if int(x) > 0],
                    "story_function": story_function,
                    "story_goal": story_goal,
                    "story_event": story_event,
                    "world_zone": world_zone,
                    "heroine_state": heroine_state,
                    "story_visual_intent": _story_visual_intent(section_label, story_function, world_zone, story_event),
                    "transition_need": transition_need,
                    "duration_sec": _duration(beat),
                    "why": _why_line(section_label, story_function, story_goal, story_event),
                }
            )
    return normalize_scene_outline(
        {
            "brief_name": brief["brief_name"],
            "story_premise": brief["story_premise"],
            "world_rules": brief["world_rules"],
            "heroine_arc": brief["heroine_arc"],
            "section_story_roles": brief["section_story_roles"],
            "shot_packages": shot_packages,
            "section_progression": section_progression,
        }
    )


def build_scene_plan(config: dict, payload: dict) -> dict:
    return build_scene_outline(config, payload)


def build_scene_outline_preview_prompt(config: dict, payload: dict) -> str:
    brief = build_director_brief_intent(config)
    return (
        "Create a story-only scene outline from the lyric timeline. "
        f"Story premise={brief['story_premise']}. "
        f"World rules={brief['world_rules']}. "
        "For each lyric beat, decide only the story function, story goal, world zone, heroine state, and transition need. "
        "Do not create prompt prose, environment anchors, motifs, or literal scene descriptions."
    )


def build_scene_plan_preview_prompt(config: dict, payload: dict) -> str:
    return build_scene_outline_preview_prompt(config, payload)


def _story_function(section_label: str, beat_index: int, beat_count: int) -> str:
    low = section_label.lower()
    if "bridge" in low:
        if beat_index == 1:
            return "pressure"
        if beat_index == beat_count:
            return "handoff"
        return "pressure"
    if beat_count <= 1:
        return "entry"
    if beat_index == 1:
        return "entry"
    if beat_index == beat_count:
        return "payoff" if "final chorus" in low else "handoff"
    if beat_index == beat_count - 1:
        return "handoff"
    return "continuation"


def _transition_need(story_function: str) -> str:
    mapping = {
        "entry": "set direction",
        "continuation": "carry motion forward",
        "pressure": "compress without stopping",
        "handoff": "end on a clear next state",
        "payoff": "land a decisive forward crossing",
    }
    return mapping.get(story_function, "carry motion forward")


def _world_zone_for_section(section_label: str, section_index: int) -> str:
    low = section_label.lower()
    if "intro" in low:
        return "threshold"
    if "pre" in low:
        return "edge"
    if "bridge" in low:
        return "compression"
    if "final chorus" in low:
        return "open_peak"
    if "chorus" in low:
        return "open_route"
    if "outro" in low:
        return "residue"
    return "narrow_route" if section_index <= 2 else "transit_route"


def _heroine_state(section_label: str, story_function: str, story_event: str) -> str:
    if story_event:
        return story_event
    base = {
        "entry": "commits to the route",
        "continuation": "keeps moving through the same world",
        "pressure": "tightens her movement without fully stopping",
        "handoff": "reaches a readable next state for the following shot",
        "payoff": "crosses into a wider forward release",
    }
    if "bridge" in section_label.lower() and story_function == "pressure":
        return "tightens her route and regains direction"
    return base.get(story_function, "keeps moving through the same world")


def _story_visual_intent(section_label: str, story_function: str, world_zone: str, story_event: str) -> str:
    low = section_label.lower()
    if story_function == "entry":
        if "intro" in low or world_zone == "threshold":
            return f"Show the first committed boundary crossing that makes the connected world physically real. Event: {story_event}".strip()
        if world_zone in {"open_route", "open_peak"}:
            return f"Show forward release beginning in a space that has already opened wider. Event: {story_event}".strip()
        return f"Show the first committed move into the route without flattening into generic walking. Event: {story_event}".strip()
    if story_function == "continuation":
        return f"Show the same route carrying forward without resetting the heroine or the world. Event: {story_event}".strip()
    if story_function == "pressure":
        return f"Show a tightened route and a shorter physical progression without fully stopping. Event: {story_event}".strip()
    if story_function == "handoff":
        if world_zone in {"threshold", "edge"}:
            return f"Show the next state already committed beyond the threshold before the cut. Event: {story_event}".strip()
        return f"Show the next state already formed so the following shot feels physically inevitable. Event: {story_event}".strip()
    if story_function == "payoff":
        if "final chorus" in low or world_zone == "open_peak":
            return f"Show the widest forward release with unmistakable arrival and larger directional commitment. Event: {story_event}".strip()
        return f"Show a decisive forward release rather than another neutral continuation. Event: {story_event}".strip()
    return f"Keep the heroine moving through one connected world with a readable physical change. Event: {story_event}".strip()


def _why_line(section_label: str, story_function: str, story_goal: str, story_event: str) -> str:
    return f"{section_label} uses a {story_function} beat to serve: {story_goal} Event: {story_event}".strip()


def _story_event(section_label: str, beat_index: int, beat_count: int, section_events: list[str], story_function: str) -> str:
    events = [str(x).strip() for x in section_events if str(x).strip()]
    if events:
        idx = min(max(beat_index - 1, 0), len(events) - 1)
        return events[idx]
    fallback = {
        "entry": "She commits to the next physical route.",
        "continuation": "She keeps the current route alive without resetting.",
        "pressure": "She compresses the route into a tighter physical beat.",
        "handoff": "She leaves the next state already formed before the cut.",
        "payoff": "She turns the route into a wider forward release.",
    }
    return fallback.get(story_function, f"{section_label} continues as a readable physical event.")


def _duration(beat: dict) -> float:
    start = float(beat.get("start_sec", 0.0) or 0.0)
    end = float(beat.get("end_sec", 0.0) or 0.0)
    return max(0.5, end - start) if end > start else 2.0
