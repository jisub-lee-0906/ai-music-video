from ai_mv.analysis.contact_sheet import build_contact_sheet_manifest, write_contact_sheet_image


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
    assert manifest["frame_count"] == 5
    assert manifest["columns"] == 4
    assert manifest["rows"] == 2
    assert manifest["reviewer_summary"] == "Contact sheet with 5 frames across 2 rows"
    assert manifest["escalation_context"] == {}
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


def test_build_contact_sheet_manifest_includes_escalation_context_when_provided(tmp_path):
    manifest = build_contact_sheet_manifest(
        frame_paths=[tmp_path / "first.png", tmp_path / "middle.png"],
        frame_labels=["first", "middle"],
        output_image_path=tmp_path / "contact-sheet.png",
        escalation_context={
            "source_stage": "rerender_escalation",
            "run_id": "run-rerender-escalate-1",
            "status": "manual_review_required",
            "shot_ids": ["S003", "S007"],
            "material_ids": ["MAT_003", "MAT_007"],
            "section_ids": ["SEC_003", "SEC_007"],
            "reference_modes": ["use_performance_anchor_still"],
            "anchor_source_shot_ids": [],
            "followup_shot_ids": ["S007"],
        },
    )

    assert manifest["escalation_context"] == {
        "source_stage": "rerender_escalation",
        "run_id": "run-rerender-escalate-1",
        "status": "manual_review_required",
        "shot_ids": ["S003", "S007"],
        "material_ids": ["MAT_003", "MAT_007"],
        "section_ids": ["SEC_003", "SEC_007"],
        "reference_modes": ["use_performance_anchor_still"],
        "anchor_source_shot_ids": [],
        "followup_shot_ids": ["S007"],
    }


def test_build_contact_sheet_manifest_preserves_material_and_section_only_escalation_context(tmp_path):
    manifest = build_contact_sheet_manifest(
        frame_paths=[tmp_path / "first.png"],
        frame_labels=["first"],
        output_image_path=tmp_path / "contact-sheet.png",
        escalation_context={
            "material_ids": ["MAT_003"],
            "section_ids": ["SEC_003"],
        },
    )

    assert manifest["escalation_context"] == {
        "source_stage": "",
        "run_id": "",
        "status": "",
        "shot_ids": [],
        "material_ids": ["MAT_003"],
        "section_ids": ["SEC_003"],
    }


def test_write_contact_sheet_image_tiles_existing_frames(tmp_path, monkeypatch):
    frame_paths = []
    for index in range(3):
        frame = tmp_path / f"frame_{index}.png"
        frame.write_bytes(b"fake-png")
        frame_paths.append(frame)

    captured = {}

    monkeypatch.setattr("ai_mv.analysis.contact_sheet.shutil.which", lambda name: "/usr/bin/ffmpeg" if name == "ffmpeg" else None)

    def _fake_run(cmd, check=False, capture_output=True, text=True):
        captured["cmd"] = cmd
        output_path = tmp_path / "contact-sheet.png"
        output_path.write_bytes(b"sheet")

        class Result:
            returncode = 0
            stdout = ""
            stderr = ""

        return Result()

    written = write_contact_sheet_image(
        frame_paths=frame_paths,
        output_image_path=tmp_path / "contact-sheet.png",
        columns=2,
        rows=2,
        run_fn=_fake_run,
    )

    assert written == tmp_path / "contact-sheet.png"
    assert written.read_bytes() == b"sheet"
    assert captured["cmd"][0] == "/usr/bin/ffmpeg"
    assert any("tile=2x2" in arg for arg in captured["cmd"])
