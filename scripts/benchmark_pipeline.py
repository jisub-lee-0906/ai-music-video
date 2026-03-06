from __future__ import annotations

import time

from ai_mv.entrypoints.run_batch import run_batch


def main() -> int:
    start = time.perf_counter()
    code = run_batch("")
    elapsed = time.perf_counter() - start
    print(f"exit={code} elapsed_sec={elapsed:.2f}")
    return code


if __name__ == "__main__":
    raise SystemExit(main())
