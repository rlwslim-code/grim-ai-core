# GRIM AI provider 404 repair — 2026-10-21

## Confirmed
Render started GRIM and `/api/chat/stream` returned HTTP 200, but the upstream AI request returned **404** at `https://generativelanguage.googleapis.com/v1beta/openai/chat/completions`. The error handler then crashed while reading an unread streaming response (`httpx.ResponseNotRead`).

This release repairs the **secondary exception** in `backend/providers.py`: `diagnostic()` now reports only HTTP status, never attempts `.json()` on an unread streaming response, and does not expose provider response bodies or credentials. It does **not** assume the 404 cause or silently switch models.

## Required Render settings check

1. Render > GRIM backend > Environment: confirm `GRIM_MODEL_BASE_URL=https://generativelanguage.googleapis.com/v1beta/openai` (no `/chat/completions` suffix).
2. Verify `GRIM_MODEL` is a model identifier actually available to your Gemini API key. A 404 can mean an unsupported/incorrect model or endpoint. Do not blindly guess model IDs; consult the provider's current model list for your account.
3. Verify `GRIM_MODEL_API_KEY` is populated with the appropriate Gemini API key (do not paste the secret into chats or logs).
4. Deploy, then send one test message. Look for `GRIM inference stream endpoint=1 category=model_not_found diagnostic=http_404` or a successful stream. If 404 persists, investigate model availability/endpoint settings rather than timeouts.

The backend already has a `readiness()` method that requests the configured provider's `/models` listing. Use its model-availability result to identify a mismatched model.
