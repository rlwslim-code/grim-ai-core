# GRIM V1.1 — Audit and inference readiness patch

## Verified locally
- Source archive contained 50 files across FastAPI, React/Vite, Expo, sandboxing, lab adapters, tests and documentation.
- Baseline tests: **19 passed, 1 skipped** in the available Python environment.
- After patch: **21 passed, 1 skipped**.
- This is a source and test verification, **not** a cloud deployment, physical-device test, or proof of functional AI inference.

## Changes from V1
- Added `ModelProvider.readiness()` to verify the configured OpenAI-compatible `/models` endpoint, including whether the selected model is listed and a response-latency measurement.
- Changed authenticated `/api/status` so model verification reflects the live endpoint instead of always displaying `configured=true, verified=false`.
- Added readiness tests for unavailable and reachable model endpoints.
- Endpoint failures are reported as unavailable without disclosing API keys.

## Remaining blockers
- GRIM chat requires a reachable compatible model service; no free cloud GPU or API access is bundled.
- Execution of project Python and pytest requires Docker and the configured sandbox image on the backend host.
- Lab management requires Docker; Kali Linux VM requires compatible virtualization infrastructure.
- Browser voice features depend on browser capabilities and permissions; iOS third-party always-on wake words are not available system-wide.
- Expo voice output is not microphone transcription. Physical iPhone build and testing remain unverified.
- Hosting, HTTPS, and secure remote exposure remain to be configured.

## Validation command
`python -m pytest -q backend/tests evolution/tests`

## Safe next steps
1. Provision a reachable backend with HTTPS and a compatible model endpoint.
2. Verify `/api/status` after authentication: check `model.health`, sandbox state and tool availability.
3. Test real web and Expo clients against that backend; exercise chat, memory, lab status, permitted task execution and emergency-stop behavior.
