from __future__ import annotations

from ai_mv.core.orchestration.bootstrap_guard import apply_input_defaults, validate_sizes, validate_templates
from ai_mv.core.orchestration.config_defaults import apply_defaults, default_config
from ai_mv.core.orchestration.pipeline import run_pipeline
from ai_mv.core.orchestration.runtime_overrides import apply_runtime_overrides

DEFAULT_CONCEPT_TEXT = "late-night city walk under wet neon lights with one protagonist moving through the same boulevard world"
DEFAULT_AUDIO_BRIEF = (
    "Short-form Korean city-pop song with one protagonist moving through the same rain-slick neon boulevard world, "
    "restrained verse detail, a tightening pre-chorus, and a chorus that feels emotionally continuous rather than scene-switching."
)
DEFAULT_HOOK_BRIEF = (
    "Give the chorus a short title-worthy Korean hook about the same wet city lights and moving forward after midnight. "
    "Keep it concise and singable."
)
DEFAULT_LANGUAGE = "ko"
DEFAULT_GENRE_HEAD = "city pop"
DEFAULT_TARGET_DURATION_SEC = 18
DEFAULT_CONTINUITY_MODE = "strict"
DEFAULT_STYLE_NAME = "citypop"



def build_fresh_validation_config(
    *,
    concept_text: str = DEFAULT_CONCEPT_TEXT,
    audio_brief: str = DEFAULT_AUDIO_BRIEF,
    hook_brief: str = DEFAULT_HOOK_BRIEF,
    language: str = DEFAULT_LANGUAGE,
    genre_head: str = DEFAULT_GENRE_HEAD,
    target_duration_sec: int = DEFAULT_TARGET_DURATION_SEC,
    continuity_mode: str = DEFAULT_CONTINUITY_MODE,
    default_style_name: str = DEFAULT_STYLE_NAME,
) -> dict:
    cfg = default_config()
    cfg["concept_text"] = str(concept_text).strip()
    cfg.setdefault("audio", {})
    cfg["audio"]["brief"] = str(audio_brief).strip()
    cfg["audio"]["hook_brief"] = str(hook_brief).strip()
    cfg["audio"]["language"] = str(language).strip()
    cfg["audio"]["genre_head"] = str(genre_head).strip()
    cfg["audio"]["target_duration_sec"] = int(target_duration_sec or DEFAULT_TARGET_DURATION_SEC)
    cfg.setdefault("planning", {})
    cfg["planning"]["continuity_mode"] = str(continuity_mode).strip()
    cfg["planning"]["default_style_name"] = str(default_style_name).strip()
    return cfg



def prepare_fresh_validation_config(**kwargs) -> dict:
    cfg = build_fresh_validation_config(**kwargs)
    apply_defaults(cfg)
    apply_runtime_overrides(cfg)
    apply_input_defaults(cfg)
    validate_sizes(cfg)
    validate_templates(cfg)
    return cfg



def run_fresh_validation(*, run_id: str, allow_existing_run: bool = True, **kwargs) -> str:
    cfg = prepare_fresh_validation_config(**kwargs)
    return run_pipeline(cfg, run_id=run_id, allow_existing_run=allow_existing_run)
