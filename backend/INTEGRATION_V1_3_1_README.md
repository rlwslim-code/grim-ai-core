# GRIM AI 1.3.1 — SHADOW AWAKENING

Incremental patch on 1.3.0; preserves all previous endpoints and data schemas.

## New functional APIs

- `GET /api/shadow/status` (Bearer token): reports isolated lab state, local SOCKS5 proxy handshake and discovery-only inventory of security tools. A successful SOCKS5 handshake does **not** establish real Tor egress. No `.onion` content is accessed.
- `POST /api/shadow/inspect` (Bearer token, JSON `{ "data_base64": "..." }`): bounded read-only static identification, SHA-1/SHA-256, limited literal indicators (not a malware verdict). Maximum 2 MiB decoded. No file is executed or stored. Owner-level audit records only SHA256 and byte count.

## Security properties

Tor diagnostic only connects to loopback. No arbitrary host scanning or direct dangerous tool execution is exposed. Arsenal entries are `invokable=false` even when their executable is found. Existing backend authentication, emergency stop, audit and Docker isolation are retained.

## Setup

1. Deploy GRIM CORE to your own HTTPS-capable Python host with **persistent disk**. Vercel's static frontend does not host this service. Store `.env` secrets server-side, never in the React build.
2. Configure `GRIM_ALLOWED_ORIGINS=https://grim-ai-dark-genesis.vercel.app` on the backend and other explicitly authorized origins if needed.
3. In the Vercel web project set `VITE_API_URL=https://YOUR-BACKEND-HOST` and redeploy, after your backend has been tested. This variable is public and must **not** contain an API key.
4. For optional local SOCKS5 checks only, set `GRIM_TOR_PROXY_HOST=127.0.0.1` and `GRIM_TOR_PROXY_PORT=9050` on the backend. Tor installation/configuration is external and not included.
5. The first registration can bootstrap the owner if no users exist. `GRIM_ALLOW_REGISTRATION=1` is required to allow more registrations; use restrictive signup policies for internet-facing deployment.

## Tested locally for this patch

`python -m pytest -q backend/tests evolution/tests` -> 37 passed, 1 skipped.
`npm ci --offline` -> failed (Vite 6.4.4 not present in local npm cache). Web production build **not run**; Expo build **not run**. No live Tor/Docker/model or remote hosting test was performed.

## Mobile

Mobile source is unchanged in this increment; it remains on the shared V1.3 API and will gain Shadow Gateway screens only after backend deployment and validation.

## Next blockers

Backend persistent hosting; backend HTTPS URL; real provider configuration; strong public signup policy; verified device build; optional independently isolated Kali tool worker. Nothing in this patch deploys itself to Vercel or GitHub.
