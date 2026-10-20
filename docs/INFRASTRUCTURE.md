# Infrastructure and deployment

## Zero-subscription development

Run the backend, web app, and Ollama on hardware you already own. A small quantized model may run slowly on a CPU and must fit available RAM/storage. Choose a smaller compatible model if necessary. The model name is configurable; local inference remains dependent on the installed model and host resources.

The default backend binds to loopback. The web client uses the same API as the mobile client. SQLite persists sessions, messages, memory, tasks, and audit metadata. Use a persistent data directory; an ephemeral free-tier container can lose state at shutdown.

Docker is optional infrastructure until sandbox execution or labs are needed. A GRIM container is not a virtual machine. Kali VM integration reports unavailable/awaiting infrastructure until a real virtualization adapter and hypervisor are configured. No cloud account or server is provisioned.

## Remote deployment checklist

1. Choose a host supporting a long-running Python process, durable storage, and your model endpoint. Docker execution additionally needs a deliberately isolated worker host with a supported daemon.
2. Put an HTTPS reverse proxy in front of the API. Keep its administrative bootstrap private; configure exact browser origins and closed registration.
3. Set provider URL/model and optional key on the server. Point both clients to the HTTPS API URL.
4. Back up the encrypted database and key securely. Test restoration.
5. Run acceptance tests on the chosen host, including timeout, emergency-stop, tenant boundaries, model errors, and device connectivity.

Free-tier inference services can change quotas, suspend inactive deployments, or require a billing account. No free-tier provider is configured or promised. The compatible provider interface allows one to be configured by its owner without rebuilding the clients.

## Remaining infrastructure

- Running inference server/model for real reasoning, planning, and AI conversation tests.
- Docker daemon/image for execution and real lab lifecycle verification.
- Physical iOS/Android devices or emulators for Expo and microphone testing.
- HTTPS endpoint and internet-reachable persistent host for cross-network use.
- Proper native iOS App Intents integration and Android background-service module for OS-level voice activation.
- Dedicated hypervisor/VM adapter for Kali and reviewed isolated detonation infrastructure for behavioral malware analysis.
- Push delivery credentials/device builds for push notifications; store developer accounts for distribution.

## Upgrades

PostgreSQL, embeddings/vector search, durable job workers, streaming model responses, approved browsing/research, document parsers, recurring schedules, evaluation gates, reviewed model fine-tuning, VPN management, forensic tools, and external security-tool invocation are extension work unless explicitly listed as implemented in the acceptance evidence.

Reference documentation: [Ollama](https://ollama.com/), [Docker security](https://docs.docker.com/engine/security/), [Expo](https://docs.expo.dev/). These links are setup resources, not evidence that those infrastructures were deployed.

## Optional Compose stack

`docker compose up --build -d` starts local API + CPU Ollama containers; then run `docker compose exec ollama ollama pull qwen2.5:3b`. This optional configuration was not executed during release verification. It keeps the API bound to loopback and persists data in volumes. The model image uses a moving upstream tag; pin its verified digest before relying on a reproducible deployment.

This API container intentionally has no Docker socket or Docker CLI. Sandbox/lab execution therefore remains unavailable in this configuration. For the initial execution workflow, run the API on the development host with the reviewed sandbox image. A separately authenticated remote worker is future work; do not mount the host daemon socket merely to make the UI show a running lab.

Optional semantic retrieval uses `GRIM_EMBEDDING_MODEL` against the same compatible model endpoint. Pull an embedding model separately. Without this setting, retrieval is lexical and labelled accordingly; embeddings were not exercised against a live provider in release verification.
