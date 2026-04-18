# ARCH-001: Async FastAPI + SQLAlchemy Repository Backend

**Date:** 2026-04-12  
**Status:** accepted  
**ADR Version:** 1.0.0  
**Last Updated:** 2026-04-16  
**Owners:** Briefly engineering team

---

## Context

Briefly needed to ingest shared links, extract metadata, run optional AI summarization, and serve swipe/content APIs quickly with a small team. The early implementation also needed clear boundaries for testing and rapid feature additions across UX, AI, auth, and integrations.

## Decision

We will use an asynchronous FastAPI backend with SQLAlchemy async sessions and a repository/service layer for data access and domain logic.

## Rationale

- Async request handling matches IO-heavy workloads (HTTP extraction, OAuth, AI service calls).
- FastAPI provides typed request/response contracts and predictable API development speed.
- Repository/service separation keeps route handlers thin and improves testability and refactoring safety.

## Alternatives Considered

| Option | Why rejected |
|---|---|
| Flask (sync) + ad hoc SQL | Lower built-in typing and weaker fit for concurrent IO-heavy endpoints. |
| Django monolith ORM-first | Higher framework overhead and less aligned with current lightweight API-first scope. |
| Direct SQL in route handlers | Faster initially but increases coupling and regression risk as feature set grows. |

## Consequences

**Positive:**
- Consistent async patterns across API, DB, and integrations.
- Better maintainability from explicit repository/service boundaries.
- Easier onboarding via clear layer responsibilities.

**Negative / trade-offs:**
- Async complexity (lifecycle cleanup, task handling) must be managed carefully.
- Repository abstraction adds boilerplate for small/simple queries.

## Related git history

- 2026-04-12 `c816762`: Initial backend card-stack API foundation (route/service/repository baseline).
- 2026-04-12 `ae06bbb`: Swipe persistence API reinforced service/repository layering.
- 2026-04-13 `bf0e8f8`: Share ingestion API added IO-heavy async workload on same backend architecture.
- 2026-04-14 `56dafb0`: Lifespan cleanup refined async lifecycle responsibilities.
- Source scope: `main`, `reflog`

## Revision History

| Version | Date | Changes | Commit |
|---|---|---|---|
| 1.0.0 | 2026-04-16 | Initial ADR from git-history + codebase scan | c816762, ae06bbb, e8d5b76 |

## Related

- Specs affected: `docs/specs/UX-001.md`, `docs/specs/UX-002.md`, `docs/specs/ING-001.md`, `docs/specs/DAT-001.md`
- Other ADRs: `ARCH-002`, `ARCH-003`, `ARCH-005`
