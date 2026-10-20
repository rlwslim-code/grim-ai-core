# Security configuration and boundaries

Use one trusted backend operator for this initial release. Owner/admin privileges and API authentication do not turn the development server into a hardened public multi-tenant service.

## Authentication and storage

Passwords are hashed; bearer sessions authenticate API requests. Treat session tokens as credentials. Configure TLS before network deployment, restrict allowed CORS origins, disable open registration, and bootstrap the first account on loopback. Logout revokes the active session. Do not place model keys in client applications.

Conversation and memory payloads are encrypted at rest with a generated Fernet key. The key lives beside the database under restrictive directory permissions; this protects against a database-only disclosure, not compromise of the server account or the whole data directory. Metadata is not all encrypted. Keep operating-system disk encryption and access controls enabled. Audit logs retain operation metadata without intentionally recording tokens or prompt bodies.

## Execution

The model produces structured tool plans. Tool names and arguments are validated independently; generated instructions cannot grant new permissions. There is no arbitrary host terminal adapter. Code execution requires Docker; unavailable infrastructure produces an error.

Sandbox containers run without network access, as a non-root user, with a read-only root filesystem, dropped capabilities, no-new-privileges, resource limits, timeouts, a bounded temporary directory, and a read-only project mount. They do not receive the Docker socket. The backend itself needs Docker authority and therefore remains a privileged trust boundary: protect its account and API.

Workspace file paths are confined to a configured managed directory. Do not share this directory with production applications or sensitive files. This is an initial implementation, not a hardened hostile multi-user execution platform. Keep untrusted high-risk samples out until a separately reviewed malware-analysis environment exists.

Emergency stop cancels the user's queued/running task loop and invokes sandbox cancellation. Resuming permits future operations; it does not silently retry cancelled tasks. Keep audit records after incidents. Stop is a control-plane action, not a guarantee against every external process or a compromised host.

## Cybersecurity scope

Real security analysis is provided by Bandit and a local static Python source analyzer. Bandit inspects managed workspace source without executing it. Installed external tools can be discovered; discovery is not an operational adapter. Do not infer that Nmap, ZAP, Metasploit, Ghidra, MobSF, AFL++, Wireshark, or Burp is integrated merely because its executable is detected.

Active network exploitation, credential theft, destructive payloads, covert surveillance, unrestricted malware execution, VPN routing, proxy endpoint switching, and anti-forensics are not implemented. Future adapters must validate configured authorization scopes outside the model, preserve logs, and receive independent review.

## Release limitations

There is no external security audit, production rate-limiting gateway, managed key service, high-availability queue, automated backup, or tenant-level container service isolation in this package. Do not activate automatic self-modification of these controls. Candidate changes should be reviewed, tested, committed, and rolled back using version control.
