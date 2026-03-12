from __future__ import annotations

import json
import os
import subprocess
import tempfile
from pathlib import Path

from jsonschema import ValidationError, validate

from ai_mv.core.contracts.errors import CodexCliRequestError
def ping_codex() -> bool:
    try:
        _login_status(_codex_command({}))
        return True
    except Exception:
        return False


def generate_structured(config: dict, prompt: str, schema: dict) -> dict:
    return _generate_once(config, prompt, schema)


def assert_codex_ready(config: dict) -> None:
    cmd = _codex_command(config)
    status = _login_status(cmd)
    if "Logged in" not in status:
        raise CodexCliRequestError("Codex CLI is not logged in")


def _generate_once(config: dict, prompt: str, schema: dict) -> dict:
    cmd = _codex_command(config)
    model = _codex_model(config)
    timeout = _codex_timeout(config)
    strict_schema = _strict_schema(schema)
    with tempfile.TemporaryDirectory(prefix="ai-mv-codex-") as tmp:
        schema_path = Path(tmp) / "schema.json"
        output_path = Path(tmp) / "output.json"
        schema_path.write_text(json.dumps(strict_schema, ensure_ascii=False), encoding="utf-8")
        args = _exec_args(cmd, model, schema_path, output_path, prompt)
        _run(args, prompt, timeout)
        data = _load_output(output_path)
        _validate_schema(data, schema)
        return data


def _exec_args(cmd: str, model: str, schema_path: Path, output_path: Path, prompt: str) -> list[str]:
    return [
        "cmd",
        "/c",
        cmd,
        "exec",
        "--skip-git-repo-check",
        "--sandbox",
        "read-only",
        "--output-schema",
        str(schema_path),
        "-o",
        str(output_path),
        "-m",
        model,
        "-",
    ]


def _load_output(path: Path) -> dict:
    if not path.exists():
        raise CodexCliRequestError("Codex CLI did not write output")
    text = path.read_text(encoding="utf-8").strip()
    if not text:
        raise CodexCliRequestError("Codex CLI returned empty output")
    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        raise CodexCliRequestError(f"Codex CLI returned invalid JSON: {exc.msg}") from exc
    if not isinstance(data, dict):
        raise CodexCliRequestError("Codex CLI structured payload must be a JSON object")
    return data


def _validate_schema(data: dict, schema: dict) -> None:
    try:
        validate(instance=data, schema=schema)
    except ValidationError as exc:
        path = ".".join(str(x) for x in exc.absolute_path)
        loc = f" at {path}" if path else ""
        raise CodexCliRequestError(f"Codex CLI schema validation failed{loc}: {exc.message}") from exc


def _strict_schema(schema: dict):
    if isinstance(schema, dict):
        out = {k: _strict_schema(v) for k, v in schema.items()}
        if out.get("type") == "object":
            out["additionalProperties"] = False
        return out
    if isinstance(schema, list):
        return [_strict_schema(x) for x in schema]
    return schema


def _login_status(cmd: str) -> str:
    res = subprocess.run(
        ["cmd", "/c", cmd, "login", "status"],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=10,
        check=False,
    )
    if res.returncode != 0:
        raise CodexCliRequestError(f"Codex CLI login status failed: {res.stderr.strip() or res.stdout.strip()}")
    text = res.stdout.strip() or res.stderr.strip()
    return text


def _run(args: list[str], prompt: str, timeout: int) -> None:
    res = subprocess.run(
        args,
        input=prompt,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=timeout,
        check=False,
    )
    if res.returncode != 0:
        detail = res.stderr.strip() or res.stdout.strip()
        raise CodexCliRequestError(f"Codex CLI exec failed: {detail}")
def _codex_command(config: dict) -> str:
    integ = config.get("integrations", {}) if isinstance(config, dict) else {}
    raw = integ.get("codex_cli_path", "") if isinstance(integ, dict) else ""
    direct = str(raw).strip()
    if direct:
        return direct
    appdata = os.getenv("APPDATA", "").strip()
    if appdata:
        npm_cmd = Path(appdata) / "npm" / "codex.cmd"
        if npm_cmd.exists():
            return str(npm_cmd)
    return "codex"


def _codex_model(config: dict) -> str:
    integ = config.get("integrations", {}) if isinstance(config, dict) else {}
    raw = integ.get("codex_model", "gpt-5.4") if isinstance(integ, dict) else "gpt-5.4"
    val = str(raw).strip()
    return val or "gpt-5.4"


def _codex_timeout(config: dict) -> int:
    integ = config.get("integrations", {}) if isinstance(config, dict) else {}
    raw = integ.get("codex_timeout_structured_sec", 600) if isinstance(integ, dict) else 600
    try:
        return max(10, int(raw))
    except Exception:
        return 600
