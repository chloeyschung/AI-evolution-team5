# ARCH-003: User-Scoped Multi-Tenant Data Isolation

**Date:** 2026-04-14  
**Status:** accepted  
**ADR Version:** 1.0.0  
**Last Updated:** 2026-04-16  
**Owners:** Briefly engineering team

---

## Context

Initial implementations used implicit/default user assumptions. As auth and integrations expanded, user-data isolation became mandatory to prevent cross-user leakage and to support real multi-user behavior.

## Decision

We will enforce user-scoped isolation across domain data by propagating `user_id` through models, repository methods, and endpoint queries, with user-scoped unique constraints where appropriate.

## Rationale

- Prevents cross-account data exposure in API and repository access paths.
- Supports secure growth from MVP assumptions to real multi-user usage.
- Makes ownership boundaries explicit in schema and service contracts.

## Alternatives Considered

| Option | Why rejected |
|---|---|
| Keep single-user (`user_id=1`) assumptions | Not safe for production multi-user scenarios. |
| Rely only on endpoint-level filtering | Easy to bypass accidentally in deeper repository paths. |
| Full DB row-level security policy layer | Overkill for current SQLite-centric deployment model and app complexity. |

## Consequences

**Positive:**
- Stronger tenant isolation invariants across routes and repositories.
- Cleaner future path to external DB engines and stricter policy enforcement.

**Negative / trade-offs:**
- More parameters and query complexity throughout data layer.
- Migration burden for legacy methods that previously omitted `user_id`.

## Related git history

- 2026-04-14 `2e010c5`: Added `user_id` to core domain tables with user-scoped uniqueness.
- 2026-04-14 `0573024`: Standardized protected route ownership via `Depends(get_current_user)`.
- 2026-04-14 `0e839ac`: Repository methods patched with user filtering for isolation.
- 2026-04-14 `7cbc0b8`: Removed hardcoded `user_id=1` parameterization defects.
- Source scope: `main`

## Revision History

| Version | Date | Changes | Commit |
|---|---|---|---|
| 1.0.0 | 2026-04-16 | Initial ADR from git-history + codebase scan | 2e010c5, 0e839ac, 7cbc0b8 |

## Related

- Specs affected: `docs/specs/DAT-002.md`, `docs/specs/SEC-001.md`, `docs/specs/AUTH-001.md`
- Other ADRs: `ARCH-001`, `ARCH-002`
