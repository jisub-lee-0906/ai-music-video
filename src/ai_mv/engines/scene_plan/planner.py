from __future__ import annotations

from ai_mv.core.contracts.visual_plan_normalize import normalize_scene_outline
from ai_mv.core.director_brief import build_director_brief_intent


def build_scene_outline(config: dict, payload: dict) -> dict:
    brief = build_director_brief_intent(config)
    timeline = payload["lyrics_timeline"]
    sections = [row for row in timeline.get("sections", []) if isinstance(row, dict)]
    shot_packages: list[dict] = []
    section_progression: list[dict] = []
    for section_index, section in enumerate(sections, start=1):
        section_name = str(section.get("section_name", "")).strip()
        section_label = str(section.get("section_label", section_name)).strip() or section_name or f"Section {section_index}"
        story_goal = _story_goal(brief, section_label, section_name)
        world_zone = _world_zone_for_section(section_label, section_index)
        line_map = {
            int(row.get("line_index", 0)): str(row.get("text", "")).strip()
            for row in section.get("lines", [])
            if isinstance(row, dict) and int(row.get("line_index", 0)) > 0 and str(row.get("text", "")).strip()
        }
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
            base_story_function = _story_function(section_label, beat_index, len(beats))
            base_story_event = _story_event(brief, section_label, beat, story_goal, base_story_function)
            for segment in _beat_segments(config, beat, base_story_function):
                story_function = _segment_story_function(base_story_function, segment["segment_index"], segment["segment_count"])
                story_event = _segment_story_event(base_story_event, segment["segment_index"], segment["segment_count"])
                transition_need = _transition_need(story_function)
                performer_state = _performer_state(section_label, story_function, story_event)
                shot_packages.append(
                    {
                        "shot_id": _segment_shot_id(beat_id, segment["segment_index"], segment["segment_count"]),
                        "section_name": section_name,
                        "section_label": section_label,
                        "beat_refs": [beat_id],
                        "line_refs": [int(x) for x in beat.get("line_refs", []) if int(x) > 0],
                        "lyric_lines": [line_map.get(int(x), "") for x in beat.get("line_refs", []) if int(x) in line_map],
                        "literal_image": str(beat.get("literal_image", "")).strip(),
                        "visible_action": str(beat.get("visible_action", "")).strip(),
                        "emotional_turn": str(beat.get("emotional_turn", "")).strip(),
                        "continuity_anchor": str(beat.get("continuity_anchor", "")).strip(),
                        "payoff_role": str(beat.get("payoff_role", "")).strip(),
                        "story_function": story_function,
                        "story_goal": story_goal,
                        "story_event": story_event,
                        "world_zone": world_zone,
                        "performer_state": performer_state,
                        "story_visual_intent": _story_visual_intent(section_label, story_function, world_zone, story_event),
                        "transition_need": transition_need,
                        "duration_sec": segment["duration_sec"],
                        "why": _why_line(section_label, story_function, story_goal, story_event),
                        "segment_index": segment["segment_index"],
                        "segment_count": segment["segment_count"],
                        "start_sec": segment["start_sec"],
                        "end_sec": segment["end_sec"],
                    }
                )
    return normalize_scene_outline(
        {
            "brief_name": brief["brief_name"],
            "story_premise": brief["story_premise"],
            "world_rules": brief["world_rules"],
            "performer_arc": brief["performer_arc"],
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
        "Use lyrics as the source of what is happening now. "
        "Use the profile only as world context for connected places and carry-over props. "
        "For each lyric beat, decide only story function, story goal, world zone, performer state, and transition need. "
        "Do not create final prompt prose."
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
        return "entry_zone"
    if "pre" in low:
        return "transition_edge"
    if "bridge" in low:
        return "compression"
    if "final chorus" in low:
        return "open_peak"
    if "chorus" in low:
        return "open_route"
    if "outro" in low:
        return "residue"
    return "narrow_route" if section_index <= 2 else "transit_route"


def _performer_state(section_label: str, story_function: str, story_event: str) -> str:
    if story_event:
        return story_event
    base = {
        "entry": "commits to the route",
        "continuation": "keeps moving through the same world",
        "pressure": "tightens the movement without fully stopping",
        "handoff": "reaches a readable next state for the following shot",
        "payoff": "crosses into a wider forward release",
    }
    if "bridge" in section_label.lower() and story_function == "pressure":
        return "tightens the route and regains direction"
    return base.get(story_function, "keeps moving through the same world")


def _story_visual_intent(section_label: str, story_function: str, world_zone: str, story_event: str) -> str:
    low = section_label.lower()
    if story_function == "entry":
        if "intro" in low or world_zone == "entry_zone":
            return f"Show the first committed boundary crossing that makes the connected world physically real. Event: {story_event}".strip()
        if world_zone in {"open_route", "open_peak"}:
            return f"Show forward release beginning in a space that has already opened wider. Event: {story_event}".strip()
        return f"Show the first committed move into the route without flattening into generic walking. Event: {story_event}".strip()
    if story_function == "continuation":
        return f"Show the same route carrying forward without resetting the performer or the world. Event: {story_event}".strip()
    if story_function == "pressure":
        return f"Show a tightened route and a shorter physical progression without fully stopping. Event: {story_event}".strip()
    if story_function == "handoff":
        if world_zone in {"entry_zone", "transition_edge"}:
            return f"Show the next state already committed beyond the transition before the cut. Event: {story_event}".strip()
        return f"Show the next state already formed so the following shot feels physically inevitable. Event: {story_event}".strip()
    if story_function == "payoff":
        if "final chorus" in low or world_zone == "open_peak":
            return f"Show the widest forward release with unmistakable arrival and larger directional commitment. Event: {story_event}".strip()
        return f"Show a decisive forward release rather than another neutral continuation. Event: {story_event}".strip()
    return f"Keep the performer moving through one connected world with a readable physical change. Event: {story_event}".strip()


def _why_line(section_label: str, story_function: str, story_goal: str, story_event: str) -> str:
    return f"{section_label} uses a {story_function} beat to serve: {story_goal} Event: {story_event}".strip()


def _story_event(brief: dict, section_label: str, beat: dict, story_goal: str, story_function: str) -> str:
    visible_action = str(beat.get("visible_action", "")).strip()
    literal_image = str(beat.get("literal_image", "")).strip()
    emotional_turn = str(beat.get("emotional_turn", "")).strip()
    continuity_anchor = str(beat.get("continuity_anchor", "")).strip()
    if visible_action:
        return visible_action
    if literal_image and emotional_turn:
        return f"{literal_image}. {emotional_turn}"
    if literal_image:
        return literal_image
    if continuity_anchor:
        return continuity_anchor
    fallback = {
        "entry": "The performer commits to the next readable beat in the same world.",
        "continuation": "The performer carries the same visual thread forward without resetting.",
        "pressure": "The performer tightens the motion without fully stopping.",
        "handoff": "The performer lands in the next state before the cut.",
        "payoff": "The performer opens into the clearest release beat.",
    }
    role = fallback.get(story_function, "The performer continues through the same connected world.")
    return f"{role} {story_goal}".strip()


def _story_goal(brief: dict, section_label: str, section_name: str) -> str:
    roles = brief.get("section_story_roles", {})
    return str(roles.get(section_label, roles.get(section_name, ""))).strip()


def _duration(beat: dict) -> float:
    start = float(beat.get("start_sec", 0.0) or 0.0)
    end = float(beat.get("end_sec", 0.0) or 0.0)
    return max(0.5, end - start) if end > start else 2.0


def _beat_segments(config: dict, beat: dict, story_function: str) -> list[dict]:
    duration = _duration(beat)
    render = config.get("render", {}) if isinstance(config, dict) else {}
    wan_safe = float(render.get("wan_safe_max_gap_sec", 4.0) or 4.0)
    target = max(2.0, min(wan_safe, 4.0 if story_function in {"continuation", "handoff"} else 3.5))
    count = max(1, int(-(-duration // target)))
    start = float(beat.get("start_sec", 0.0) or 0.0)
    segment_span = duration / float(count)
    out: list[dict] = []
    for idx in range(count):
        seg_start = round(start + segment_span * idx, 3)
        seg_end = round(start + segment_span * (idx + 1), 3)
        out.append(
            {
                "segment_index": idx + 1,
                "segment_count": count,
                "duration_sec": round(max(0.5, seg_end - seg_start), 3),
                "start_sec": seg_start,
                "end_sec": seg_end,
            }
        )
    return out


def _segment_story_function(base: str, segment_index: int, segment_count: int) -> str:
    if segment_count <= 1:
        return base
    if segment_index == 1:
        return "entry" if base == "entry" else "continuation"
    if segment_index == segment_count:
        return base
    return "continuation"


def _segment_story_event(base_event: str, segment_index: int, segment_count: int) -> str:
    if segment_count <= 1:
        return base_event
    if segment_index == 1:
        return f"{base_event} The moment begins here and sets the route."
    if segment_index == segment_count:
        return f"{base_event} The moment lands in a clear next state."
    return f"{base_event} The route keeps carrying through the same connected movement."


def _segment_shot_id(beat_id: str, segment_index: int, segment_count: int) -> str:
    if segment_count <= 1:
        return beat_id
    return f"{beat_id}_s{segment_index}"
