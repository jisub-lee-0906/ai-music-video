from pathlib import Path

from ai_mv.core.artifacts.manifest import write_manifest
from ai_mv.core.artifacts.schema import artifact_schema_version



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
