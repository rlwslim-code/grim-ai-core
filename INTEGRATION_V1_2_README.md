# GRIM AI V1.2 — DARK GENESIS (incremental source release)

This release is built from the supplied `GRIM_AI_Dark_Genesis_V1_1_Audited(1).zip`. No original modules were replaced with unrelated stubs. The backend, web and mobile archives are **parts of the same project**, not independent inference services.

## Changes completed in V1.2
- OpenAI-compatible model provider: added real SSE token streaming (`POST /api/chat/stream`), categorized errors (`authentication_failure`, `rate_limit`, `network_failure`, `provider_error`, `execution_failure`), and up to four opt-in inference fallbacks.
- Backend: streamed chat authenticates via bearer token, uses stored conversation context and relevant memory, emits `meta`, `delta`, `done` and `error` SSE events, and saves completed turns in the existing encrypted database. Broken streams aren't persisted as completed answers.
- Web: real streaming GRIM CORE/LIVE reply rendering wired to backend SSE. Retains the existing glass UI, tasks, lab controls, terminal task planner and browser speech synthesis/recognition.
- Mobile: explicitly displays the configured provider model and its actual health category; keeps existing secure session, task, memory, voice-output and lab integrations.
- Tests: new mocked SSE wire-protocol, authentication failure and provider failover tests (no fake AI text masquerades as live inference).

## Configuration (backend)
Run from the common `GRIM_AI` root, with a **Python virtual environment**:

```sh
python -m pip install -r backend/requirements.txt
cp .env.example .env
# edit .env; keys must remain on the server
python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000
```

Use an actual reachable OpenAI-compatible inference endpoint. By default the backend expects Ollama at `http://127.0.0.1:11434/v1` with model `qwen2.5:3b` (pull/install it separately). `GRIM_MODEL_BASE_URL`, `GRIM_MODEL` and `GRIM_MODEL_API_KEY` select the primary endpoint.

Optional fallback example in `.env` (one line):

```
GRIM_MODEL_FALLBACKS=[{"base_url":"https://compatible-provider.example/v1","model":"a-real-model-id","api_key_env":"SECONDARY_MODEL_API_KEY"}]
```

Replace the illustrative URL with a real endpoint; specify `SECONDARY_MODEL_API_KEY` separately. This configuration is optional, not an active provider, and **does not activate paid services**. Fallback is attempted only on request failure before streaming text is emitted. A started but interrupted stream cannot transparently switch models mid-answer.

## Web
From `web/`, run `npm ci && npm run dev`, configuring `VITE_API_URL` (for example `http://localhost:8000`). Production: `npm run build`. The web server can also serve the existing `web/dist` if built artifacts are supplied; **rebuild dist to include V1.2 changes**.

## Mobile
From `mobile/`, run `npm ci && npx expo start` (SDK 54). Set `EXPO_PUBLIC_API_URL` to a reachable backend address. On a physical iPhone, `localhost` is the phone rather than a development computer. Keep API secrets server-side. Expo Go supports native speech output via `expo-speech`; microphone speech-to-text is *not yet integrated natively*. iOS platform-wide wake-word listening is not supported. Browser wake phrase works only with active browser recognition.

## Actual validation performed in this environment
`python -m pytest -q backend/tests evolution/tests`: **24 passed, 1 skipped**. The omitted test is an existing skip. Web and mobile dependency installation using offline npm cache failed with `ENOTCACHED` (missing Vite and yocto-queue packages), so neither TS/Vite build nor native compilation was verified. No Docker binary was present, so container-based execution and Kali lab availability were not tested. No real model endpoint, HTTPS host, physical iPhone, paid provider or runtime deployment was provisioned.

## Existing versus incomplete systems
Existing V1.1 modules provide encrypted SQLite storage, authenticated sessions, memory retrieval (semantic only if configured embedding endpoint exists), typed planning and guarded workspace tools, Docker-only container execution, emergency stop, Docker lab adapters, static security tools, and web/mobile clients. These capabilities remain conditional on infrastructure.

This **incremental release is not a complete realization of every V1.2 mission item**. Outstanding integrations include native live microphone transcription and interruption, a dedicated neural voice model, independent streaming terminal sessions, true VM snapshots/Kali virtualization, installable lab integrations, mobile push notifications, agent orchestration beyond the existing single planner, fully autonomous code repair, and a hosted always-on sandbox. Do not interpret UI tabs as proof of running infrastructure. `GET /api/status` and `/api/tools` report configured/detected conditions.

## Security boundaries
Use a dedicated isolated deployment. Do not mount the Docker socket inside a public container. Tasks accept allowlisted tools only and Python execution requires an isolated Docker sandbox image; the host shell is not exposed. Keep keys out of version control, configure HTTPS and origins before remote access, and do not enable untrusted guest access. `POST /api/emergency-stop` cancels tasks and stops owner containers.

## Continuation patch (V1.2.1)

This continuation adds a read-only, authenticated real task event stream at `GET /api/tasks/{task_id}/events`. It emits SSE snapshots only when the persisted task status/results change, stops when a terminal state is reached, and refuses requests for another account's task. It does not execute a host shell or fabricate output. Existing task history remains unchanged.

The mobile CORE screen now displays the 20 most recent saved conversations; select any to retrieve its messages from the shared authenticated backend. The web TERMINAL now stays on the terminal screen after launching a task and displays its current persisted execution state from the existing five-second task polling loop. These are incremental changes to the existing V1.2 applications, not a rewrite.

Verification: `python -m pytest -q backend/tests`: 19 passed, 1 skipped (continuation environment). This count is for the backend/tests directory, not the entire repository. No inference credentials or Docker daemon were available for end-to-end model/container tests. Web and mobile compilation have **not** been verified in this continuation environment. Install dependencies and run `npm ci && npm run build` inside web; `npm ci && npm run typecheck` inside mobile to verify. The mobile on-device behavior remains unverified.

SSE task events are available to any authenticated client using a standard fetch streaming reader. Native EventSource without auth headers will not work for this endpoint; use fetch with bearer token. Browser UI currently refreshes through authenticated polling, not this new SSE endpoint.

## V1.2.2 continuation — real deliverable operations

- `GET /api/workspace/export`: authenticated owner-scoped ZIP download of existing workspace source files; hidden paths and symlinks excluded; 500-file, 10 MiB total, and 256 KiB/file limits. No source execution or Docker required to export. Available from WEB's Terminal **Export workspace ZIP** button.
- `POST /api/tasks/{id}/cancel`: authenticated per-task cancellation request that cancels the executing coroutine and terminates the matching isolated container. This is distinct from the account-wide emergency stop. The web terminal and mobile task feed provide controls; final tasks reject cancellation with HTTP 409.
- `DELETE /api/conversations/{id}`: owner-scoped deletion of conversation and associated messages with an audit event; stored memory entries remain separate.

**Validation in this continuation:** `PYTHONPATH=. pytest -q backend/tests`: **21 passed, 1 skipped**. The new tests verify archive membership, exclusion of symlinks/hidden credentials, and size limits. Build verification for web and mobile is **not completed** because node_modules dependencies are absent; the updated client source is included but no claim of successful TypeScript or native compilation is made. A live inference provider, actual Docker daemon, native microphone and physical device remain untested. The archive API requires a reachable authenticated backend and a workspace belonging to the account. This release does not introduce a general-purpose host terminal.
