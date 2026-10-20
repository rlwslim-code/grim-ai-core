# GRIM EVOLUTION: review-only evaluation

Run from the project root with the backend virtual environment active:

```sh
python -m evolution.evaluate score task-outcomes.json evaluation.json
python -m evolution.evaluate candidate proposed.patch candidate.json --description 'Retry transient provider failures'
python -m evolution.evaluate manifest . source-version.json --version 1.0.0
python -m evolution.evaluate regress backend regression.json --timeout 120
python -m pytest evolution/tests -q
```

Task outcome input is a JSON array of records with boolean `verified`, optional `failure_category`, and optional nonnegative `duration_seconds`. The scorer reports actual verification fields, recurring failure categories, and average durations. It cannot independently prove caller-provided measurements.

Candidate registration hashes a patch and records its pending human review status. It does not apply patches, activate models, or modify security controls. Source manifests fingerprint supported source files; they are not backups. Preserve Git commits, encrypted application data, and its encryption key separately for rollback.

The regression CLI runs a fixed `python -m pytest` command without a shell, with a time limit and a reduced environment. It is an explicit developer operation and is not exposed to the autonomous executor. Repository tests execute code; select trusted code or invoke this CLI inside a disposable laboratory. Test output is not persisted because it may contain secrets. Pytest plugin autoload is disabled; repositories requiring plugins must load reviewed plugins through their own pytest configuration.

Not implemented: fine-tuning jobs, model comparisons on a curated benchmark, autonomous patch generation, automatic activation, automatic rollback, or a live backend integration. These utilities provide a controlled baseline for subsequent development.
