from ai_mv.utils.redaction import redact_secrets


def test_redacts_actual_secret_patterns_but_preserves_debug_context():
    raw = "request failed at C:/work/file.py:42 authorization: Bearer abc.def token=secret-value status=401"

    redacted = redact_secrets(raw)

    assert "C:/work/file.py:42" in redacted
    assert "status=401" in redacted
    assert "abc.def" not in redacted
    assert "secret-value" not in redacted
    assert redacted.count("[REDACTED]") == 2


def test_does_not_redact_generic_error_words():
    raw = "tokenizer failed and password policy check returned false"

    assert redact_secrets(raw) == raw
