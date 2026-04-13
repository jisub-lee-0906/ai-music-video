from __future__ import annotations

import shutil
from pathlib import Path

from ai_mv.core.contracts.errors import PipelineError
from ai_mv.core.workflow_names import WORKFLOW_FILES
from ai_mv.infra.comfy_local import validate_local_comfy_config
from ai_mv.utils.path_utils import resolve_project_path


def assert_runtime_ready(config: dict) -> None:
    validate_local_comfy_config(config)
    _assert_ff_tools()
    _assert_workflow_templates(config)


def _assert_ff_tools() -> None:
    for name in ("ffmpeg", "ffprobe"):
        if not shutil.which(name):
            raise PipelineError(f"{name} is required on PATH")


def _assert_workflow_templates(config: dict) -> None:
    base = resolve_project_path(str(config["integrations"]["workflows_dir"]))
    if not base.exists() or not base.is_dir():
        raise PipelineError("integrations.workflows_dir must be an existing directory")
    for name in WORKFLOW_FILES:
        path = base / name
        _assert_workflow_file(path)


def _assert_workflow_file(path: Path) -> None:
    if not path.exists() or not path.is_file():
        raise PipelineError(f"missing workflow template: {path.as_posix()}")
