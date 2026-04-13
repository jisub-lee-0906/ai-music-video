from pathlib import Path

from ai_mv.infra.single_flight_lock import release_lock


def test_release_lock_is_noop_when_file_is_already_gone(tmp_path):
    missing = tmp_path / "missing.lock"
    release_lock(Path(missing))
