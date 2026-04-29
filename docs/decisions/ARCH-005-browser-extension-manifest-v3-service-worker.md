# ARCH-005: Browser Extension on Manifest V3 Service Worker Architecture

**Date:** 2026-04-14  
**Status:** accepted  
**ADR Version:** 1.0.0  
**Last Updated:** 2026-04-16  
**Owners:** Briefly engineering team

---

## Context

Briefly required a browser capture surface that can trigger auth, read current page context, and send share payloads to backend APIs. The extension also needed to run on modern Chromium browsers with current platform requirements.

## Decision

We will implement the extension using Chrome Manifest V3 with a background service worker, content script extraction, popup/login pages, and shared TypeScript modules built by Vite.

## Rationale

- Manifest V3 is the current supported architecture for Chromium extensions.
- Service worker + content script split cleanly separates page extraction from privileged extension flows.
- Shared modules reduce duplication across popup, login, and background flows.

## Alternatives Considered

| Option | Why rejected |
|---|---|
| Manifest V2 background pages | Deprecated platform direction and weaker long-term support. |
| Bookmarklet-based capture | Poorer auth/session flow and lower UX/control than extension APIs. |
| Electron/native desktop capture app | Larger operational and distribution burden for current scope. |

## Consequences

**Positive:**
- Standards-aligned extension architecture for modern browsers.
- Clear extension module boundaries and maintainable build pipeline.
- Direct integration with Briefly auth/share APIs.

**Negative / trade-offs:**
- MV3 service worker lifecycle constraints require careful event-driven coding.
- Broad host permissions (`<all_urls>`) increase scrutiny and review requirements.

## Related git history

- 2026-04-14 `4447fba`: Browser extension MVP introduced MV3 structure and modules.
- 2026-04-14 `f78bb1c`: Inventory/docs aligned to extension architecture as implemented.
- 2026-04-15 `db94bf4`: Extension redesign coordinated with dashboard and E2E evolution.
- Source scope: `main`

## Revision History

| Version | Date | Changes | Commit |
|---|---|---|---|
| 1.0.0 | 2026-04-16 | Initial ADR from git-history + codebase scan | 4447fba, db94bf4 |

## Related

- Specs affected: `docs/specs/EXT-001.md`, `docs/specs/ING-001.md`
- Other ADRs: `ARCH-001`, `ARCH-004`
