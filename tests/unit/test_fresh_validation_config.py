from ai_mv.core.orchestration.fresh_validation import prepare_fresh_validation_config, run_fresh_validation


def test_prepare_fresh_validation_config_builds_canonical_short_wsl_smoke_shape(monkeypatch):
    calls: list[str] = []

    monkeypatch.setattr(
        "ai_mv.core.orchestration.fresh_validation.default_config",
        lambda: {"audio": {"existing": "keep"}, "planning": {"existing": "keep"}},
    )

    def _record(name: str):
        def _inner(cfg):
            calls.append(name)
            cfg.setdefault("_calls", []).append(name)
            return cfg

        return _inner

    monkeypatch.setattr("ai_mv.core.orchestration.fresh_validation.apply_defaults", _record("apply_defaults"))
    monkeypatch.setattr("ai_mv.core.orchestration.fresh_validation.apply_wsl_runtime_overrides", _record("apply_wsl_runtime_overrides"))
    monkeypatch.setattr("ai_mv.core.orchestration.fresh_validation.apply_input_defaults", _record("apply_input_defaults"))
    monkeypatch.setattr("ai_mv.core.orchestration.fresh_validation.validate_sizes", _record("validate_sizes"))
    monkeypatch.setattr("ai_mv.core.orchestration.fresh_validation.validate_templates", _record("validate_templates"))

    cfg = prepare_fresh_validation_config()

    assert cfg["concept_text"] == "late-night city walk under wet neon lights with one protagonist moving through the same boulevard world"
    assert cfg["audio"]["existing"] == "keep"
    assert cfg["audio"]["brief"] == (
        "Short-form Korean city-pop song with one protagonist moving through the same rain-slick neon boulevard world, "
        "restrained verse detail, a tightening pre-chorus, and a chorus that feels emotionally continuous rather than scene-switching."
    )
    assert cfg["audio"]["hook_brief"] == (
        "Give the chorus a short title-worthy Korean hook about the same wet city lights and moving forward after midnight. "
        "Keep it concise and singable."
    )
    assert cfg["audio"]["language"] == "ko"
    assert cfg["audio"]["genre_head"] == "city pop"
    assert cfg["audio"]["target_duration_sec"] == 18
    assert cfg["planning"]["existing"] == "keep"
    assert cfg["planning"]["continuity_mode"] == "strict"
    assert cfg["planning"]["default_style_name"] == "citypop"
    assert calls == [
        "apply_defaults",
        "apply_wsl_runtime_overrides",
        "apply_input_defaults",
        "validate_sizes",
        "validate_templates",
    ]


def test_run_fresh_validation_prepares_config_and_launches_pipeline(monkeypatch):
    captured: dict[str, object] = {}

    monkeypatch.setattr(
        "ai_mv.core.orchestration.fresh_validation.prepare_fresh_validation_config",
        lambda **kwargs: {"concept_text": kwargs["concept_text"], "audio": {"target_duration_sec": kwargs["target_duration_sec"]}},
    )

    def _fake_run_pipeline(cfg, run_id="", allow_existing_run=False):
        captured["cfg"] = cfg
        captured["run_id"] = run_id
        captured["allow_existing_run"] = allow_existing_run
        return "fresh-run-123"

    monkeypatch.setattr("ai_mv.core.orchestration.fresh_validation.run_pipeline", _fake_run_pipeline)

    run_id = run_fresh_validation(
        run_id="fresh-validation-run",
        concept_text="custom concept",
        target_duration_sec=12,
        allow_existing_run=True,
    )

    assert run_id == "fresh-run-123"
    assert captured == {
        "cfg": {"concept_text": "custom concept", "audio": {"target_duration_sec": 12}},
        "run_id": "fresh-validation-run",
        "allow_existing_run": True,
    }
