from __future__ import annotations

from pathlib import Path


def main() -> int:
    roots = [Path("src/ai_mv/core"), Path("src/ai_mv/engines")]
    for root in roots:
        count = len(list(root.rglob("*.py")))
        print(f"{root}: {count} files")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

