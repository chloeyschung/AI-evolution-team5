# ARCH-013: Unified Frontend Design System and Dense Data Shell

**Date:** 2026-04-17  
**Status:** accepted

---

## Context
Briefly now operates across multiple user-facing frontend surfaces (web dashboard + browser extension). Prior implementation had visual drift, duplicated styling decisions, and interaction inconsistencies that conflict with the project principles in `docs/MANIFEST.md` and `docs/mps.md` (Consumption over Collection, Radical Brevity, Guilt-Free Experience). Audit findings in `docs/audit/criticalquestions_Briefly.md` also highlighted frontend instability risks, especially around auth/navigation lifecycle and client-side state drift.

## Decision
We will standardize the web dashboard and browser extension on one tokenized design language and a data-dense shell architecture. The dashboard uses `NavRail + TopBar + MainViewport` with reusable primitives (`DataGrid`, `MetricCard`, `SlideDrawer`), and extension surfaces adopt aligned color/typography/spacing tokens.

## Rationale
- Creates a single visual and interaction source of truth across all frontend surfaces.
- Supports high-density information workflows (inbox triage, analytics, archive operations).
- Reduces risk from ad-hoc page-level styling and behavior divergence.

## Alternatives Considered

| Option | Why rejected |
|---|---|
| Keep per-page/per-surface custom styling | Continues drift and increases maintenance overhead |
| Retain card-first layouts for all workflows | Insufficient density and scan efficiency for large data sets |
| Full framework/style-system migration first (e.g. Tailwind-first refactor) | Excessive scope for current delivery timeline |

## Consequences

**Positive:**
- Consistent theme tokens and component behavior in dashboard + extension.
- Faster scan/comparison flows through sticky headers and table-like density.
- Better non-blocking context expansion via drawers.
- Extension auth/save flows now use class-driven token styling (reduced inline drift risk).

**Negative / trade-offs:**
- Larger initial refactor footprint.
- Requires ongoing governance to prevent token bypass styles.
- Some API-level pagination metadata gaps still need backend follow-up.

## Related
- Specs affected: `docs/specs/UX-001.md`, `docs/specs/UX-004.md`, `docs/specs/UX-005.md`, `docs/specs/ADV-001.md`, `docs/specs/ADV-002.md`, `docs/specs/ADV-003.md`
- Other ADRs: `ARCH-004-web-dashboard-migration-vue3-to-react18.md`, `ARCH-005-browser-extension-manifest-v3-service-worker.md`
