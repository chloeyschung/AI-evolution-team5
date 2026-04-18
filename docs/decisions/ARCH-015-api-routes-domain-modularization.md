# ARCH-015: API Routes Domain Modularization

**Date:** 2026-04-17
**Status:** proposed
**ADR Version:** 1.0.0
**Last Updated:** 2026-04-17
**Owners:** Briefly engineering team

---

## Context

`src/api/routes.py` has grown to ~2,625 lines and handles 50+ endpoints across 7 domains: auth, content, swipe, user preferences, integrations (YouTube, LinkedIn), AI processing, and account management. All router decorators, business logic orchestration, and dependency injections are in a single file.

**Current pain points:**

- Parallel feature development on different domains causes merge conflicts on the same file
- Test isolation is impossible — all route tests share one import surface
- New contributors cannot navigate domain boundaries by file structure alone
- Adding audit logging (SEC-003) or soft-delete hooks (DAT-003) requires touching an already-dense file

**Trigger for this decision:** The audit identified SOTA-001 as a critical architectural risk. With SEC-003 (audit logging) and DAT-003 (soft delete) requiring instrumentation across multiple route groups, the complexity of doing that work safely in a monolithic file is prohibitive.

---

## Decision

Split `src/api/routes.py` into domain router modules under `src/api/routers/`. Each module owns one domain. The main `app.py` assembles them via `include_router`.

### Target structure

```
src/api/
├── app.py                   # assembles routers, middleware, lifespan
├── schemas.py               # all Pydantic schemas (unchanged)
├── dependencies.py          # shared Depends() helpers (get_current_user, get_db, etc.)
└── routers/
    ├── __init__.py
    ├── auth.py              # /auth/* — login, register, token refresh, OAuth Google
    ├── content.py           # /content/* — CRUD, status, list, pagination
    ├── swipe.py             # /swipe/* — record action, get pending
    ├── user.py              # /user/* — profile, preferences, statistics
    ├── integrations.py      # /integrations/* — YouTube, LinkedIn connect/callback/sync
    ├── ai.py                # /ai/* — summarize, tag, batch process
    └── account.py           # /auth/account/* — delete, restore (DAT-003 hooks)
```

### Routing assembly in `app.py`

```python
from src.api.routers import auth, content, swipe, user, integrations, ai, account

app.include_router(auth.router,         prefix="/api/v1", tags=["auth"])
app.include_router(content.router,      prefix="/api/v1", tags=["content"])
app.include_router(swipe.router,        prefix="/api/v1", tags=["swipe"])
app.include_router(user.router,         prefix="/api/v1", tags=["user"])
app.include_router(integrations.router, prefix="/api/v1", tags=["integrations"])
app.include_router(ai.router,           prefix="/api/v1", tags=["ai"])
app.include_router(account.router,      prefix="/api/v1", tags=["account"])
```

---

## Rationale

| Option | Pros | Cons |
|--------|------|------|
| **Keep monolithic** | No migration effort | Merge conflicts grow; SEC-003/DAT-003 instrumentation risky |
| **Split by domain (chosen)** | Parallel dev, clear ownership, testable in isolation | One-time migration; imports need updating |
| **Split by layer (service/route/schema per file)** | Pure separation of concerns | Over-engineered for current team size; cross-layer navigation harder |

Domain split is the industry-standard FastAPI pattern and matches how tests are already organized (`tests/auth/`, `tests/integrations/`, etc.).

---

## Consequences

**Positive:**
- Each router file is < 400 lines, focused on one domain
- New route additions have a clear home — no ambiguity
- SEC-003 audit hooks and DAT-003 soft-delete cascade can be added per-router without touching unrelated code
- Test files can import only the router they test

**Negative:**
- One-time migration effort: ~2,625 lines must be moved, imports adjusted, shared helpers extracted to `dependencies.py`
- All `from src.api.routes import router` references in tests must be updated
- Risk of missing a route or duplicating a dependency during the split — requires a full regression run after migration

**Mitigation:** Migrate domain by domain (auth first, then content, etc.), running `uv run pytest tests/ -q` after each domain. Keep the old `routes.py` in place until all domains are migrated, then delete it.

---

## Implementation Notes

1. **Extract shared dependencies first**: `get_current_user`, `get_db`, `get_user_id_from_token` into `src/api/dependencies.py` before splitting routes. This is the most import-heavy step.

2. **Domain order** (least to most cross-cutting): `swipe → content → user → auth → integrations → ai → account`

3. **No behavior changes**: this is a pure structural refactor. No new endpoints, no schema changes, no business logic edits. Any bug found during migration should be filed separately.

4. **Estimated effort**: ~4–6h for a careful domain-by-domain migration with tests passing at each step.

---

## Related Decisions

- [ARCH-001](ARCH-001-async-fastapi-sqlalchemy-repository-backend.md) — FastAPI as the API framework
- [ARCH-012](ARCH-012-centralized-test-fixtures-and-repository-oriented-tests.md) — Test fixture structure (test imports affected by this split)

## Related Specs

- [SEC-003](../specs/SEC-003.md) — Audit logging (requires per-router instrumentation)
- [DAT-003](../specs/DAT-003.md) — Soft delete (requires account router hooks)
