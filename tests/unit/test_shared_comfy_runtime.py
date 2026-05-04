from __future__ import annotations

from ai_mv.core.orchestration.config_defaults import apply_defaults, default_config
import ai_mv.entrypoints.start as start_entry


def test_default_config_uses_shared_comfy_safe_runtime_defaults():
    cfg = default_config()

    assert cfg["runtime"]["interrupt_comfy_before_start"] is False
    assert cfg["runtime"]["clear_comfy_queue_before_start"] is False


def test_apply_defaults_backfills_shared_comfy_safe_runtime_defaults():
    cfg = {"runtime": {}}

    apply_defaults(cfg)

    assert cfg["runtime"]["interrupt_comfy_before_start"] is False
    assert cfg["runtime"]["clear_comfy_queue_before_start"] is False


def test_prepare_comfy_queue_does_not_interrupt_or_clear_by_default(monkeypatch):
    calls: list[tuple[str, str]] = []
    monkeypatch.setattr(start_entry, "interrupt_comfy", lambda url: calls.append(("interrupt", url)))
    monkeypatch.setattr(start_entry, "clear_comfy_queue", lambda url: calls.append(("clear", url)))
    monkeypatch.setattr(start_entry, "comfy_queue_counts", lambda _url: (0, 0))

    start_entry._prepare_comfy_queue({"integrations": {"comfyui_base_url": "http://127.0.0.1:8000"}})

    assert calls == []


def test_default_config_allows_explicit_exclusive_comfy_opt_in(monkeypatch):
    monkeypatch.setenv("AI_MV_INTERRUPT_COMFY_BEFORE_START", "1")
    monkeypatch.setenv("AI_MV_CLEAR_COMFY_QUEUE_BEFORE_START", "true")

    cfg = default_config()

    assert cfg["runtime"]["interrupt_comfy_before_start"] is True
    assert cfg["runtime"]["clear_comfy_queue_before_start"] is True


def test_default_config_allows_explicit_between_clip_cleanup_opt_in(monkeypatch):
    monkeypatch.setenv("AI_MV_CLEANUP_BETWEEN_CLIPS", "true")

    cfg = default_config()

    assert cfg["render"]["cleanup_between_clips"] is True
