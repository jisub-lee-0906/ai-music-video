from __future__ import annotations

from pathlib import Path

from ai_mv.core.orchestration.wsl_overrides import _default_wsl_codex_bin, _discover_wsl_comfy_dir, apply_wsl_runtime_overrides


def test_apply_wsl_runtime_overrides_leaves_non_wsl_config_unchanged(monkeypatch):
    cfg = {
        "integrations": {
            "comfyui_base_url": "http://127.0.0.1:8000",
            "comfyui_input_dir": r"C:\Users\Desktop\Documents\ComfyUI\input",
            "comfyui_output_dir": r"C:\Users\Desktop\Documents\ComfyUI\output",
            "codex_cli_path": "",
        }
    }
    monkeypatch.setattr("ai_mv.core.orchestration.wsl_overrides._is_wsl", lambda: False)

    out = apply_wsl_runtime_overrides(cfg)

    assert out == cfg
    assert out is cfg


def test_apply_wsl_runtime_overrides_rewrites_windows_paths_when_env_present(monkeypatch):
    cfg = {
        "integrations": {
            "comfyui_base_url": "http://127.0.0.1:8000",
            "comfyui_input_dir": r"C:\Users\Desktop\Documents\ComfyUI\input",
            "comfyui_output_dir": r"C:\Users\Desktop\Documents\ComfyUI\output",
            "codex_cli_path": "",
        }
    }
    monkeypatch.setattr("ai_mv.core.orchestration.wsl_overrides._is_wsl", lambda: True)
    monkeypatch.setenv("AI_MV_COMFY_HOST", "127.0.0.1")
    monkeypatch.setenv("AI_MV_COMFY_INPUT_DIR", r"C:\\Users\\Desktop\\Documents\\ComfyUI\\input")
    monkeypatch.setenv("AI_MV_COMFY_OUTPUT_DIR", r"C:\\Users\\Desktop\\Documents\\ComfyUI\\output")
    monkeypatch.setenv("AI_MV_CODEX_BIN", "/home/jisub-lee/.hermes/node/bin/codex")

    out = apply_wsl_runtime_overrides(cfg)

    assert out["integrations"]["comfyui_base_url"] == "http://127.0.0.1:8000"
    assert out["integrations"]["comfyui_input_dir"] == r"C:\\Users\\Desktop\\Documents\\ComfyUI\\input"
    assert out["integrations"]["comfyui_output_dir"] == r"C:\\Users\\Desktop\\Documents\\ComfyUI\\output"
    assert out["integrations"]["codex_cli_path"] == "/home/jisub-lee/.hermes/node/bin/codex"



def test_apply_wsl_runtime_overrides_uses_detected_defaults_when_env_missing(monkeypatch):
    cfg = {
        "integrations": {
            "comfyui_base_url": "http://127.0.0.1:8000",
            "comfyui_input_dir": r"C:\Users\Desktop\Documents\ComfyUI\input",
            "comfyui_output_dir": r"C:\Users\Desktop\Documents\ComfyUI\output",
            "codex_cli_path": "",
        }
    }
    monkeypatch.setattr("ai_mv.core.orchestration.wsl_overrides._is_wsl", lambda: True)
    monkeypatch.setattr("ai_mv.core.orchestration.wsl_overrides._wsl_windows_gateway_host", lambda: "127.0.0.1")
    monkeypatch.setattr(
        "ai_mv.core.orchestration.wsl_overrides._default_wsl_comfy_input_dir",
        lambda: r"C:\\Users\\Desktop\\Documents\\ComfyUI\\input",
    )
    monkeypatch.setattr(
        "ai_mv.core.orchestration.wsl_overrides._default_wsl_comfy_output_dir",
        lambda: r"C:\\Users\\Desktop\\Documents\\ComfyUI\\output",
    )
    monkeypatch.setattr(
        "ai_mv.core.orchestration.wsl_overrides._default_wsl_codex_bin",
        lambda: "/home/jisub-lee/.hermes/node/bin/codex",
    )

    out = apply_wsl_runtime_overrides(cfg)

    assert out["integrations"]["comfyui_base_url"] == "http://127.0.0.1:8000"
    assert out["integrations"]["comfyui_input_dir"] == r"C:\\Users\\Desktop\\Documents\\ComfyUI\\input"
    assert out["integrations"]["comfyui_output_dir"] == r"C:\\Users\\Desktop\\Documents\\ComfyUI\\output"
    assert out["integrations"]["codex_cli_path"] == "/home/jisub-lee/.hermes/node/bin/codex"



def test_discover_wsl_comfy_dir_finds_user_documents_path(tmp_path):
    users_root = tmp_path / "Users"
    (users_root / "Alice" / "Documents" / "ComfyUI" / "input").mkdir(parents=True)
    (users_root / "Alice" / "Documents" / "ComfyUI" / "output").mkdir(parents=True)

    assert _discover_wsl_comfy_dir("input", users_root) == str(users_root / "Alice" / "Documents" / "ComfyUI" / "input")
    assert _discover_wsl_comfy_dir("output", users_root) == str(users_root / "Alice" / "Documents" / "ComfyUI" / "output")



