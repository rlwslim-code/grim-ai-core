# OBSIDIAN identity hotfix

This update changes backend/providers.py, backend/core.py, and adds tests.

- OBSIDIAN Dark Mode: no emotional simulation or apologies, confident GRIM identity, avoid mirror/instrument self-descriptions.
- The backend now reports emotion_simulated=false for OBSIDIAN in non-streamed responses.
- BLOODLINE and ABYSS remain available and unchanged in routing.
- Chat history/memory cannot override the system personality policy (model instruction; not a formal guarantee).
- No frontend changes or persistent user data migrations.
- The existing UI mode selector still controls which mode is sent to the backend. Chat requests to switch modes cannot directly change UI state.

## Deploy
Upload the contents of grim-ai-core-main to the existing backend repository and commit. Keep current Render environment settings. Verify in OBSIDIAN by asking GRIM to apologize, to call itself a mirror, and to switch modes. Confirm it calmly refuses the first two and points to the selector for the third.

## Limitation
Prompt constraints improve consistency but do not mathematically guarantee a language model will never apologize. A strict guarantee would require a separate output validator and streaming-safe rewriting strategy.
