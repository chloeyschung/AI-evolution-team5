# ARCH-011: Conventional Commit Governance

**Date:** 2026-04-14  
**Status:** accepted  
**ADR Version:** 1.0.0  
**Last Updated:** 2026-04-16  
**Owners:** Briefly engineering team

---

## Context

Rapid iteration produced many commits across feature, refactor, and docs tracks. Without a stable commit taxonomy, history-to-doc traceability (spec/record/ADR linkage) degrades and review automation becomes harder.

## Decision

We will enforce conventional-style commit message format through a `commit-msg` git hook (`type(scope): message` or `type: message`) using an allowlisted set of change types.

## Rationale

- Enables reliable parsing of history for governance/reporting and ADR maintenance.
- Improves readability of dense commit streams.
- Creates a shared contract for contributors during high-frequency delivery.

## Alternatives Considered

| Option | Why rejected |
|---|---|
| Free-form commit messages | Lower consistency and weaker machine readability. |
| PR-title-only conventions without local hook | Enforcement too late and inconsistent across local workflows. |
| External CI enforcement only | Misses fast local feedback and correction before push. |

## Consequences

**Positive:**
- Better change traceability from commit history to docs.
- Cleaner classification of technical vs product changes.

**Negative / trade-offs:**
- Minor contributor friction for strict message formatting.
- Hook maintenance required if taxonomy evolves.

## Related git history

- 2026-04-14 `bb00397`: Added `commit-msg` hook enforcing conventional commit taxonomy.
- 2026-04-15 `7c3ae97`: Unified docs migration demonstrated downstream value of structured history.
- Source scope: `main`

## Revision History

| Version | Date | Changes | Commit |
|---|---|---|---|
| 1.0.0 | 2026-04-16 | Initial ADR from all-ref scan + hook validation | bb00397 |

## Related

- Specs affected: `docs/specs/QOL-001.md`
- Other ADRs: `ARCH-009`
