from __future__ import annotations

from pathlib import Path


MAX_LINES = 300


def main() -> int:
    bad = []
    for path in Path("src").rglob("*.py"):
        lines = path.read_text(encoding="utf-8").splitlines()
        if len(lines) > MAX_LINES:
            bad.append((str(path), len(lines)))
    for path, size in bad:
        print(f"{path}: {size}")
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())

