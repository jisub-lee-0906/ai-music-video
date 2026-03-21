from ai_mv.core.contracts.prompt_normalize import normalize_flux2_ref_items


def test_normalize_flux2_ref_preserves_long_optional_clauses():
    anchors = [{"shot_id": "S001"}]
    raw_items = [
        {
            "shot_id": "S001",
            "prompt_text": "The same anime girl, now hero turns and smiles. Neon city skyline. Flat cel shading, thick clean outlines.",
            "subject_clause": " ".join([f"word{i}" for i in range(1, 30)]),
            "action_clause": "hero turns and smiles",
            "camera_clause": "neon city skyline",
            "continuity_clause": "keeps same lane",
        },
    ]

    out = normalize_flux2_ref_items(raw_items, anchors)
    clause = out["S001"]["subject_clause"]
    assert clause == " ".join(f"word{i}" for i in range(1, 30))
