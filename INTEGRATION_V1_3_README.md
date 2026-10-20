# GRIM AI V1.3.0 — PROJECT AWAKENING

This is an incremental update on the existing GRIM AI V1.2.2 application. Keep the three archive directory layouts; they are not three unrelated apps.

## Release delta
- CORE: server-side bounded AI-assisted task repair. `/api/tasks` accepts `auto_repair` (boolean, default false). When enabled, after an actual failed tool result GRIM may request **one** replacement tool call from the configured inference provider and retry. Maximum of **two** repair calls per failing step, maximum original plan length 12. Repairs are checked against the existing tool allowlist and run under existing Docker/tool permissions. Task events persist each attempt, the verification result, and repair planning. Unavailable sandbox errors are not retried. No host shell was added.
- WEB: terminal's task submission exposes an opt-in repair toggle (enabled in UI by default). Execution progress remains tied to persisted backend tasks.
- MOBILE: newly submitted planned tasks request bounded model repair. Existing Expo speech playback is retained; native speech recognition has not been added.
- Backend automated tests: **25 passed, 1 skipped** in this environment, including four V1.3 repair and authorization checks.

## Integration
1. Extract CORE, WEB, and MOBILE into sibling directories (each archive already contains `backend/`, `web/`, or `mobile/` respectively). Never overwrite production data or the existing database file.
2. For local development, create a Python environment, install `backend/requirements.txt`, configure `GRIM_DATA_DIR`, `GRIM_ENCRYPTION_KEY`, and your model inference provider as detailed in CORE's original README / `.env.example`. Do not commit secrets.
3. `cd CORE_ROOT && python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000`. For device testing, the API must be reachable from the phone via your private network or an HTTPS endpoint with valid credentials.
4. Build the existing isolated execution image using `infra/Dockerfile.sandbox` and configure Docker on a trusted server; Docker is mandatory for `python`/`pytest` execution. Do not mount the Docker socket into user workspaces.
5. `cd WEB_ROOT/web && npm ci && npm run build`; configure `VITE_GRIM_API_URL` using the existing `.env.example` instructions.
6. `cd MOBILE_ROOT/mobile && npm ci && npx expo start`; set backend URL from GRIM mobile settings. SDK native module support depends on Expo Go versus custom dev builds.
7. Run backend tests: `cd CORE_ROOT && PYTHONPATH=. python -m pytest -q backend/tests`.

## Verified limitations
- AI repair requires an actually configured, accessible inference provider. Model requests and real Docker execution were **not** exercised here.
- Docker, Kali VM, Nmap, ZAP, mobile microphone transcription, continuous wake word, and neural speech were **not** activated by this update.
- Web build and Expo TypeScript compilation were attempted but could not pass: npm dependencies were not installed in this environment; TypeScript reported missing React/Expo type definitions and Expo config. These are *not* considered successful builds.
- A successful `pytest` result validates backend logic only; it does not establish live platform integration.
- Existing tests show one explicitly skipped test. No live payments, production deployments, or external attacks were performed.
