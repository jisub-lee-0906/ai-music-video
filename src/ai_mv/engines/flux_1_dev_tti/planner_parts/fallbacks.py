from __future__ import annotations


def default_shots(sections: list[dict], guidance: str) -> list[dict]:
    shots: list[dict] = []
    idx = 0
    for sec in sections or [{"name": "verse"}]:
        shots.append(
            {
                "shot_id": f"{sec['name']}_{idx:03d}",
                "prompt": f"{guidance}, section {sec['name']}",
                "negative_prompt": "lowres, blur, artifacts",
                "duration_sec": 5.0,
                "seed": 1000 + idx,
            }
        )
        idx += 1
    return shots

