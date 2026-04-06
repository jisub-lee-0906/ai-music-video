from __future__ import annotations

from functools import lru_cache
from pathlib import Path

import yaml

from ai_mv.utils.path_utils import resolve_project_path


GRAMMAR_ROOT = resolve_project_path("config/prompt_grammar")


def grammar_file(name: str) -> Path:
    return GRAMMAR_ROOT / f"{name}.yaml"


@lru_cache(maxsize=None)
def load_prompt_grammar(name: str) -> dict:
    path = grammar_file(name)
    if not path.exists():
        return {}
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        return {}
    return raw


def load_ref_archetype_grammars() -> dict:
    return load_prompt_grammar("ref_archetypes")


def load_tti_families() -> dict:
    return load_prompt_grammar("tti_families")


def load_wan_transitions() -> dict:
    return load_prompt_grammar("wan_transitions")


def load_golden_structures() -> dict:
    return load_prompt_grammar("golden_structures")


def load_flux2_prompting() -> dict:
    return load_prompt_grammar("flux2_prompting")


def load_director_rules() -> dict:
    return load_prompt_grammar("director_rules")


def load_render_plan_rules() -> dict:
    return load_prompt_grammar("render_plan")


def load_render_verbalizer_rules() -> dict:
    return load_prompt_grammar("render_verbalizer")


def ref_archetype_grammar(name: str) -> dict:
    raw = load_ref_archetype_grammars().get("archetypes", {})
    if not isinstance(raw, dict):
        return {}
    node = raw.get(str(name).strip(), {})
    return dict(node) if isinstance(node, dict) else {}


def ref_archetype_variant(archetype: str, variant: str) -> dict:
    base = ref_archetype_grammar(archetype)
    variants = base.get("variants", {})
    if not isinstance(variants, dict):
        return {}
    node = variants.get(str(variant).strip(), {})
    return dict(node) if isinstance(node, dict) else {}


def tti_anchor_families() -> list[dict]:
    rows = load_tti_families().get("families", [])
    return [dict(row) for row in rows if isinstance(row, dict)]


def wan_transition_families() -> list[dict]:
    rows = load_wan_transitions().get("families", [])
    return [dict(row) for row in rows if isinstance(row, dict)]


def wan_transition_family(name: str) -> dict:
    for row in wan_transition_families():
        if str(row.get("name", "")).strip() == str(name).strip():
            return row
    return {}


def golden_structure_guidance(story_function: str, archetype: str, variant: str = "") -> dict:
    rows = load_golden_structures().get("structures", [])
    if not isinstance(rows, list):
        return {}
    wanted_story = str(story_function).strip()
    wanted_archetype = str(archetype).strip()
    wanted_variant = str(variant).strip()
    fallback: dict = {}
    for row in rows:
        if not isinstance(row, dict):
            continue
        if str(row.get("story_function", "")).strip() != wanted_story:
            continue
        if str(row.get("ref_archetype", "")).strip() != wanted_archetype:
            continue
        row_variant = str(row.get("variant", "")).strip()
        if row_variant and row_variant == wanted_variant:
            return dict(row)
        if not row_variant and not fallback:
            fallback = dict(row)
    return fallback
