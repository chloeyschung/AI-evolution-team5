# ARCH-010: Transaction Boundary and Durability Checkpoints

**Date:** 2026-04-13  
**Status:** accepted  
**ADR Version:** 1.0.0  
**Last Updated:** 2026-04-16  
**Owners:** Briefly engineering team

---

## Context

As API flows expanded (share ingestion, integration sync, auth/session writes), transaction handling became inconsistent and produced double-commit/partial-persistence defects in earlier iterations. Some long-running flows also needed explicit log durability before request completion.

## Decision

We will use request-scoped DB session management as the default transaction boundary, while allowing explicit intermediate commits only where durability checkpoints are required (for example sync log persistence in long-running integration flows).

## Rationale

- Default request-scoped commit/rollback reduces accidental transaction fragmentation.
- Explicit checkpoint commits preserve operational logs and progress state when long-running work can fail later.
- Separating default vs exception paths makes transaction intent auditable.

## Alternatives Considered

| Option | Why rejected |
|---|---|
| Commit only inside every repository method | High risk of double-commit and unclear unit-of-work semantics. |
| Strict single commit only at request end (no exceptions) | Loses useful durability guarantees in long-running integration flows. |
| No explicit transaction policy | Reintroduced prior regressions and inconsistent behavior. |

## Consequences

**Positive:**
- Clearer baseline transaction behavior for most routes.
- Better failure observability via persisted sync logs/checkpoints.

**Negative / trade-offs:**
- Mixed commit patterns still require discipline and review.
- Incorrect checkpoint placement can still cause partial-state complexity.

## Related git history

- 2026-04-13 `f01fea5` (reflog/unreachable): Fix removed double-commit behavior in share endpoint path.
- 2026-04-14 `b5a4d75`: Explicit commit checkpoints added for sync-log durability.
- 2026-04-14 `56dafb0`: Shutdown/background-task cleanup tightened end-of-request/process consistency.
- Source scope: `main`, `reflog`, `unreachable`

## Revision History

| Version | Date | Changes | Commit |
|---|---|---|---|
| 1.0.0 | 2026-04-16 | Initial ADR from all-ref/reflog scan + current codebase validation | f01fea5, b5a4d75, 56dafb0 |

## Related

- Specs affected: `docs/specs/ING-001.md`, `docs/specs/INT-001.md`, `docs/specs/INT-002.md`
- Other ADRs: `ARCH-001`, `ARCH-006`, `ARCH-007`
