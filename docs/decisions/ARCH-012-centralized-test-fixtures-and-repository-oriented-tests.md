# ARCH-012: Centralized Test Fixtures and Repository-Oriented Tests

**Date:** 2026-04-13  
**Status:** accepted  
**ADR Version:** 1.0.0  
**Last Updated:** 2026-04-16  
**Owners:** Briefly engineering team

---

## Context

Early test implementation duplicated setup logic and had isolation issues across API/data tests. Refactors introduced centralized fixtures and stronger repository-oriented test structure to reduce flakiness and maintenance cost.

## Decision

We will centralize shared test fixtures in common test setup modules and prefer repository/service-oriented test seams instead of ad hoc route-level setup duplication.

## Rationale

- Shared fixtures reduce inconsistent setup and hidden coupling.
- Repository/service-level seams improve determinism and isolate business/data logic.
- Better foundation for adding integration and E2E layers.

## Alternatives Considered

| Option | Why rejected |
|---|---|
| Per-test-file bespoke fixtures | High duplication and drifting setup behavior. |
| Route-only heavy integration tests for everything | Slower, harder to debug, and less targeted failures. |
| Mock-everything unit tests only | Insufficient confidence for persistence/query behavior. |

## Consequences

**Positive:**
- Improved test isolation and maintainability.
- Clearer contract between API, service, and repository layers in tests.

**Negative / trade-offs:**
- Fixture indirection can make some tests less immediately readable.
- Requires ongoing discipline when introducing new shared fixtures.

## Related git history

- 2026-04-13 `7a4cf1f` (reflog/unreachable): Centralized test fixtures and repository-oriented test refactor.
- 2026-04-13 `e8d5b76`: Mainline follow-up consolidated fixture usage patterns.
- 2026-04-14 `22df2ec`: Test DB fixture isolation fixes validated centralized test architecture.
- Source scope: `main`, `reflog`, `unreachable`

## Revision History

| Version | Date | Changes | Commit |
|---|---|---|---|
| 1.0.0 | 2026-04-16 | Initial ADR from all-ref/reflog scan + current test structure validation | 7a4cf1f, e8d5b76, 22df2ec |

## Related

- Specs affected: `docs/specs/QOL-001.md`, `docs/specs/UX-002.md`
- Other ADRs: `ARCH-001`, `ARCH-008`
