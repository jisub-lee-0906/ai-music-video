from ai_mv.entrypoints import start


def test_prepare_comfy_queue_frees_vram_after_interrupt_and_clear(monkeypatch):
    calls = []

    monkeypatch.setattr(start, "interrupt_comfy", lambda base_url: calls.append(("interrupt", base_url)))
    monkeypatch.setattr(start, "clear_comfy_queue", lambda base_url: calls.append(("clear", base_url)))
    monkeypatch.setattr(start, "comfy_queue_counts", lambda base_url: calls.append(("counts", base_url)) or (0, 0))
    monkeypatch.setattr(start, "free_comfy_memory", lambda base_url: calls.append(("free", base_url)))

    start._prepare_comfy_queue(
        {
            "integrations": {"comfyui_base_url": "http://127.0.0.1:8000"},
            "runtime": {
                "interrupt_comfy_before_start": True,
                "clear_comfy_queue_before_start": True,
            },
        }
    )

    assert calls == [
        ("interrupt", "http://127.0.0.1:8000"),
        ("clear", "http://127.0.0.1:8000"),
        ("counts", "http://127.0.0.1:8000"),
        ("free", "http://127.0.0.1:8000"),
    ]


def test_prepare_comfy_queue_does_not_free_vram_when_queue_was_not_stopped(monkeypatch):
    calls = []

    monkeypatch.setattr(start, "interrupt_comfy", lambda base_url: calls.append(("interrupt", base_url)))
    monkeypatch.setattr(start, "clear_comfy_queue", lambda base_url: calls.append(("clear", base_url)))
    monkeypatch.setattr(start, "comfy_queue_counts", lambda base_url: calls.append(("counts", base_url)) or (0, 0))
    monkeypatch.setattr(start, "free_comfy_memory", lambda base_url: calls.append(("free", base_url)))

    start._prepare_comfy_queue(
        {
            "integrations": {"comfyui_base_url": "http://127.0.0.1:8000"},
            "runtime": {},
        }
    )

    assert calls == [("counts", "http://127.0.0.1:8000")]
