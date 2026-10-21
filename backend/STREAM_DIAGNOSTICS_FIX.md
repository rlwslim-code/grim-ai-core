# GRIM streaming diagnostics repair

Based on the prior Render startup fix. No database migration or frontend replacement.

- Log the full unexpected Python exception traceback to Render logs (`grim.stream`).
- Log classified provider failures with diagnostic category.
- Reject successful-but-empty model responses before persisting messages.
- Emit an explicit `done` SSE event after successful completion.

## Deploy
Replace the backend repository contents with this updated archive (or copy the modified files `backend/main.py` and `backend/core.py`) and redeploy the existing Render service. Preserve Render environment variables and any persistent storage.

## Verify
Send one message to GRIM LIVE, then inspect Render logs around `GRIM STREAM: Model generation started`. If it fails, the next lines should now reveal a provider failure category or an `Unexpected GRIM streaming failure` traceback. Never share API keys or secret values.

Validation: `python -m compileall -q backend` and `python -m pytest backend/tests -q`: 31 passed, 1 skipped.
