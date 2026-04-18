# ARCH-004: Web Dashboard Migration from Vue 3 to React 18

**Date:** 2026-04-15  
**Status:** accepted  
**ADR Version:** 1.0.0  
**Last Updated:** 2026-04-16  
**Owners:** Briefly engineering team

---

## Context

The web dashboard was initially implemented in Vue 3. A large refactor migrated it to React 18 with updated routing/state patterns and expanded frontend E2E coverage.

## Decision

We will standardize the web dashboard on React 18 + React Router + Zustand + Vite, replacing the prior Vue 3 + Pinia implementation.

## Rationale

- Migration aligned dashboard implementation with ongoing frontend redesign work.
- React ecosystem/tooling and existing team workflows reduced iteration friction.
- The new structure integrates cleanly with Playwright multi-circle test strategy.

## Alternatives Considered

| Option | Why rejected |
|---|---|
| Keep Vue 3 + Pinia and incrementally patch | Higher dual-pattern overhead during active redesign and interoperability work. |
| Rewrite using Next.js | Added framework complexity not required for current SPA/API architecture. |
| Maintain both Vue and React in parallel | Unsustainable maintenance and testing burden. |

## Consequences

**Positive:**
- Unified dashboard architecture for new development.
- Cleaner component/test organization in current codebase.
- Better long-term consistency with frontend delivery direction.

**Negative / trade-offs:**
- Migration cost and churn in component/store/router layers.
- Team now fully committed to React-specific patterns and dependencies.

## Related git history

- 2026-04-14 `43a98d8`: Initial web dashboard feature landed.
- 2026-04-15 `95ec3d7`: Framework migration from Vue 3 to React 18 completed.
- 2026-04-15 `0f71867`: Migration record added, documenting design and trade-offs.
- 2026-04-15 `db94bf4`: Post-migration redesign and cross-layer test strategy expansion.
- Source scope: `main`

## Revision History

| Version | Date | Changes | Commit |
|---|---|---|---|
| 1.0.0 | 2026-04-16 | Initial ADR from git-history + codebase scan | 43a98d8, 95ec3d7, db94bf4 |

## Related

- Specs affected: `docs/specs/EXT-002.md`
- Other ADRs: `ARCH-001`, `ARCH-005`
