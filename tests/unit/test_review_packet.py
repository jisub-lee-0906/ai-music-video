import json
from pathlib import Path

from ai_mv.analysis.review_packet import build_review_packet_manifest, write_review_packet


def test_build_review_packet_manifest_for_final_includes_expected_paths(tmp_path):
    manifest = build_review_packet_manifest(
        video_path=tmp_path / "final.mp4",
        output_dir=tmp_path / "review-packet",
        kind="final",
        shot_ids=["S001", "S002"],
        sample_count=4,
        duration_fn=lambda _path: 20.0,
    )

    assert manifest["video_path"] == str(tmp_path / "final.mp4")
    assert manifest["kind"] == "final"
    assert manifest["sample_count"] == 4
    assert manifest["shot_ids"] == ["S001", "S002"]
    assert manifest["frame_paths"] == [
        str(tmp_path / "review-packet" / "frames" / "final_01.png"),
        str(tmp_path / "review-packet" / "frames" / "final_02.png"),
        str(tmp_path / "review-packet" / "frames" / "final_03.png"),
        str(tmp_path / "review-packet" / "frames" / "final_04.png"),
    ]
    assert manifest["quality_findings_path"] == str(tmp_path / "review-packet" / "review-findings.json")
    assert manifest["reviewer_notes_path"] == str(tmp_path / "review-packet" / "review-notes.md")
    assert manifest["contact_sheet_image_path"] == str(tmp_path / "review-packet" / "contact-sheet.png")
    assert manifest["contact_sheet_manifest_path"] == str(tmp_path / "review-packet" / "contact-sheet.json")
    assert manifest["frame_count"] == 4
    assert manifest["reviewer_summary"] == "Review packet for 2 shots with 4 extracted frames"


