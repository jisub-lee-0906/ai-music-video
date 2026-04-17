from __future__ import annotations

import json
from pathlib import Path

from ai_mv.core.review.quality_findings import quality_findings_review_input_template



def run_quality_findings_template(shot_ids: list[str], output: str) -> int:
    payload = quality_findings_review_input_template(shot_ids)
    path = Path(output)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    shot_count = len(payload["review_inputs"]["quality_findings"])
    print(f"output={path}")
    print(f"shot_count={shot_count}")
    return 0
