from __future__ import annotations

from ai_mv.core.visual_pipeline_settings import visual_pipeline_settings


def build_section_semantics(config: dict, sections: list[dict]) -> list[dict]:
    settings = visual_pipeline_settings(config)
    out: list[dict] = []
    for row in sections:
        section_name = str(row.get("name", "section")).strip().lower()
        section_label = str(row.get("label", row.get("name", "section"))).strip()
        out.append(
            {
                "section_name": section_name,
                "section_label": section_label,
                "energy_phase": _energy_phase(section_name, section_label),
                "release_level": _release_level(section_name, section_label),
                "hook_priority": _hook_priority(section_name, section_label),
                "movement_bias": _movement_bias(settings["mv_grammar"], section_name, section_label),
                "return_weight": _return_weight(section_name, section_label),
                "hero_frame_priority": _hero_frame_priority(section_name, section_label),
            }
        )
    return out


def section_semantics_digest(audio_map: dict, limit: int = 12) -> str:
    rows = audio_map.get("section_semantics", []) if isinstance(audio_map, dict) else []
    out: list[str] = []
    for row in rows[: max(1, limit)]:
        if not isinstance(row, dict):
            continue
        out.append(
            f"{row.get('section_label', row.get('section_name', 'section'))}|"
            f"{row.get('mv_function', row.get('movement_bias', ''))}|"
            f"{row.get('release_level', '')}|"
            f"{row.get('hero_frame_priority', '')}"
        )
    return ", ".join(x for x in out if x)


def attach_tti_metadata(shot: dict, section_name: str, section_label: str) -> dict:
    item = dict(shot)
    mv_function = _mv_function(section_name, section_label)
    hero_frame_score = _hero_frame_score(section_name, section_label, str(item.get("shot_type", "")))
    shot_priority = _shot_priority(mv_function, hero_frame_score)
    item["hero_frame_score"] = hero_frame_score
    item["consistency_need"] = _consistency_need(hero_frame_score, str(item.get("shot_type", "")))
    item["mv_function"] = mv_function
    item["return_weight"] = _return_weight(section_name, section_label)
    item["edit_density"] = _edit_density(mv_function)
    item["shot_priority"] = shot_priority
    item["transition_role"] = _transition_role(mv_function, shot_priority)
    return item


def _energy_phase(section_name: str, section_label: str) -> str:
    sec = str(section_name).strip().lower()
    label = str(section_label).strip().lower()
    if "final chorus" in label:
        return "arrival"
    mapping = {
        "intro": "set",
        "verse_1": "contained",
        "verse_2": "contained",
        "pre_chorus": "lift",
        "chorus": "release",
        "post_chorus": "echo",
        "bridge": "break",
        "outro": "settle",
    }
    return mapping.get(sec, "contained")


def _release_level(section_name: str, section_label: str) -> str:
    sec = str(section_name).strip().lower()
    label = str(section_label).strip().lower()
    if "final chorus" in label:
        return "peak"
    if "chorus 2" in label:
        return "high"
    if sec == "chorus":
        return "high"
    if sec == "pre_chorus":
        return "medium"
    if sec == "bridge":
        return "withheld"
    if sec == "outro":
        return "settled"
    return "low"


def _hook_priority(section_name: str, section_label: str) -> str:
    sec = str(section_name).strip().lower()
    label = str(section_label).strip().lower()
    if "final chorus" in label:
        return "peak"
    if sec == "chorus":
        return "high"
    if sec == "pre_chorus":
        return "medium"
    return "low"


def _movement_bias(grammar: dict, section_name: str, section_label: str) -> str:
    sec = str(section_name).strip().lower()
    label = str(section_label).strip().lower()
    if "final chorus" in label or sec == "chorus":
        return str(grammar.get("chorus_payoff_bias", "")).strip()
    if sec == "bridge":
        return str(grammar.get("bridge_interrupt_bias", "")).strip()
    if sec == "outro":
        return str(grammar.get("outro_residue_bias", "")).strip()
    return str(grammar.get("verse_coverage_bias", "")).strip()


def _hero_frame_priority(section_name: str, section_label: str) -> str:
    sec = str(section_name).strip().lower()
    label = str(section_label).strip().lower()
    if "final chorus" in label:
        return "peak"
    if sec == "chorus":
        return "high"
    if sec == "pre_chorus":
        return "medium"
    if sec == "bridge":
        return "medium"
    return "low"


def _return_weight(section_name: str, section_label: str) -> int:
    sec = str(section_name).strip().lower()
    label = str(section_label).strip().lower()
    if "final chorus" in label:
        return 4
    if "chorus 2" in label:
        return 3
    if sec == "chorus":
        return 2
    if sec == "bridge":
        return 2
    return 1


def _mv_function(section_name: str, section_label: str) -> str:
    sec = str(section_name).strip().lower()
    label = str(section_label).strip().lower()
    if sec == "intro":
        return "establish"
    if sec in {"verse_1", "verse_2"}:
        return "coverage"
    if sec == "pre_chorus":
        return "lift"
    if sec == "chorus" and "final chorus" in label:
        return "payoff"
    if sec == "chorus":
        return "payoff"
    if sec == "bridge":
        return "interrupt"
    if sec == "outro":
        return "residue"
    return "coverage"


def _hero_frame_score(section_name: str, section_label: str, shot_type: str) -> int:
    sec = str(section_name).strip().lower()
    label = str(section_label).strip().lower()
    shot = str(shot_type).strip().upper()
    score = 1
    if shot == "EMOTION_CLOSE":
        score += 2
    elif shot == "CHAR_MASTER":
        score += 1
    elif shot in {"SYMBOLIC_INSERT", "GRAPHIC_EVENT", "WORLD_EVENT", "TRANSITIONAL_ABSTRACT", "RHYTHM_DETAIL"}:
        score -= 1
    if sec == "pre_chorus":
        score += 1
    if sec == "chorus":
        score += 1
    if "final chorus" in label:
        score += 1
    return max(1, min(5, score))


def _consistency_need(hero_frame_score: int, shot_type: str) -> str:
    shot = str(shot_type).strip().upper()
    if hero_frame_score >= 4 or shot == "EMOTION_CLOSE":
        return "high"
    if hero_frame_score >= 3 or shot == "CHAR_MASTER":
        return "normal"
    return "low"


def _edit_density(mv_function: str) -> str:
    mapping = {
        "establish": "low",
        "coverage": "medium",
        "lift": "medium",
        "payoff": "high",
        "interrupt": "sparse",
        "residue": "low",
    }
    return mapping.get(str(mv_function).strip().lower(), "medium")


def _shot_priority(mv_function: str, hero_frame_score: int) -> str:
    fn = str(mv_function).strip().lower()
    if fn == "payoff" and hero_frame_score >= 3:
        return "hero"
    if fn in {"interrupt", "lift"} and hero_frame_score >= 3:
        return "accent"
    if fn in {"establish", "residue"}:
        return "anchor"
    return "support"


def _transition_role(mv_function: str, shot_priority: str) -> str:
    fn = str(mv_function).strip().lower()
    pri = str(shot_priority).strip().lower()
    if fn == "establish":
        return "entry"
    if fn == "residue":
        return "exit"
    if fn == "interrupt":
        return "break"
    if pri == "hero":
        return "arrival"
    if fn == "lift":
        return "build"
    return "carry"
