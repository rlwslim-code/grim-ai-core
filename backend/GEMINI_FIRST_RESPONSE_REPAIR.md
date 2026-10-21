# GRIM AI — Gemini First Response Recovery

This release builds on the latest Provider 404 Diagnostic Repair, preserving the backend and web UI.

## Fixes
- Keeps the existing safe HTTP error classifier (no `ResponseNotRead` secondary exception).
- On a Gemini chat-completions 404, requests the actual list of models available to the configured Gemini API key via Google's `v1beta/models` endpoint.
- Selects a supported text-generation Gemini model, preferring Flash, and retries the streaming request once.
- Preserves all existing authentication, conversations, memory, personality modes, and streaming event format.
- If the API key cannot list models or the alternative fails, returns an explicit provider error rather than fabricating an answer.

## Deployment
1. Upload this repository tree to the existing `grim-ai-core` GitHub repository, keeping `backend/` at the repository root. Do not upload to the GRIM web repository.
2. Commit: `fix(grim): recover Gemini 404 streaming using available models`
3. Confirm Render deployed the new commit. Keep `GRIM_MODEL_BASE_URL=https://generativelanguage.googleapis.com/v1beta/openai`, `GRIM_MODEL_API_KEY` (secret), and `GRIM_MODEL` (your current selection).
4. In GRIM LIVE send `Hello GRIM. What can you do?` and inspect Render logs for `GRIM STREAM: Generation completed`.
5. If unsuccessful, copy the new `GRIM inference stream` warning and `Stream provider failure` message (never share API keys).

This cannot guarantee generation until Google's API accepts a model for your account. The automatic retry does not permanently change Render environment variables.

## Local verification
`python -m compileall -q backend`
`PYTHONPATH=. pytest -q backend/tests`
Results: 33 passed, 1 skipped.
