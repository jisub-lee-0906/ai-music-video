from pathlib import Path

from ai_mv.utils.project_root import project_root


def test_project_root_prefers_marked_repository_root(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "pyproject.toml").write_text("name = \"test\"")
    (repo / "README.md").write_text("# repo")

    module_file = repo / "src" / "nested" / "ai_mv" / "utils" / "path_utils.py"
    module_file.parent.mkdir(parents=True, exist_ok=True)
    module_file.write_text("")

    assert project_root(module_file) == repo
