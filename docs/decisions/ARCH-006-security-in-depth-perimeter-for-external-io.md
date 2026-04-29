# ARCH-006: Security-in-Depth Perimeter for External IO

**Date:** 2026-04-14  
**Status:** accepted  
**ADR Version:** 1.0.0  
**Last Updated:** 2026-04-16  
**Owners:** Briefly engineering team

---

## Context

Briefly fetches arbitrary external URLs during ingestion and exposes internet-facing auth/content APIs. As the system moved from MVP to multi-user operation, abuse and isolation risks required a consistent security baseline across routes, HTTP clients, and configuration.

## Decision

We will enforce a security-in-depth perimeter consisting of: strict startup secret validation, centralized SSRF-protected external fetch path, pooled/thread-safe HTTP client usage, and API rate limiting/security headers at the application boundary.

## Rationale

- A single control is insufficient for internet-facing ingestion and auth surfaces.
- Centralized IO policy reduces bypass risk from ad hoc HTTP calls.
- Fail-fast config validation prevents insecure runtime states.

## Alternatives Considered

| Option | Why rejected |
|---|---|
| Endpoint-by-endpoint ad hoc hardening | Inconsistent and prone to coverage gaps as features expand. |
| Network perimeter only (no app-layer checks) | Does not protect against logic-level abuse in application flows. |
| Defer security to post-MVP | Risk profile already high with OAuth + external fetch + multi-user data. |

## Consequences

**Positive:**
- More consistent protection for ingestion/auth endpoints.
- Lower chance of accidental insecure code paths.
- Clear security baseline for future features and reviews.

**Negative / trade-offs:**
- Additional implementation complexity and operational configuration burden.
- Some legitimate requests may be blocked by stricter SSRF/rate-limit policy.

## Related git history

- 2026-04-14 `e90a0bd`: SSRF hardening expanded with DNS rebinding prevention checks.
- 2026-04-14 `3ea2770`: API-level rate limiting added for abuse control.
- 2026-04-14 `3353e36`: HTTP client pool made thread-safe for concurrent runtime safety.
- 2026-04-14 `b50cf57`: JWT secret became required env config (fail-fast security posture).
- Source scope: `main`

## Revision History

| Version | Date | Changes | Commit |
|---|---|---|---|
| 1.0.0 | 2026-04-16 | Initial ADR from expanded git-history + codebase scan | e90a0bd, 3ea2770, 3353e36, b50cf57 |

## Related

- Specs affected: `docs/specs/SEC-001.md`, `docs/specs/ING-001.md`
- Other ADRs: `ARCH-001`, `ARCH-002`, `ARCH-003`
