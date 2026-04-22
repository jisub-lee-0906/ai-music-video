from ai_mv.core.artifacts.provenance import dedupe_preserve_order, normalized_text_list


def test_normalized_text_list_trims_filters_and_rejects_non_lists():
    assert normalized_text_list(["  S001  ", "", None, "  ", 7]) == ["S001", "None", "7"]
    assert normalized_text_list("S001") == []
    assert normalized_text_list({"shot_id": "S001"}) == []



def test_dedupe_preserve_order_keeps_first_seen_values():
    assert dedupe_preserve_order(["MAT_B", "MAT_A", "MAT_B", "MAT_C", "MAT_A"]) == ["MAT_B", "MAT_A", "MAT_C"]
