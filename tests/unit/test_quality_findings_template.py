import json
from pathlib import Path

from ai_mv.core.review.quality_findings import (
    KNOWN_QUALITY_FINDING_CODES,
    quality_findings_review_input_template,
)

REPO_ROOT = Path(__file__).resolve().parents[2]


def test_quality_findings_review_input_template_scaffolds_shot_map():
    template = quality_findings_review_input_template(["S001", "S002"])

    assert template["review_inputs"]["quality_findings"] == {
        "S001": [],
        "S002": [],
    }
    assert template["known_quality_finding_codes"] == list(KNOWN_QUALITY_FINDING_CODES)


def test_quality_findings_review_input_template_dedups_blank_shot_ids():
    template = quality_findings_review_input_template(["S001", "", "S001", " S002 "])

    assert template["review_inputs"]["quality_findings"] == {
        "S001": [],
        "S002": [],
    }


def test_quality_findings_review_input_template_is_json_serializable():
    payload = quality_findings_review_input_template(["S010"])

    assert json.loads(json.dumps(payload))["review_inputs"]["quality_findings"] == {"S010": []}



def test_quality_findings_review_input_template_exposes_reference_review_hints_for_followup_shots():
    template = quality_findings_review_input_template(
        ["S007"],
        escalation_context={
            "reference_modes": ["use_performance_anchor_still"],
            "followup_shot_ids": ["S007"],
        },
    )

    assert template["review_inputs"]["reference_review_hints"] == [
        "Reference modes in scope: use_performance_anchor_still.",
        "Follow-up shots to review against their anchor continuity: S007.",
    ]



def test_quality_findings_review_input_template_exposes_manual_mv_payoff_codes():
    template = quality_findings_review_input_template(["S001"])

    assert "weak_character_payoff" in template["known_quality_finding_codes"]
    assert "background_dominant_composition" in template["known_quality_finding_codes"]


def test_quality_findings_manual_review_docs_list_scaffold_known_codes():
    docs_text = (REPO_ROOT / "docs" / "quality-findings.md").read_text(encoding="utf-8")

    missing = [code for code in KNOWN_QUALITY_FINDING_CODES if f"`{code}`" not in docs_text]

    assert missing == []
    assert "`repetitive_safe_editing`" in docs_text
