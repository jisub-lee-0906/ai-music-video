from __future__ import annotations

from math import ceil
from pathlib import Path



def build_contact_sheet_manifest(
    *,
    frame_paths: list[str | Path],
    frame_labels: list[str],
    output_image_path: str | Path,
    max_columns: int = 4,
) -> dict[str, object]:
    normalized_paths = [str(Path(path)) for path in frame_paths]
    normalized_labels = [str(label) for label in frame_labels]
    count = min(len(normalized_paths), len(normalized_labels))
    columns = max(1, min(int(max_columns or 4), max(count, 1)))
    rows = max(1, ceil(count / columns))
    frames: list[dict[str, object]] = []
    for index in range(count):
        frames.append(
            {
                "index": index,
                "label": normalized_labels[index],
                "frame_path": normalized_paths[index],
                "row": index // columns,
                "column": index % columns,
            }
        )
    return {
        "output_image_path": str(Path(output_image_path)),
        "columns": columns,
        "rows": rows,
        "frames": frames,
    }
