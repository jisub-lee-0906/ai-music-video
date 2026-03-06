from __future__ import annotations

import hashlib

from ai_mv.core.contracts.errors import PipelineError
from ai_mv.utils.path_utils import resolve_project_path
from ai_mv.utils.text_utils import ensure_16_9, parse_size, parse_target


def apply_profile(config: dict) -> None:
    name = str(config["profile"]).strip()
    if not name:
        return
    fname = name if name.endswith(".yaml") else f"{name}.yaml"
    path = resolve_project_path(f"configs/profiles/{fname}")
    if not path.exists():
        raise PipelineError(f"missing profile config: {path.as_posix()}")
    import yaml

    profile = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(profile, dict):
        raise PipelineError(f"invalid profile config: {path.as_posix()}")
    _deep_merge(config, profile)
    config["profile"] = name


def validate_sizes(config: dict) -> None:
    w, h, _ = parse_target(config["video"]["target"])
    ensure_16_9(w, h)
    for key in ("tti_size", "uso_size", "wan_size"):
        rw, rh = parse_size(str(config["render"][key]))
        ensure_16_9(rw, rh)


def validate_templates(config: dict) -> None:
    wf = resolve_project_path(str(config["integrations"]["workflows_dir"]))
    fixed = [
        "audio_ace_step_1_5_tta.api.json",
        "image_flux1_dev_tti.api.json",
        "image_flux1_dev_uso.api.json",
        "video_wan_2_2_flf2v.api.json",
    ]
    for name in fixed:
        if not (wf / name).exists():
            raise PipelineError(f"missing workflow template: {name}")
    hashes = config["runtime"]["template_hashes"]
    if not bool(config["runtime"]["template_hash_lock"]):
        return
    if not isinstance(hashes, dict) or not hashes:
        raise PipelineError("template_hash_lock=true requires non-empty runtime.template_hashes")
    for name, expected in hashes.items():
        p = wf / name
        actual = hashlib.sha256(p.read_bytes()).hexdigest()
        if str(expected) and actual != str(expected):
            raise PipelineError(f"template hash mismatch: {name}")


def _deep_merge(base: dict, patch: dict) -> None:
    for key, val in patch.items():
        if isinstance(val, dict) and isinstance(base.get(key), dict):
            _deep_merge(base[key], val)
        else:
            base[key] = val