def test_discover_wsl_comfy_dir_skips_inaccessible_candidate_and_prefers_accessible_one(monkeypatch, tmp_path):
    users_root = tmp_path / "Users"
    sandbox = users_root / "CodexSandboxOffline" / "Documents" / "ComfyUI" / "input"
    desktop = users_root / "Desktop" / "Documents" / "ComfyUI" / "input"
    sandbox.mkdir(parents=True)
    desktop.mkdir(parents=True)

    original_is_dir = Path.is_dir

    def _fake_is_dir(path_obj):
        if str(path_obj) == str(sandbox):
            raise PermissionError("permission denied")
        return original_is_dir(path_obj)

    monkeypatch.setattr(Path, "is_dir", _fake_is_dir)

    assert _discover_wsl_comfy_dir("input", users_root) == str(desktop)



def test_default_wsl_codex_bin_uses_home_fallback(monkeypatch, tmp_path):
    home = tmp_path / "home-user"
    codex = home / ".hermes" / "node" / "bin" / "codex"
    codex.parent.mkdir(parents=True)
    codex.write_text("#!/bin/sh\n", encoding="utf-8")
    codex.chmod(0o755)
    monkeypatch.delenv("AI_MV_CODEX_BIN", raising=False)
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setattr("ai_mv.core.orchestration.wsl_overrides.shutil.which", lambda _name: None)

    assert _default_wsl_codex_bin() == str(codex)


def test_apply_wsl_runtime_overrides_preserves_linux_safe_values(monkeypatch):
    cfg = {
        "integrations": {
            "comfyui_base_url": "http://10.0.0.9:8000",
            "comfyui_input_dir": "/mnt/c/custom/input",
            "comfyui_output_dir": "/mnt/c/custom/output",
            "codex_cli_path": "/usr/local/bin/codex",
        }
    }
    monkeypatch.setattr("ai_mv.core.orchestration.wsl_overrides._is_wsl", lambda: True)
    monkeypatch.setenv("AI_MV_COMFY_HOST", "127.0.0.1")
    monkeypatch.setenv("AI_MV_COMFY_INPUT_DIR", r"C:\\Users\\Desktop\\Documents\\ComfyUI\\input")
    monkeypatch.setenv("AI_MV_COMFY_OUTPUT_DIR", r"C:\\Users\\Desktop\\Documents\\ComfyUI\\output")
    monkeypatch.setenv("AI_MV_CODEX_BIN", "/home/jisub-lee/.hermes/node/bin/codex")

    out = apply_wsl_runtime_overrides(cfg)

    assert out["integrations"]["comfyui_base_url"] == "http://10.0.0.9:8000"
    assert out["integrations"]["comfyui_input_dir"] == "/mnt/c/custom/input"
    assert out["integrations"]["comfyui_output_dir"] == "/mnt/c/custom/output"
    assert out["integrations"]["codex_cli_path"] == "/usr/local/bin/codex"


def test_apply_wsl_runtime_overrides_enables_smoke_mode(monkeypatch):
    cfg = {
        "audio": {
            "target_duration_min_sec": 150,
            "target_duration_max_sec": 180,
        },
        "planning": {
            "enable_ia2v": True,
        },
        "integrations": {
            "comfyui_base_url": "http://127.0.0.1:8000",
            "comfyui_input_dir": r"C:\\Users\\Desktop\\Documents\\ComfyUI\\input",
            "comfyui_output_dir": r"C:\\Users\\Desktop\\Documents\\ComfyUI\\output",
            "codex_cli_path": "",
        },
    }
    monkeypatch.setattr("ai_mv.core.orchestration.wsl_overrides._is_wsl", lambda: True)
    monkeypatch.setenv("AI_MV_COMFY_HOST", "127.0.0.1")
    monkeypatch.setenv("AI_MV_COMFY_INPUT_DIR", r"C:\\Users\\Desktop\\Documents\\ComfyUI\\input")
    monkeypatch.setenv("AI_MV_COMFY_OUTPUT_DIR", r"C:\\Users\\Desktop\\Documents\\ComfyUI\\output")
    monkeypatch.setenv("AI_MV_CODEX_BIN", "/home/jisub-lee/.hermes/node/bin/codex")
    monkeypatch.setenv("AI_MV_WSL_SMOKE_MODE", "1")
    monkeypatch.setenv("AI_MV_SMOKE_AUDIO_MIN_SEC", "15")
    monkeypatch.setenv("AI_MV_SMOKE_AUDIO_MAX_SEC", "20")

    out = apply_wsl_runtime_overrides(cfg)

    assert out["audio"]["target_duration_min_sec"] == 15
    assert out["audio"]["target_duration_max_sec"] == 20
    assert out["planning"]["enable_ia2v"] is True
    assert "enable_flf2v" not in out["planning"]
    assert "max_flf2v_shots" not in out["planning"]
    assert "flf2v_min_sec" not in out["planning"]
    assert "flf2v_max_sec" not in out["planning"]
