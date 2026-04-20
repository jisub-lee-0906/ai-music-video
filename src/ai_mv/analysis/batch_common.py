from __future__ import annotations

import json
from pathlib import Path



def save_results(batch_dir: Path, metadata: dict, runs: list[dict]) -> Path:
    results_path = batch_dir / "results.json"
    payload = {"metadata": metadata, "runs": runs}
    results_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return results_path



def pending_runs(runs: list[dict], existing: list[dict]) -> list[dict]:
    seen = {str(row.get("run_id", "")).strip() for row in existing if isinstance(row, dict)}
    return [row for row in runs if str(row.get("run_id", "")).strip() not in seen]
