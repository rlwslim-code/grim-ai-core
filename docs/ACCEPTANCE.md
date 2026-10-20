# Initial acceptance evidence

This is a development release, not full acceptance of every requested capability. No paid service, live cloud deployment, GPU, Kali VM, or background microphone service was activated.

## Automated verification

Executed from the project root with Python 3.12 and dependencies pinned in `backend/requirements.txt`:

```text
python -m pytest backend/tests evolution/tests -q
20 passed, 1 warning in 1.58s
```

The remaining warning concerns the Starlette test-client/httpx dependency deprecation. The suite includes real API/storage/workspace/static-analysis integration, security boundary tests, scheduler tests, and evolution evaluation tests. A separate real loopback HTTP smoke passed via `scripts/smoke_http.py`. Chat persistence/provider-error unit tests substitute controlled model responses; they do not prove live inference.

| Acceptance criterion | Implementation | Verification / exact blocker |
| --- | --- | --- |
| Web application launches | React/TypeScript client | Strict TypeScript + Vite production build passed. Browser interactive QA blocked: Chromium and headless browser downloads returned truncated 0 MiB archives. Real loopback HTTP smoke passed: built web HTML, auth, actual Bandit task, stop rejection, logout revocation. |
| Expo application runs | Expo SDK 54 source | TypeScript, SDK dependency compatibility, and iOS + Android Metro exports passed. No physical device/emulator acceptance run performed here. |
| Both clients share backend | Same authenticated FastAPI API | Source/API integration verified; simultaneous physical mobile + web run pending. |
| AI conversations | OpenAI-compatible provider; default Ollama | No running model/provider configured in this environment; live response not tested. Missing provider returns an error, never a fabricated answer. |
| Memory persists | Encrypted SQLite; history and memory CRUD | Encryption, cross-process SQLite/key reopening, access isolation, history serialization, edit/delete tested. Live model conversation across application restarts pending. |
| Semantic retrieval | Optional compatible embedding model | Real embedding endpoint not exercised. Default lexical retrieval is labelled accordingly. |
| Voice input/output | Browser recognition/synthesis; mobile system speech | Microphone/system voices and device permissions require manual browser/device verification. No guaranteed custom voice model bundled. |
| Multistep planning | Model JSON planner + structured registry | Plan validation tested; live model-generated plan blocked by unavailable inference. |
| Permitted execution | Managed files, Bandit/AST analysis, Docker Python/pytest | Actual file + static-analysis multistep task passed. Docker CLI/daemon absent; no host execution fallback. |
| Generate and test small application | Model code generation plus workspace/Docker tools | Full workflow blocked by absent model + Docker. No successful app build is invented. |
| Isolated lab lifecycle | Networkless Docker containers; status/create/stop/reset | Infrastructure unavailable here. Containers explicitly distinguished from VM. Kali adapter reports awaiting infrastructure. |
| Real security analysis tool | Bandit plus GRIM AST analyzer | Static-analysis tests, real API AST findings, and real loopback Bandit B602 findings passed. External installed-tool discovery is not invocation support. |
| Execution progress/results | Persisted task events/status API and clients | Real API task reached completed with verification findings. |
| Emergency stop/security boundaries | Stop flag, task cancellation, sandbox cleanup, path confinement, auth | Rejection during stop, resume, token revocation, path checks, denied host shell tested. Real in-flight container kill remains unverified without Docker. |
| Automated tests | Backend + evolution tests | 20 passed at final verification snapshot. |

## Additional modules

- Personality: OBSIDIAN, BLOODLINE, ABYSS system policies and simulated-expression presentation; no consciousness claim.
- Scheduling: encrypted persistent one-shot API schedules with timezone validation, emergency-stop waiting, and interrupted-claim recovery. Requires a running single backend process; no recurring scheduling or cloud scheduler.
- Evolution: standalone review-only CLI records verified outcomes, recurring failures, candidate patch hashes and fixed regression-command results. Six tests pass as part of the combined suite. It does not activate changes or fine-tune a model.
- Ghost: auth/session revocation and emergency stop foundations only. VPN configuration, region switching, incident detection and automated lockdown are not implemented.
- Malware research: static source inspection and future disposable execution interface only. No binary detonation, ransomware simulator, dedicated forensic toolchain, or installed Kali tool suite is claimed.
- Browser automation, document ingestion, recurring schedules, model fine-tuning, automatic recovery, push delivery, Siri App Intents extension, native continuous speech recognition and background wake services remain extension work.

## Required next acceptance run

On a development computer, start Ollama, pull the configured model, build the sandbox image, and run the API/web client. Test one chat with retrieved memory, one model-generated two-step plan, one generated app with passing tests inside Docker, one real container timeout/stop, and one lab create/reset/stop. Connect Expo on a physical device to the same backend and verify sign-in, history, speech, biometric availability, and reconnect behavior.

Record actual provider, model, hardware, device/browser versions, commands and outcomes. Re-run tests after any code changes. Keep this matrix honest when promoting the release.
