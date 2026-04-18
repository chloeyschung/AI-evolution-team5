# ARCH-007: Provider-Agnostic Integration Sync Subsystem

**Date:** 2026-04-14  
**Status:** accepted  
**ADR Version:** 1.0.0  
**Last Updated:** 2026-04-16  
**Owners:** Briefly engineering team

---

## Context

Briefly added YouTube and LinkedIn synchronization with common needs: OAuth token lifecycle, per-user sync configs, last-sync tracking, logs, and ingestion into shared content pipelines.

## Decision

We will use a provider-agnostic integration subsystem: shared integration tables/repository (`tokens`, `sync_config`, `sync_log`) with provider-specific clients/sync services layered on top.

## Rationale

- Shared persistence model avoids duplicating auth/sync state logic per provider.
- Provider-specific services preserve API-specific behavior while reusing common contracts.
- Enables adding new providers with lower architectural churn.

## Alternatives Considered

| Option | Why rejected |
|---|---|
| Separate schema/repository per provider | High duplication and inconsistent behavior across integrations. |
| Generic provider adapter only (no provider services) | Too rigid for provider-specific flow differences and edge cases. |
| One-off import scripts without persisted sync state | No reliable incremental sync, observability, or user control. |

## Consequences

**Positive:**
- Consistent integration lifecycle and easier provider expansion.
- Unified operational visibility through sync logs/config.
- Better reuse of security controls (encrypted token storage, user scoping).

**Negative / trade-offs:**
- Abstraction layer adds complexity for simple integrations.
- Provider-specific quirks still require bespoke client/service code.

## Related git history

- 2026-04-14 `38ae39d`: YouTube auto-sync implementation established integration baseline.
- 2026-04-14 `e770f4e`: LinkedIn sync added on same shared integration model.
- 2026-04-14 `52a2adf`: Provider enum standardization reinforced provider-agnostic contracts.
- 2026-04-14 `80d36f9`: Encrypted OAuth token storage aligned integration security handling.
- Source scope: `main`

## Revision History

| Version | Date | Changes | Commit |
|---|---|---|---|
| 1.0.0 | 2026-04-16 | Initial ADR from expanded git-history + codebase scan | 38ae39d, e770f4e, 52a2adf, 80d36f9 |

## Related

- Specs affected: `docs/specs/INT-001.md`, `docs/specs/INT-002.md`, `docs/specs/SEC-001.md`
- Other ADRs: `ARCH-001`, `ARCH-002`, `ARCH-006`
