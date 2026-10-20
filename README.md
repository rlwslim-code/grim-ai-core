> V1.1 verification and changes: [docs/V1_1_AUDIT.md](docs/V1_1_AUDIT.md)

# GRIM AI — DARK GENESIS

**1.0 — THE AWAKENING · THE DARKNESS ANSWERS.**

An integrated development package: FastAPI backend, persistent encrypted SQLite memory, replaceable OpenAI-compatible model provider, three personality modes, structured task execution, persistent one-shot schedules, Docker laboratory controls, React web client, and Expo mobile client.

This release uses an existing language model. It is not an independently trained model. Personality and emotional expression are simulated.

## Start locally

Prerequisites: Python 3.11+, Node.js, and a computer capable of running the backend. Docker is optional for sandbox execution. Ollama or a compatible inference endpoint is required for AI responses. An iPhone alone cannot host this backend or a Kali VM.

From this directory:

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate
# macOS/Linux:
source .venv/bin/activate
pip install -r backend/requirements.txt
cp .env.example .env
# Install Ollama separately, then:
ollama pull qwen2.5:3b
# Export the .env values into your shell, or use:
uvicorn backend.main:app --host 127.0.0.1 --port 8000 --env-file .env
```

In a second terminal:

```bash
cd web
npm install
npm run dev
```

Open the Vite address printed by the command, configure the backend if requested, and register the first account. The first account bootstraps the owner. Keep the backend bound to localhost during bootstrap. Registration is disabled after bootstrap unless explicitly enabled.

For the mobile app, follow [mobile/README.md](mobile/README.md). Set its backend URL to the development computer's LAN address, not `localhost`. Exposing the API to other devices requires binding to the LAN and allowing the port through the local firewall. Use HTTPS for remote access; do not expose a plaintext development server to the public internet.

## Enable isolated execution

```bash
docker build -t grim-sandbox:1 -f infra/Dockerfile.sandbox .
```

Docker must be installed, running, and accessible to the backend process. GRIM never substitutes host Python or an unrestricted host terminal when Docker is unavailable. Workspace file operations and static analysis use constrained backend-managed paths; code execution occurs only in disposable containers. See [docs/SECURITY.md](docs/SECURITY.md).

## Verify

```bash
python -m pytest backend/tests evolution/tests -q
cd web
npm run build
cd ..
# Real loopback API + built-web smoke:
python scripts/smoke_http.py
```

Device-dependent voice, Expo execution, real inference, and Docker lifecycle checks require their respective infrastructure. Passing unit tests does not establish those capabilities as tested. See [docs/ACCEPTANCE.md](docs/ACCEPTANCE.md) for the release evidence.

## Project structure

- `backend/`: authenticated API, SQLite store, model interface, planner, executor, labs, automated tests.
- `web/`: React/TypeScript browser application with supported browser speech input/output.
- `mobile/`: Expo/TypeScript client controlling the same API.
- `infra/`: constrained sandbox image.
- `docs/`: security boundary, infrastructure, acceptance evidence, voice integrations.

See [docs/SCHEDULING.md](docs/SCHEDULING.md) for persistent one-shot schedules. Run a single backend worker.

Runtime databases, encryption keys, tokens, and API keys are excluded from the source archive. Back up the runtime data directory and its encryption key together. Losing the key makes encrypted content unreadable.

No paid resources are activated. Local software can be used without a subscription, but still requires existing hardware, internet for installation/model download, storage, and electricity. Always-on cloud compute, cloud GPUs, App Store distribution, and a hardware-virtualized Kali VM are not provisioned by this package.

### V1.2.2
Backend adds authenticated bounded workspace ZIP export (`/api/workspace/export`), owner-scoped task cancellation (`POST /api/tasks/{id}/cancel`) and conversation deletion (`DELETE /api/conversations/{id}`). Web Terminal can export project source files; web and mobile can cancel active individual tasks. See `INTEGRATION_V1_2_README.md` for validation and platform limitations.
