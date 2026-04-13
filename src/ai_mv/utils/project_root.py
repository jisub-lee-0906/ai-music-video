from __future__ import annotations

from pathlib import Path


def project_root(module_file: str | Path) -> Path:
    file_path = Path(module_file).resolve()
    for parent in (file_path, *file_path.parents):
        if (parent / "pyproject.toml").exists() and (parent / "README.md").exists():
            return parent

    fallback_index = 4
    if len(file_path.parents) > fallback_index:
        return file_path.parents[fallback_index]
    return file_path.parent
