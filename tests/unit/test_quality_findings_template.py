import json

from ai_mv.core.review.quality_findings import (
    KNOWN_QUALITY_FINDING_CODES,
    quality_findings_review_input_template,
)


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
