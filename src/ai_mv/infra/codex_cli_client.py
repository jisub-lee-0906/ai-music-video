from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
import time
from pathlib import Path

from jsonschema import ValidationError, validate

from ai_mv.core.contracts.errors import CodexCliRequestError


class CodexCliSchemaValidationError(CodexCliRequestError):
    pass


def ping_codex(config: dict | None = None) -> bool:
    try:
        _login_status(_codex_command_parts(config or {}))
        return True
    except Exception:
        return False


def generate_structured(config: dict, prompt: str, schema: dict, attempts: int = 3) -> dict:
    current_prompt = prompt
    last_exc: Exception | None = None
    repair = (
        "Previous output failed schema validation or execution. "
        "Return JSON only, strictly matching the schema."
    )
    total_attempts = max(1, int(attempts))
    for attempt in range(1, total_attempts + 1):
        try:
            return _generate_once(config, current_prompt, schema)
        except CodexCliSchemaValidationError as exc:
            last_exc = exc
            break
        except CodexCliRequestError as exc:
            last_exc = exc
            if attempt >= total_attempts:
                break
            current_prompt = f"{prompt}\n\n{repair}"
            time.sleep(min(2 ** attempt, 8))
    if last_exc is not None:
        raise last_exc
    raise CodexCliRequestError("Codex CLI structured generation failed without an exception")


def generate_text(config: dict, prompt: str, attempts: int = 3) -> str:
    current_prompt = prompt
    last_exc: Exception | None = None
    repair = "Previous output failed formatting. Return plain text only in the exact requested format."
    total_attempts = max(1, int(attempts))
    for attempt in range(1, total_attempts + 1):
        try:
            return _generate_text_once(config, current_prompt)
        except CodexCliRequestError as exc:
            last_exc = exc
            if attempt >= total_attempts:
                break
            current_prompt = f"{prompt}\n\n{repair}"
            time.sleep(min(2 ** attempt, 8))
    if last_exc is not None:
        raise last_exc
    raise CodexCliRequestError("Codex CLI text generation failed without an exception")


def assert_codex_ready(config: dict) -> None:
    status = _login_status(_codex_command_parts(config))
    if "Logged in" not in status:
        raise CodexCliRequestError("Codex CLI is not logged in")


def _generate_once(config: dict, prompt: str, schema: dict) -> dict:
    cmd = _codex_command_parts(config)
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


def _generate_text_once(config: dict, prompt: str) -> str:
    cmd = _codex_command_parts(config)
    model = _codex_model(config)
    timeout = _codex_text_timeout(config)
    args = cmd + [
        "exec",
        "--skip-git-repo-check",
        "--sandbox",
        "read-only",
        "-m",
        model,
        "-",
    ]
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
    text = (res.stdout or "").strip()
    if not text:
        raise CodexCliRequestError("Codex CLI returned empty text output")
    return _strip_code_fence(text)


def _exec_args(cmd: list[str], model: str, schema_path: Path, output_path: Path, prompt: str) -> list[str]:
    return cmd + [
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
        raise CodexCliSchemaValidationError(f"Codex CLI schema validation failed{loc}: {exc.message}") from exc


def _strict_schema(schema: dict):
    if isinstance(schema, dict):
        out = {k: _strict_schema(v) for k, v in schema.items()}
        if out.get("type") == "object":
            out["additionalProperties"] = False
        return out
    if isinstance(schema, list):
        return [_strict_schema(x) for x in schema]
    return schema


def _login_status(cmd: list[str]) -> str:
    try:
        res = subprocess.run(
            cmd + ["login", "status"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=10,
            check=False,
        )
    except FileNotFoundError as exc:
        raise CodexCliRequestError("Codex CLI executable not found") from exc
    if res.returncode != 0:
        raise CodexCliRequestError(f"Codex CLI login status failed: {res.stderr.strip() or res.stdout.strip()}")
    text = res.stdout.strip() or res.stderr.strip()
    return text


def _run(args: list[str], prompt: str, timeout: int | None) -> None:
    try:
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
    except FileNotFoundError as exc:
        raise CodexCliRequestError("Codex CLI executable not found") from exc
    if res.returncode != 0:
        detail = res.stderr.strip() or res.stdout.strip()
        raise CodexCliRequestError(f"Codex CLI exec failed: {detail}")


def _strip_code_fence(text: str) -> str:
    stripped = text.strip()
    if not stripped.startswith("```"):
        return stripped
    lines = stripped.splitlines()
    if len(lines) >= 3 and lines[0].startswith("```") and lines[-1].strip() == "```":
        return "\n".join(lines[1:-1]).strip()
    return stripped


def _codex_command_parts(config: dict) -> list[str]:
    integ = config.get("integrations", {}) if isinstance(config, dict) else {}
    raw = integ.get("codex_cli_path", "") if isinstance(integ, dict) else ""
    direct = str(raw).strip()
    if direct:
        return _validated_command_parts(Path(direct).expanduser())
    appdata = os.getenv("APPDATA", "").strip()
    if appdata:
        npm_cmd = Path(appdata) / "npm" / "codex.cmd"
        if npm_cmd.exists():
            return _validated_command_parts(npm_cmd)
    resolved = shutil.which("codex") or shutil.which("codex.cmd")
    if resolved:
        return _validated_command_parts(Path(resolved))
    return ["codex"]


def _validated_command_parts(path: Path) -> list[str]:
    resolved = path.resolve()
    if not resolved.exists() or not resolved.is_file():
        raise CodexCliRequestError(f"invalid codex_cli_path: {resolved}")
    if resolved.suffix.lower() in {".cmd", ".bat"}:
        return [os.environ.get("COMSPEC", "cmd.exe"), "/d", "/c", str(resolved)]
    return [str(resolved)]


def _codex_model(config: dict) -> str:
    integ = config.get("integrations", {}) if isinstance(config, dict) else {}
    raw = integ.get("codex_model", "gpt-5.5") if isinstance(integ, dict) else "gpt-5.5"
    val = str(raw).strip()
    return val or "gpt-5.5"


def _codex_timeout(config: dict) -> int | None:
    integ = config.get("integrations", {}) if isinstance(config, dict) else {}
    raw = integ.get("codex_timeout_structured_sec", 0) if isinstance(integ, dict) else 0
    try:
        value = int(raw)
    except Exception:
        return None
    return None if value <= 0 else max(10, value)


def _codex_text_timeout(config: dict) -> int | None:
    integ = config.get("integrations", {}) if isinstance(config, dict) else {}
    raw = integ.get("codex_timeout_text_sec", None) if isinstance(integ, dict) else None
    if raw is None or str(raw).strip() == "":
        return _codex_timeout(config)
    try:
        value = int(raw)
    except Exception:
        return _codex_timeout(config)
    return None if value <= 0 else max(10, value)
