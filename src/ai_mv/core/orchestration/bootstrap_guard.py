from __future__ import annotations

import hashlib

from ai_mv.core.contracts.errors import PipelineError
from ai_mv.core.workflow_names import WORKFLOW_FILES
from ai_mv.utils.bool_utils import parse_bool
from ai_mv.utils.text_utils import ensure_16_9, ensure_positive_size, parse_size, parse_target
from ai_mv.utils.path_utils import resolve_project_path

DEFAULT_CONCEPT = "emotionally resonant original song and music video concept with a distinct visual theme"


def apply_input_defaults(config: dict) -> None:
    concept_text = str(config.get("concept_text", "")).strip()
    if not concept_text:
        config["concept_text"] = DEFAULT_CONCEPT
    audio = config.get("audio", {}) if isinstance(config.get("audio", {}), dict) else {}
    if audio:
        config["audio"] = audio


def validate_sizes(config: dict) -> None:
    w, h, _ = parse_target(config["video"]["target"])
    ensure_16_9(w, h)
    for key in ("flux2_size", "ltx_i2v_size", "ltx_ia2v_size", "ltx_flf2v_size"):
        rw, rh = parse_size(str(config["render"][key]))
        ensure_positive_size(rw, rh)


def validate_templates(config: dict) -> None:
    wf = resolve_project_path(str(config["integrations"]["workflows_dir"]))
    for name in WORKFLOW_FILES:
        if not (wf / name).exists():
            raise PipelineError(f"missing workflow template: {name}")
    hashes = config["runtime"]["template_hashes"]
    if not parse_bool(config["runtime"]["template_hash_lock"], default=False):
        return
    if not isinstance(hashes, dict) or not hashes:
        raise PipelineError("template_hash_lock=true requires non-empty runtime.template_hashes")
    for name, expected in hashes.items():
        p = wf / name
        actual = hashlib.sha256(p.read_bytes()).hexdigest()
        if str(expected) and actual != str(expected):
            raise PipelineError(f"template hash mismatch: {name}")
