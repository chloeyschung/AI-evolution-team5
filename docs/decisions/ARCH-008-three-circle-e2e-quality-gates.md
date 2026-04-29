# ARCH-008: Three-Circle E2E Quality Gates

**Date:** 2026-04-15  
**Status:** accepted  
**ADR Version:** 1.0.0  
**Last Updated:** 2026-04-16  
**Owners:** Briefly engineering team

---

## Context

Frontend redesign and multi-surface behavior increased risk of regressions between UI, API, and persistence. A single E2E layer did not isolate where failures originated.

## Decision

We will use a three-circle E2E test strategy: Circle 1 (frontend-only), Circle 2 (backend+frontend integration), Circle 3 (DB+backend+frontend full stack), with dedicated Playwright configs and scripts.

## Rationale

- Layered circles localize failures quickly (UI vs API vs persistence boundary).
- Keeps fast feedback for pure frontend changes while preserving full-stack confidence.
- Aligns with active dashboard/extension delivery cadence.

## Alternatives Considered

| Option | Why rejected |
|---|---|
| Single full-stack E2E suite only | Slower debugging and higher run cost for all changes. |
| Unit/integration tests only, no E2E layering | Insufficient confidence for cross-surface user flows. |
| Manual QA only | Not reliable for frequent frontend iterations. |

## Consequences

**Positive:**
- Better regression detection across boundaries.
- Faster diagnosis via explicit test-layer ownership.
- Sustainable quality gates for rapid UI iteration.

**Negative / trade-offs:**
- Additional maintenance for multiple configs and seed/setup paths.
- Potential overlap between circle scenarios if test design drifts.

## Related git history

- 2026-04-15 `95ec3d7`: React migration raised cross-layer regression risk and test surface.
- 2026-04-15 `db94bf4`: Three-circle Playwright E2E strategy introduced and wired into scripts/config.
- Source scope: `main`

## Revision History

| Version | Date | Changes | Commit |
|---|---|---|---|
| 1.0.0 | 2026-04-16 | Initial ADR from expanded git-history + codebase scan | db94bf4 |

## Related

- Specs affected: `docs/specs/EXT-002.md`
- Other ADRs: `ARCH-004`, `ARCH-005`
