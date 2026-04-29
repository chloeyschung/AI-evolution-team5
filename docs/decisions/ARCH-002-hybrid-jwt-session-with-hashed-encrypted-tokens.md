# ARCH-002: Hybrid JWT Session with Hashed/Encrypted Tokens

**Date:** 2026-04-14  
**Status:** accepted  
**ADR Version:** 1.0.0  
**Last Updated:** 2026-04-16  
**Owners:** Briefly engineering team

---

## Context

Briefly needed Google OAuth login, stateless API authorization, token revocation support, and stronger storage security after code review findings. Integration providers (YouTube/LinkedIn) introduced additional sensitive token storage requirements.

## Decision

We will use a hybrid auth model: signed JWT access tokens for API calls, database-backed refresh tokens for rotation/revocation, hashed access-token storage, and encrypted third-party OAuth token storage at rest.

## Rationale

- JWT access tokens keep API auth fast and interoperable across clients.
- DB-backed refresh/session state enables revocation/logout and token rotation.
- Hashing and encryption reduce impact if database rows are leaked.

## Alternatives Considered

| Option | Why rejected |
|---|---|
| Pure server-side sessions only | Adds stateful coupling and weaker fit for extension/dashboard API clients. |
| JWT-only without token persistence | Revocation and logout guarantees are weaker. |
| Plaintext token storage in DB | Unacceptable security exposure for auth and integration credentials. |

## Consequences

**Positive:**
- Stronger session security while keeping client/API ergonomics.
- Revocation and rotation behavior is explicit and auditable.
- Better alignment with SEC-001 hardening goals.

**Negative / trade-offs:**
- More moving parts (JWT validation + DB checks + encryption key management).
- Key/config startup validation becomes mandatory for all environments.

## Related git history

- 2026-04-14 `a37f7b9`: Google social login introduced OAuth-based auth entrypoint.
- 2026-04-14 `2de431f`: Access-token hashing introduced for DB storage hardening.
- 2026-04-14 `80d36f9`: OAuth provider tokens moved to encrypted-at-rest storage.
- 2026-04-14 `c62d573`: JWT signature verification enforced in auth dependency path.
- Source scope: `main`

## Revision History

| Version | Date | Changes | Commit |
|---|---|---|---|
| 1.0.0 | 2026-04-16 | Initial ADR from git-history + codebase scan | a37f7b9, 2de431f, 80d36f9, c62d573 |

## Related

- Specs affected: `docs/specs/AUTH-001.md`, `docs/specs/AUTH-002.md`, `docs/specs/AUTH-003.md`, `docs/specs/AUTH-004.md`, `docs/specs/SEC-001.md`, `docs/specs/INT-001.md`
- Other ADRs: `ARCH-001`, `ARCH-003`
