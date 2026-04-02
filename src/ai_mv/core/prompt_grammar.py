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
        raise RuntimeError(f"missing prompt grammar file: {path.as_posix()}")
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise RuntimeError(f"invalid prompt grammar file: {path.as_posix()}")
    return raw


def load_ref_archetype_grammars() -> dict:
    return load_prompt_grammar("ref_archetypes")


def load_tti_grammars() -> dict:
    return load_prompt_grammar("tti_grammars")


def load_wan_grammars() -> dict:
    return load_prompt_grammar("wan_grammars")


def ref_archetype_grammar(name: str) -> dict:
    raw = load_ref_archetype_grammars().get("archetypes", {})
    if not isinstance(raw, dict):
        return {}
    node = raw.get(str(name).strip(), {})
    return dict(node) if isinstance(node, dict) else {}


def ref_archetype_variant(archetype: str, variant: str) -> dict:
    base = ref_archetype_grammar(archetype)
    variants = base.get("variant_notes", {})
    if not isinstance(variants, dict):
        return {}
    node = variants.get(str(variant).strip(), {})
    return dict(node) if isinstance(node, dict) else {}


def tti_anchor_families() -> list[dict]:
    rows = load_tti_grammars().get("anchor_families", [])
    return [dict(row) for row in rows if isinstance(row, dict)]


def wan_transition_families() -> list[dict]:
    rows = load_wan_grammars().get("transition_families", [])
    return [dict(row) for row in rows if isinstance(row, dict)]


def wan_transition_family(name: str) -> dict:
    for row in wan_transition_families():
        if str(row.get("name", "")).strip() == str(name).strip():
            return row
    return {}
