from ai_mv.analysis.contact_sheet import build_contact_sheet_manifest


def test_build_contact_sheet_manifest_assigns_grid_positions(tmp_path):
    manifest = build_contact_sheet_manifest(
        frame_paths=[
            tmp_path / "final_01.png",
            tmp_path / "final_02.png",
            tmp_path / "final_03.png",
            tmp_path / "final_04.png",
            tmp_path / "final_05.png",
        ],
        frame_labels=["final_01", "final_02", "final_03", "final_04", "final_05"],
        output_image_path=tmp_path / "contact-sheet.png",
    )

    assert manifest["output_image_path"] == str(tmp_path / "contact-sheet.png")
    assert manifest["columns"] == 4
    assert manifest["rows"] == 2
    assert manifest["frames"][0]["row"] == 0
    assert manifest["frames"][0]["column"] == 0
    assert manifest["frames"][4]["row"] == 1
    assert manifest["frames"][4]["column"] == 0


def test_build_contact_sheet_manifest_keeps_label_path_pairs_aligned(tmp_path):
    manifest = build_contact_sheet_manifest(
        frame_paths=[tmp_path / "first.png", tmp_path / "middle.png", tmp_path / "last.png"],
        frame_labels=["first", "middle", "last"],
        output_image_path=tmp_path / "contact-sheet.png",
    )

    assert [row["label"] for row in manifest["frames"]] == ["first", "middle", "last"]
    assert [row["frame_path"] for row in manifest["frames"]] == [
        str(tmp_path / "first.png"),
        str(tmp_path / "middle.png"),
        str(tmp_path / "last.png"),
    ]
