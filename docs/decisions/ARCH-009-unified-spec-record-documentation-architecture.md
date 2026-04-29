# ARCH-009: Unified Spec/Record Documentation Architecture

**Date:** 2026-04-15  
**Status:** accepted  
**ADR Version:** 1.0.0  
**Last Updated:** 2026-04-16  
**Owners:** Briefly engineering team

---

## Context

As implemented features grew, docs diverged in structure and quality. The project introduced broad migration to standardized spec/record formats to keep implementation intent, acceptance criteria, and delivery evidence consistent across features.

## Decision

We will maintain a unified documentation architecture where each significant feature uses standardized `spec` and `record` documents, and architectural decisions are tracked in versioned ADRs under `docs/decisions`.

## Rationale

- Standard templates improve consistency and reduce omission risk.
- Linking spec -> record -> ADR improves traceability across planning and implementation.
- Supports long-term maintenance as code and decisions evolve.

## Alternatives Considered

| Option | Why rejected |
|---|---|
| Free-form per-feature docs | Inconsistent completeness and difficult cross-feature review. |
| Spec-only docs (no implementation records) | Loses post-implementation rationale and verification evidence. |
| Code-only history without docs governance | Architectural intent becomes hard to recover over time. |

## Consequences

**Positive:**
- Better doc discoverability and change auditing.
- More reliable handoff across contributors.
- Explicit baseline for versioning architecture docs.

**Negative / trade-offs:**
- Documentation overhead for each significant change.
- Requires active upkeep to prevent drift.

## Related git history

- 2026-04-13 `c0b868b`: Broad spec alignment pass established structured documentation trajectory.
- 2026-04-14 `e29ad19`: Record creation plus dependency/spec mismatch correction reinforced traceability.
- 2026-04-15 `7c3ae97`: Full migration to unified spec/record format completed.
- Source scope: `main`

## Revision History

| Version | Date | Changes | Commit |
|---|---|---|---|
| 1.0.0 | 2026-04-16 | Initial ADR from expanded git-history + codebase scan | 7c3ae97 |

## Related

- Specs affected: `docs/specs/SEC-001.md`, `docs/specs/QOL-001.md`
- Other ADRs: `ARCH-001`, `ARCH-004`