def test_build_review_packet_manifest_includes_escalation_context_when_provided(tmp_path):
    manifest = build_review_packet_manifest(
        video_path=tmp_path / "final.mp4",
        output_dir=tmp_path / "review-packet",
        kind="final",
        shot_ids=["S003", "S007"],
        sample_count=4,
        duration_fn=lambda _path: 20.0,
        escalation_context={
            "source_stage": "rerender_escalation",
            "run_id": "run-rerender-escalate-1",
            "status": "manual_review_required",
            "shot_ids": ["S003", "S007"],
            "material_ids": ["MAT_003", "MAT_007"],
            "section_ids": ["SEC_003", "SEC_007"],
            "reference_modes": ["use_performance_anchor_still"],
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
        "followup_shot_ids": ["S007"],
        "reference_review_hints": [
            "Reference modes in scope: use_performance_anchor_still.",
            "Follow-up shots to review against their anchor continuity: S007.",
        ],
    }


def test_build_review_packet_manifest_includes_production_policy_context_for_reviewers(tmp_path):
    manifest = build_review_packet_manifest(
        video_path=tmp_path / "final.mp4",
        output_dir=tmp_path / "review-packet",
        kind="final",
        shot_ids=["S005", "S006"],
        sample_count=4,
        duration_fn=lambda _path: 20.0,
        escalation_context={
            "production_policy_by_shot": {
                "S005": {
                    "candidate_role": "hero_face_performance",
                    "ia2v_risk_class": "green",
                    "anchor_reference_arm": "B_UPPER_ONLY",
                    "recommended_duration_sec": {"min": 0.8, "max": 1.8},
                    "review_focus": ["face_stability", "mouth_jaw_drift"],
                },
                "S006": {
                    "candidate_role": "high_risk_interaction_payoff",
                    "ia2v_risk_class": "red",
                    "anchor_reference_arm": "D_FULLBODY_UPPER",
                    "recommended_duration_sec": {"min": 0.3, "max": 0.7},
                    "safety_rules": ["hover_or_reaction_alternative_required"],
                    "review_focus": ["hand_integrity", "water_glow_contact"],
                },
            }
        },
    )

    production_context = manifest["escalation_context"]["production_policy_by_shot"]
    assert production_context["S005"]["candidate_role"] == "hero_face_performance"
    assert production_context["S006"]["ia2v_risk_class"] == "red"
    assert production_context["S006"]["recommended_duration_sec"] == {"min": 0.3, "max": 0.7}


def test_write_review_packet_notes_surface_production_policy_context(tmp_path):
    written = write_review_packet(
        video_path=tmp_path / "final.mp4",
        output_dir=tmp_path / "review-packet",
        kind="final",
        shot_ids=["S006"],
        sample_count=4,
        duration_fn=lambda _path: 20.0,
        escalation_context={
            "production_policy_by_shot": {
                "S006": {
                    "candidate_role": "high_risk_interaction_payoff",
                    "ia2v_risk_class": "red",
                    "anchor_reference_arm": "D_FULLBODY_UPPER",
                    "recommended_duration_sec": {"min": 0.3, "max": 0.7},
                    "safety_rules": ["start_middle_end_review_required"],
                    "review_focus": ["hand_integrity", "water_glow_contact"],
                }
            }
        },
        extract_frames_fn=lambda **_kwargs: [],
        contact_sheet_image_fn=lambda **_kwargs: Path(_kwargs["output_image_path"]),
    )

    notes = written["reviewer_notes_path"].read_text(encoding="utf-8")
    assert "## Production policy context" in notes
    assert "S006: high_risk_interaction_payoff / red / D_FULLBODY_UPPER" in notes
    assert "recommended duration 0.3-0.7s" in notes
    assert "review focus: hand_integrity, water_glow_contact" in notes
    assert "safety: start_middle_end_review_required" in notes


def test_build_review_packet_manifest_preserves_material_and_section_only_escalation_context(tmp_path):
    manifest = build_review_packet_manifest(
        video_path=tmp_path / "final.mp4",
        output_dir=tmp_path / "review-packet",
        kind="final",
        shot_ids=[],
        sample_count=4,
        duration_fn=lambda _path: 20.0,
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



def test_build_review_packet_manifest_is_json_serializable(tmp_path):
    manifest = build_review_packet_manifest(
        video_path=tmp_path / "clip.mp4",
        output_dir=tmp_path / "packet",
        kind="clip",
        shot_ids=["S006"],
        sample_count=6,
        duration_fn=lambda _path: 12.0,
    )

    data = json.loads(json.dumps(manifest))
    assert data["kind"] == "clip"
    assert data["frame_paths"] == [
        str(tmp_path / "packet" / "frames" / "first.png"),
        str(tmp_path / "packet" / "frames" / "middle.png"),
        str(tmp_path / "packet" / "frames" / "last.png"),
    ]
    assert data["contact_sheet_image_path"] == str(tmp_path / "packet" / "contact-sheet.png")


def test_build_review_packet_manifest_uses_callable_duration_fn_when_not_explicitly_provided(tmp_path, monkeypatch):
    captured = {}

    def _fake_plan(**kwargs):
        captured.update(kwargs)
        return [
            {
                "label": "final_01",
                "timestamp_sec": 1.0,
                "output_path": tmp_path / "packet" / "frames" / "final_01.png",
            }
        ]

    monkeypatch.setattr("ai_mv.analysis.review_packet.representative_frame_plan", _fake_plan)

    manifest = build_review_packet_manifest(
        video_path=tmp_path / "final.mp4",
        output_dir=tmp_path / "packet",
        kind="final",
        shot_ids=["S001"],
        sample_count=1,
    )

    assert callable(captured["duration_fn"])
    assert manifest["frame_paths"] == [str(tmp_path / "packet" / "frames" / "final_01.png")]



def test_write_review_packet_returns_contact_sheet_image_path(tmp_path):
    written = write_review_packet(
        video_path=tmp_path / "clip.mp4",
        output_dir=tmp_path / "packet",
        kind="clip",
        shot_ids=["S006"],
        sample_count=6,
        duration_fn=lambda _path: 12.0,
        escalation_context={
            "reference_modes": ["use_anchor_still"],
            "followup_shot_ids": ["S006"],
        },
        extract_frames_fn=lambda **_kwargs: [],
        contact_sheet_image_fn=lambda **_kwargs: Path(_kwargs["output_image_path"]),
    )

    assert written["contact_sheet_image_path"] == tmp_path / "packet" / "contact-sheet.png"
    assert written["contact_sheet_manifest_path"] == tmp_path / "packet" / "contact-sheet.json"

    quality_findings = json.loads((tmp_path / "packet" / "review-findings.json").read_text(encoding="utf-8"))
    assert quality_findings["review_inputs"]["reference_review_hints"] == [
        "Reference modes in scope: use_anchor_still.",
        "Follow-up shots to review against their anchor continuity: S006.",
    ]

    contact_sheet = json.loads((tmp_path / "packet" / "contact-sheet.json").read_text(encoding="utf-8"))
    assert contact_sheet["escalation_context"] == {
        "source_stage": "",
        "run_id": "",
        "status": "",
        "shot_ids": [],
        "material_ids": [],
        "section_ids": [],
        "reference_modes": ["use_anchor_still"],
        "followup_shot_ids": ["S006"],
        "reference_review_hints": [
            "Reference modes in scope: use_anchor_still.",
            "Follow-up shots to review against their anchor continuity: S006.",
        ],
    }


def test_write_review_packet_extracts_frames_and_writes_contact_sheet_image(tmp_path):
    calls = {}

    def _extract_frames(**kwargs):
        calls["extract"] = kwargs
        frames_dir = Path(kwargs["output_dir"])
        frames_dir.mkdir(parents=True, exist_ok=True)
        written = []
        for name in ("final_01.png", "final_02.png"):
            path = frames_dir / name
            path.write_bytes(b"frame")
            written.append(path)
        return written

    def _write_contact_sheet(**kwargs):
        calls["contact_sheet"] = kwargs
        output_path = Path(kwargs["output_image_path"])
        output_path.write_bytes(b"sheet")
        return output_path

    written = write_review_packet(
        video_path=tmp_path / "final.mp4",
        output_dir=tmp_path / "review-packet",
        kind="final",
        shot_ids=["S001"],
        sample_count=2,
        duration_fn=lambda _path: 12.0,
        extract_frames_fn=_extract_frames,
        contact_sheet_image_fn=_write_contact_sheet,
    )

    assert calls["extract"]["output_dir"] == tmp_path / "review-packet" / "frames"
    assert calls["extract"]["kind"] == "final"
    assert calls["extract"]["sample_count"] == 2
    assert calls["contact_sheet"]["frame_paths"] == [
        tmp_path / "review-packet" / "frames" / "final_01.png",
        tmp_path / "review-packet" / "frames" / "final_02.png",
    ]
    assert written["contact_sheet_image_path"].read_bytes() == b"sheet"
    manifest = json.loads(written["manifest_path"].read_text(encoding="utf-8"))
    assert all(Path(path).exists() for path in manifest["frame_paths"])


def test_write_review_packet_includes_reference_continuity_notes_for_reviewers(tmp_path):
    written = write_review_packet(
        video_path=tmp_path / "final.mp4",
        output_dir=tmp_path / "review-packet",
        kind="final",
        shot_ids=["S006", "S007"],
        sample_count=4,
        duration_fn=lambda _path: 20.0,
        escalation_context={
            "reference_modes": ["use_performance_anchor_still"],
            "anchor_source_shot_ids": ["S006"],
            "followup_shot_ids": ["S007"],
        },
        extract_frames_fn=lambda **_kwargs: [],
        contact_sheet_image_fn=lambda **_kwargs: Path(_kwargs["output_image_path"]),
    )

    notes = written["reviewer_notes_path"].read_text(encoding="utf-8")
    assert "## Reference continuity context" in notes
    assert "- Reference modes in scope: use_performance_anchor_still." in notes
    assert "- Follow-up shots to review against their anchor continuity: S007." in notes
    assert "- Anchor-source shots to review as continuity baselines: S006." in notes
    assert "## Shot-specific continuity roles" in notes
    assert "- S006: anchor-source continuity baseline" in notes
    assert "- S007: follow-up continuity shot" in notes
