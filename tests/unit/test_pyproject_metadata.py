from pathlib import Path
import tomllib


def test_dev_extras_include_build_tool():
    data = tomllib.loads(Path("pyproject.toml").read_text(encoding="utf-8"))
    dev_extras = data["project"]["optional-dependencies"]["dev"]
    assert any(item == "build" or item.startswith("build==") or item.startswith("build>") or item.startswith("build<") or item.startswith("build~") for item in dev_extras)
