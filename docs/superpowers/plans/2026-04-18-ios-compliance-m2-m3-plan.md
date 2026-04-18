# iOS Compliance M-2/M-3 Execution Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans style task execution with checkbox tracking.

**Goal:** Verify whether M-2 (cursor pagination) and M-3 (user timezone storage) require spec-first treatment, then implement both in atomic, sequential agent tasks with one local commit per task.

**Architecture:**
- M-2 introduces cursor pagination as an additive contract on existing paginated content endpoints while preserving current offset fields for backward compatibility.
- M-3 introduces explicit IANA timezone persistence on `UserProfile` and exposes it via profile read/update APIs.

**Execution constraints:**
- Exactly one worker agent active at a time.
- No per-agent worktree creation.
- Each worker must commit locally after tests pass.
- Orchestrator integrates interdependency outcomes between workers.

---

## Phase 0: Spec Necessity Gate

- [ ] Compare preexisting spec depth/style/objectification level (`docs/specs/*.md`, recent AUTH-005 updates).
- [ ] Determine whether M-2/M-3 are substantial contract/data-model changes requiring specs.
- [ ] If true, create specs before implementation.

Exit criteria:
- A written decision with explicit rationale.

---

## Phase 1: Spec Authoring (Orchestrator)

- [ ] Add `docs/specs/DAT-004.md` for cursor pagination behavior, edge-cases, and API contract.
- [ ] Add `docs/specs/DAT-005.md` for timezone storage model + API semantics.
- [ ] Ensure each spec contains concrete requirements, API examples, implementation files, tests, and sensory verification.

Exit criteria:
- Both specs exist and match existing repository spec rigor.

---

## Phase 2: Atomic Task A (Worker 1) — M-2 Cursor Pagination

Ownership (write scope):
- `src/utils/cursor_pagination.py` (new)
- `src/api/schemas.py` (pagination response schema extension)
- `src/api/routers/content.py` (list + search cursor params/response)
- `src/api/routers/swipe.py` (pending/kept/discarded cursor params/response)
- `src/data/repository.py` (cursor-scoped query helpers for content lists/search)
- `tests/api/test_pagination_envelope.py` and targeted route tests for cursor behavior
- `docs/specs/DAT-004.md` (implementation status sync if needed)

- [ ] Add failing tests for cursor token shape and forward-only stability.
- [ ] Implement cursor encode/decode + validation.
- [ ] Add optional `cursor` query param and `next_cursor` response field.
- [ ] Keep existing `offset`/`next_offset` to preserve old clients.
- [ ] Run focused API tests for pagination endpoints.
- [ ] Commit with M-2 specific message.

Exit criteria:
- Cursor-based traversal works and tests pass.

---

## Phase 3: Interdependency Check (Orchestrator)

- [ ] Verify M-2 changes do not break M-3 touchpoints (profile endpoints/models).
- [ ] Rebase mental model for worker-2 instructions from current `HEAD`.

Exit criteria:
- Clean handoff prompt for Worker 2.

---

## Phase 4: Atomic Task B (Worker 2) — M-3 Timezone Storage

Ownership (write scope):
- `src/data/models.py` (`UserProfile.timezone` field)
- `src/data/repository.py` (profile create/update defaults + validation point)
- `src/api/schemas.py` (`UserProfileResponse`, `UserProfileUpdate` timezone)
- `src/api/routers/user.py` (read/write timezone wiring)
- `tests/api/test_account_user_datetime.py`, `tests/data/test_user_profile.py` (timezone persistence + update tests)
- `docs/specs/DAT-005.md` (implementation status sync if needed)

- [ ] Add failing tests for timezone persistence and profile update semantics.
- [ ] Implement `UserProfile.timezone` storage with default `UTC`.
- [ ] Accept/update timezone via profile patch and return in profile responses.
- [ ] Run focused profile/data tests.
- [ ] Commit with M-3 specific message.

Exit criteria:
- Timezone is persisted and round-trippable via profile APIs.

---

## Phase 5: Final Sync (Orchestrator)

- [ ] Update inventory/dependency docs if new DAT IDs are introduced.
- [ ] Run combined targeted test slice for M-2 + M-3.
- [ ] Provide commit notes and interdependency report.

