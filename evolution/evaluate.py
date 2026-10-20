"""Local, review-only task evaluation and change tracking. Python 3.11+."""
from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile


def stamp() -> str:
    return datetime.now(timezone.utc).isoformat()


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=".evolution-", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as out:
            json.dump(value, out, indent=2)
            out.write("\n")
        os.replace(temporary, path)
    finally:
        Path(temporary).unlink(missing_ok=True)


def evaluate(records: list[dict]) -> dict:
    """Evaluate verification outcomes, rather than a model's self-reported success."""
    if not isinstance(records, list) or len(records) > 10000:
        raise ValueError("Expected at most 10,000 task records")
    failures: Counter[str] = Counter()
    verified = 0
    durations = []
    for item in records:
        if not isinstance(item, dict) or type(item.get("verified")) is not bool:
            raise ValueError("Each record requires a boolean verified field")
        verified += int(item["verified"])
        if not item["verified"]:
            category = item.get("failure_category", "unclassified")
            if not isinstance(category, str) or len(category) > 80:
                raise ValueError("Invalid failure category")
            failures[category] += 1
        elapsed = item.get("duration_seconds")
        if elapsed is not None:
            if type(elapsed) not in (int, float) or not 0 <= elapsed <= 86400:
                raise ValueError("Invalid duration")
            durations.append(elapsed)
    return {
        "evaluated_at": stamp(), "total": len(records), "verified": verified,
        "verification_rate": verified / len(records) if records else None,
        "mean_duration_seconds": sum(durations) / len(durations) if durations else None,
        "recurring_failures": dict(failures.most_common()),
        "measurement": "caller-supplied verification outcomes; not independently certified",
    }


def candidate(patch: Path, output: Path, description: str) -> dict:
    if patch.is_symlink() or not patch.is_file() or patch.stat().st_size > 2_000_000:
        raise ValueError("Patch must be a regular file below 2 MB")
    contents = patch.read_bytes()
    record = {
        "created_at": stamp(), "description": description[:2000],
        "patch_sha256": hashlib.sha256(contents).hexdigest(),
        "patch_file": patch.name, "status": "awaiting-human-review",
        "activation": "Not supported: apply reviewed changes through version control",
        "security_control_review_required": True,
    }
    write_json(output, record)
    return record


def regress(repository: Path, output: Path, timeout: int = 120) -> dict:
    repository = repository.resolve(strict=True)
    if not repository.is_dir() or not 1 <= timeout <= 600:
        raise ValueError("Choose a repository directory and a timeout of 1–600 seconds")
    # This is a developer-invoked CLI, never an autonomous action adapter. Tests
    # execute repository code: use a disposable lab when reviewing untrusted code.
    command = [sys.executable, "-m", "pytest", "-q", "--disable-warnings"]
    environment = {
        key: value for key, value in os.environ.items()
        if key in {"PATH", "SYSTEMROOT", "WINDIR", "TEMP", "TMP", "LANG"}
    }
    environment["PYTEST_DISABLE_PLUGIN_AUTOLOAD"] = "1"
    try:
        result = subprocess.run(command, cwd=repository, env=environment,
                                timeout=timeout, stdout=subprocess.DEVNULL,
                                stderr=subprocess.DEVNULL, shell=False)
        report = {"passed": result.returncode == 0, "returncode": result.returncode,
                  "timed_out": False}
    except subprocess.TimeoutExpired:
        report = {"passed": False, "returncode": None, "timed_out": True}
    # Test stdout can contain secrets. Store only outcome metadata.
    report.update({"evaluated_at": stamp(), "command": command,
                   "timeout_seconds": timeout, "activation_permitted": False})
    write_json(output, report)
    return report


def manifest(repository: Path, output: Path, version: str) -> dict:
    repository = repository.resolve(strict=True)
    if not repository.is_dir() or not version or len(version) > 120:
        raise ValueError("Repository and version are required")
    ignored = {".git", ".venv", "venv", "node_modules", "dist", "build", "__pycache__", ".pytest_cache", "data"}
    extensions = {".py", ".tsx", ".ts", ".jsx", ".js", ".css", ".html", ".md", ".toml"}
    files = {}
    for path in sorted(repository.rglob("*")):
        relative = path.relative_to(repository)
        if any(part in ignored or part.startswith(".") for part in relative.parts):
            continue
        if path.is_symlink() or not path.is_file() or path.suffix not in extensions:
            continue
        if path.resolve() == output.resolve():
            continue
        if path.stat().st_size > 5_000_000:
            raise ValueError(f"Source exceeds manifest limit: {relative}")
        files[relative.as_posix()] = hashlib.sha256(path.read_bytes()).hexdigest()
    result = {"version": version, "created_at": stamp(), "source_sha256": files,
              "scope": "source fingerprint only, not a backup or complete deployment manifest",
              "rollback": "Restore your reviewed Git commit and preserved database backup; this tool never modifies source or security policy."}
    write_json(output, result)
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="operation", required=True)
    score = sub.add_parser("score")
    score.add_argument("records", type=Path)
    score.add_argument("output", type=Path)
    patch = sub.add_parser("candidate")
    patch.add_argument("patch", type=Path)
    patch.add_argument("output", type=Path)
    patch.add_argument("--description", required=True)
    test = sub.add_parser("regress")
    test.add_argument("repository", type=Path)
    test.add_argument("output", type=Path)
    test.add_argument("--timeout", type=int, default=120)
    version = sub.add_parser("manifest")
    version.add_argument("repository", type=Path)
    version.add_argument("output", type=Path)
    version.add_argument("--version", required=True)
    args = parser.parse_args()
    if args.operation == "score":
        result = evaluate(json.loads(args.records.read_text()))
        write_json(args.output, result)
    elif args.operation == "candidate":
        result = candidate(args.patch, args.output, args.description)
    elif args.operation == "regress":
        result = regress(args.repository, args.output, args.timeout)
    else:
        result = manifest(args.repository, args.output, args.version)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
