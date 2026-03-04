from __future__ import annotations

import ast
from pathlib import Path


MAX_LINES = 40


def main() -> int:
    bad = []
    for path in Path("src").rglob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                size = (node.end_lineno or node.lineno) - node.lineno + 1
                if size > MAX_LINES:
                    bad.append((str(path), node.name, size))
    for path, name, size in bad:
        print(f"{path}:{name} -> {size}")
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())

