import json
from pathlib import Path
import subprocess
import pytest

from evolution.evaluate import candidate, evaluate, manifest, regress


def test_score_distinguishes_success_from_verified():
    result = evaluate([
        {"verified": False, "status": "completed", "failure_category": "assertion", "duration_seconds": 2},
        {"verified": False, "failure_category": "assertion", "duration_seconds": 4},
        {"verified": True, "duration_seconds": 6},
    ])
    assert result["verification_rate"] == 1 / 3
    assert result["recurring_failures"] == {"assertion": 2}
    assert result["mean_duration_seconds"] == 4


def test_empty_score_is_unknown_and_invalid_records_rejected():
    assert evaluate([])["verification_rate"] is None
    with pytest.raises(ValueError):
        evaluate([{"verified": "yes"}])


def test_candidate_never_applies_patch(tmp_path):
    patch = tmp_path / "candidate.patch"
    patch.write_text("review this change")
    result = candidate(patch, tmp_path / "record.json", "improvement")
    assert result["status"] == "awaiting-human-review"
    assert len(result["patch_sha256"]) == 64
    assert patch.read_text() == "review this change"


def test_manifest_excludes_secrets_dependencies_and_symlinks(tmp_path):
    (tmp_path / "main.py").write_text("pass")
    (tmp_path / ".env").write_text("API_KEY=secret")
    (tmp_path / "node_modules").mkdir()
    (tmp_path / "node_modules" / "secret.js").write_text("secret")
    (tmp_path / "link.py").symlink_to(tmp_path / "main.py")
    result = manifest(tmp_path, tmp_path / "version.json", "v1")
    assert set(result["source_sha256"]) == {"main.py"}


def test_regression_uses_fixed_argv_and_does_not_persist_output(tmp_path, monkeypatch):
    def run(argv, **kwargs):
        assert argv[1:] == ["-m", "pytest", "-q", "--disable-warnings"]
        assert kwargs["shell"] is False
        assert "API_SECRET" not in kwargs["env"]
        return subprocess.CompletedProcess(argv, 0, "API_SECRET=leaked", "")
    monkeypatch.setenv("API_SECRET", "hidden")
    monkeypatch.setattr(subprocess, "run", run)
    output = tmp_path / "evaluation.json"
    assert regress(tmp_path, output)["passed"]
    assert "leaked" not in output.read_text()
    assert not json.loads(output.read_text())["activation_permitted"]


def test_timeout_cannot_activate(tmp_path, monkeypatch):
    def run(argv, **kwargs):
        raise subprocess.TimeoutExpired(argv, 1)
    monkeypatch.setattr(subprocess, "run", run)
    result = regress(tmp_path, tmp_path / "result.json", 1)
    assert result["timed_out"] and not result["passed"]
