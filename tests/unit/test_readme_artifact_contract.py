from pathlib import Path

from ai_mv.core.artifacts.manifest import write_manifest
from ai_mv.core.artifacts.schema import artifact_schema_version


def test_readme_declares_current_flux_anchor_ia2v_canon_without_removed_video_workflows():
    readme = Path("README.md").read_text(encoding="utf-8")
    lowered = readme.lower()

    assert "flux tti upper-body identity anchor" in lowered
    assert "flux reference pose/action anchor bank" in lowered
    assert "ia2v-only video generation" in lowered
    assert "bridge-shot repair" in lowered
    assert "flf2v" not in lowered


def test_docs_guide_only_points_to_current_truth_surfaces():
    docs_guide = Path("docs/README.md").read_text(encoding="utf-8")

    assert "Current source of truth" in docs_guide
    assert "docs/plans/" not in docs_guide
    assert "docs/analysis/" not in docs_guide
    assert "docs/archive/" not in docs_guide
    assert "historical docs" not in docs_guide.lower()



def test_readme_artifact_contract_matches_current_public_manifest_schema(monkeypatch):
    readme = Path("README.md").read_text(encoding="utf-8")
    captured: list[dict] = []

    monkeypatch.setattr("ai_mv.core.artifacts.manifest.write_json", lambda path, payload: captured.append(payload))
    monkeypatch.setattr("ai_mv.core.artifacts.manifest.run_file", lambda run_id, name, scope: f"/tmp/{run_id}/{scope}/{name}")
    monkeypatch.setattr("ai_mv.core.artifacts.manifest.latest_file", lambda name, scope: f"/tmp/latest/{scope}/{name}")
    monkeypatch.setattr("ai_mv.core.artifacts.manifest.latest_success_file", lambda name, scope: f"/tmp/latest-success/{scope}/{name}")

    write_manifest(
        {"run_id": "run-readme", "status": "done", "failure_reason": "", "scope": "run"},
        {},
    )

    manifest = captured[0]
    public_sections = [key for key in manifest.keys() if key in {"input", "song", "plan", "stills", "clips", "assembly", "review", "artifacts"}]
    expected_section_sentence = (
        "`manifest.json` also records canonical sections such as "
        + ", ".join(f"`{key}`" for key in public_sections[:-1])
        + ", and "
        + f"`{public_sections[-1]}`"
    )

    assert artifact_schema_version() in readme
    assert expected_section_sentence in readme
