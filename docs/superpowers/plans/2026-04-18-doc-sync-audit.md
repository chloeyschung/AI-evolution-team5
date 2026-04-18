# Document Synchronization Audit Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development to execute this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Systematically audit all up-to-date documents for conflicts (doc-doc) and gaps between spec and code (doc-code) without making any changes.

**Architecture:** Dispatch one agent per feature ID. Each agent performs doc-doc sync AND doc-code sync for a single feature, reports findings, and waits for the next assignment. No parallel execution.

**Tech Stack:** Grep, Glob, Read tools for document/code exploration; doc-doc-sync and doc-code-sync skills for analysis.

---

## Scope

**Up-to-date documents (sync targets):**
- `docs/specs/*.md` — 30 spec files
- `docs/records/*.md` — 29 record files
- `docs/external/Briefly_FeatureList.md` — authoritative feature list
- `mps.md` — background/vision (may be stale)

**Skip (immutable snapshots):**
- `docs/audit/` — timestamped audit reports
- `docs/plans/` — historical implementation plans
- `PREMORTEM.md`, `WHYTREE.md` — analysis snapshots

**ADR files (reference for architectural constraints):**
- `docs/decisions/ARCH-*.md` — 15 ADR files

---

## Feature ID List (30 specs to audit)

| # | ID | Category |
|---|-----|----------|
| 1 | AUTH-001 | Authentication |
| 2 | AUTH-002 | Authentication |
| 3 | AUTH-003 | Authentication |
| 4 | AUTH-004 | Authentication |
| 5 | AUTH-005 | Authentication |
| 6 | AI-001 | AI/ML |
| 7 | AI-002 | AI/ML |
| 8 | AI-003 | AI/ML |
| 9 | DAT-001 | Data |
| 10 | DAT-002 | Data |
| 11 | DAT-003 | Data |
| 12 | DAT-004 | Data |
| 13 | DAT-005 | Data |
| 14 | EXT-001 | Extension |
| 15 | EXT-002 | Extension |
| 16 | ING-001 | Ingestion |
| 17 | ING-002 | Ingestion |
| 18 | INT-001 | Integration |
| 19 | INT-002 | Integration |
| 20 | QOL-001 | Quality of Life |
| 21 | SEC-001 | Security |
| 22 | SEC-002 | Security |
| 23 | SEC-003 | Security |
| 24 | UX-001 | UX |
| 25 | UX-002 | UX |
| 26 | UX-003 | UX |
| 27 | UX-004 | UX |
| 28 | UX-005 | UX |
| 29 | UX-006 | UX |
| 30 | ADV-001, ADV-002, ADV-003 | Advanced Features |

---

### Task 1: AUTH-001 Audit

**Files:**
- Spec: `docs/specs/AUTH-001.md`
- Record: `docs/records/AUTH-001-record.md`
- FeatureList: `docs/external/Briefly_FeatureList.md` (search for F-001, AUTH-001)

- [ ] **Step 1: Run doc-doc sync**
  - Use `Briefly-doc-doc-sync` skill
  - Compare spec vs FeatureList vs record vs mps.md
  - Identify conflicts using hierarchy (FeatureList > spec > ADR > mps > record)

- [ ] **Step 2: Run doc-code sync**
  - Use `Briefly-doc-code-sync` skill
  - Check spec endpoints exist in code
  - Check spec models exist in code
  - Check acceptance criteria implemented
  - Check status consistency with FeatureList

- [ ] **Step 3: Report findings**
  - Document conflicts found (or "none")
  - Document gaps found (or "none")
  - Wait for next assignment

---

### Task 2: AUTH-002 Audit

**Files:**
- Spec: `docs/specs/AUTH-002.md`
- Record: `docs/records/AUTH-002-record.md`
- FeatureList: `docs/external/Briefly_FeatureList.md` (search for F-002, AUTH-002)

- [ ] **Step 1: Run doc-doc sync**
- [ ] **Step 2: Run doc-code sync**
- [ ] **Step 3: Report findings**

---

### Task 3: AUTH-003 Audit

**Files:**
- Spec: `docs/specs/AUTH-003.md`
- Record: `docs/records/AUTH-003-record.md`
- FeatureList: `docs/external/Briefly_FeatureList.md` (search for F-003, AUTH-003)

- [ ] **Step 1: Run doc-doc sync**
- [ ] **Step 2: Run doc-code sync**
- [ ] **Step 3: Report findings**

---

### Task 4: AUTH-004 Audit

**Files:**
- Spec: `docs/specs/AUTH-004.md`
- Record: `docs/records/AUTH-004-record.md`
- FeatureList: `docs/external/Briefly_FeatureList.md` (search for AUTH-004)

- [ ] **Step 1: Run doc-doc sync**
- [ ] **Step 2: Run doc-code sync**
- [ ] **Step 3: Report findings**

---

### Task 5: AUTH-005 Audit

**Files:**
- Spec: `docs/specs/AUTH-005.md`
- Record: `docs/records/AUTH-005-record.md`
- FeatureList: `docs/external/Briefly_FeatureList.md` (search for F-027, AUTH-005)

- [ ] **Step 1: Run doc-doc sync**
- [ ] **Step 2: Run doc-code sync**
- [ ] **Step 3: Report findings**

---

### Task 6: AI-001 Audit

**Files:**
- Spec: `docs/specs/AI-001.md`
- Record: `docs/records/AI-001-record.md`
- FeatureList: `docs/external/Briefly_FeatureList.md` (search for AI-001)

- [ ] **Step 1: Run doc-doc sync**
- [ ] **Step 2: Run doc-code sync**
- [ ] **Step 3: Report findings**

---

### Task 7: AI-002 Audit

**Files:**
- Spec: `docs/specs/AI-002.md`
- Record: `docs/records/AI-002-record.md`
- FeatureList: `docs/external/Briefly_FeatureList.md` (search for AI-002)

- [ ] **Step 1: Run doc-doc sync**
- [ ] **Step 2: Run doc-code sync**
- [ ] **Step 3: Report findings**

---

### Task 8: AI-003 Audit

**Files:**
- Spec: `docs/specs/AI-003.md`
- Record: `docs/records/AI-003-record.md`
- FeatureList: `docs/external/Briefly_FeatureList.md` (search for AI-003)

- [ ] **Step 1: Run doc-doc sync**
- [ ] **Step 2: Run doc-code sync**
- [ ] **Step 3: Report findings**

---

### Task 9: DAT-001 Audit

**Files:**
- Spec: `docs/specs/DAT-001.md`
- Record: `docs/records/DAT-001-record.md`
- FeatureList: `docs/external/Briefly_FeatureList.md` (search for DAT-001)

- [ ] **Step 1: Run doc-doc sync**
- [ ] **Step 2: Run doc-code sync**
- [ ] **Step 3: Report findings**

---

### Task 10: DAT-002 Audit

**Files:**
- Spec: `docs/specs/DAT-002.md`
- Record: `docs/records/DAT-002-record.md`
- FeatureList: `docs/external/Briefly_FeatureList.md` (search for DAT-002)

- [ ] **Step 1: Run doc-doc sync**
- [ ] **Step 2: Run doc-code sync**
- [ ] **Step 3: Report findings**

---

### Task 11: DAT-003 Audit

**Files:**
- Spec: `docs/specs/DAT-003.md`
- Record: (check if exists)
- FeatureList: `docs/external/Briefly_FeatureList.md` (search for DAT-003)

- [ ] **Step 1: Run doc-doc sync**
- [ ] **Step 2: Run doc-code sync**
- [ ] **Step 3: Report findings**

---

### Task 12: DAT-004 Audit

**Files:**
- Spec: `docs/specs/DAT-004.md`
- Record: (check if exists)
- FeatureList: `docs/external/Briefly_FeatureList.md` (search for DAT-004)

- [ ] **Step 1: Run doc-doc sync**
- [ ] **Step 2: Run doc-code sync**
- [ ] **Step 3: Report findings**

---

### Task 13: DAT-005 Audit

**Files:**
- Spec: `docs/specs/DAT-005.md`
- Record: (check if exists)
- FeatureList: `docs/external/Briefly_FeatureList.md` (search for DAT-005)

- [ ] **Step 1: Run doc-doc sync**
- [ ] **Step 2: Run doc-code sync**
- [ ] **Step 3: Report findings**

---

### Task 14: EXT-001 Audit

**Files:**
- Spec: `docs/specs/EXT-001.md`
- Record: `docs/records/EXT-001-record.md`
- FeatureList: `docs/external/Briefly_FeatureList.md` (search for F-020, EXT-001)

- [ ] **Step 1: Run doc-doc sync**
- [ ] **Step 2: Run doc-code sync**
- [ ] **Step 3: Report findings**

---

### Task 15: EXT-002 Audit

**Files:**
- Spec: `docs/specs/EXT-002.md`
- Record: `docs/records/EXT-002-record.md`
- FeatureList: `docs/external/Briefly_FeatureList.md` (search for EXT-002)

- [ ] **Step 1: Run doc-doc sync**
- [ ] **Step 2: Run doc-code sync**
- [ ] **Step 3: Report findings**

---

### Task 16: ING-001 Audit

**Files:**
- Spec: `docs/specs/ING-001.md`
- Record: `docs/records/ING-001-record.md`
- FeatureList: `docs/external/Briefly_FeatureList.md` (search for ING-001)

- [ ] **Step 1: Run doc-doc sync**
- [ ] **Step 2: Run doc-code sync**
- [ ] **Step 3: Report findings**

---

### Task 17: ING-002 Audit

**Files:**
- Spec: `docs/specs/ING-002.md`
- Record: `docs/records/ING-002-record.md`
- FeatureList: `docs/external/Briefly_FeatureList.md` (search for ING-002)

- [ ] **Step 1: Run doc-doc sync**
- [ ] **Step 2: Run doc-code sync**
- [ ] **Step 3: Report findings**

---

### Task 18: INT-001 Audit

**Files:**
- Spec: `docs/specs/INT-001.md`
- Record: `docs/records/INT-001-record.md`
- FeatureList: `docs/external/Briefly_FeatureList.md` (search for F-022, INT-001)

- [ ] **Step 1: Run doc-doc sync**
- [ ] **Step 2: Run doc-code sync**
- [ ] **Step 3: Report findings**

---

### Task 19: INT-002 Audit

**Files:**
- Spec: `docs/specs/INT-002.md`
- Record: `docs/records/INT-002-record.md`
- FeatureList: `docs/external/Briefly_FeatureList.md` (search for F-023, INT-002)

- [ ] **Step 1: Run doc-doc sync**
- [ ] **Step 2: Run doc-code sync**
- [ ] **Step 3: Report findings**

---

### Task 20: QOL-001 Audit

**Files:**
- Spec: `docs/specs/QOL-001.md`
- Record: `docs/records/QOL-001-record.md`
- FeatureList: `docs/external/Briefly_FeatureList.md` (search for QOL-001)

- [ ] **Step 1: Run doc-doc sync**
- [ ] **Step 2: Run doc-code sync**
- [ ] **Step 3: Report findings**

---

### Task 21: SEC-001 Audit

**Files:**
- Spec: `docs/specs/SEC-001.md`
- Record: `docs/records/SEC-001-record.md`
- FeatureList: `docs/external/Briefly_FeatureList.md` (search for SEC-001)

- [ ] **Step 1: Run doc-doc sync**
- [ ] **Step 2: Run doc-code sync**
- [ ] **Step 3: Report findings**

---

### Task 22: SEC-002 Audit

**Files:**
- Spec: `docs/specs/SEC-002.md`
- Record: `docs/records/SEC-002-record.md`
- FeatureList: `docs/external/Briefly_FeatureList.md` (search for SEC-002)

- [ ] **Step 1: Run doc-doc sync**
- [ ] **Step 2: Run doc-code sync**
- [ ] **Step 3: Report findings**

---

### Task 23: SEC-003 Audit

**Files:**
- Spec: `docs/specs/SEC-003.md`
- Record: (check if exists)
- FeatureList: `docs/external/Briefly_FeatureList.md` (search for SEC-003)

- [ ] **Step 1: Run doc-doc sync**
- [ ] **Step 2: Run doc-code sync**
- [ ] **Step 3: Report findings**

---

### Task 24: UX-001 Audit

**Files:**
- Spec: `docs/specs/UX-001.md`
- Record: `docs/records/UX-001-record.md`
- FeatureList: `docs/external/Briefly_FeatureList.md` (search for UX-001)

- [ ] **Step 1: Run doc-doc sync**
- [ ] **Step 2: Run doc-code sync**
- [ ] **Step 3: Report findings**

---

### Task 25: UX-002 Audit

**Files:**
- Spec: `docs/specs/UX-002.md`
- Record: `docs/records/UX-002-record.md`
- FeatureList: `docs/external/Briefly_FeatureList.md` (search for UX-002)

- [ ] **Step 1: Run doc-doc sync**
- [ ] **Step 2: Run doc-code sync**
- [ ] **Step 3: Report findings**

---

### Task 26: UX-003 Audit

**Files:**
- Spec: `docs/specs/UX-003.md`
- Record: `docs/records/UX-003-record.md`
- FeatureList: `docs/external/Briefly_FeatureList.md` (search for UX-003)

- [ ] **Step 1: Run doc-doc sync**
- [ ] **Step 2: Run doc-code sync**
- [ ] **Step 3: Report findings**

---

### Task 27: UX-004 Audit

**Files:**
- Spec: `docs/specs/UX-004.md`
- Record: `docs/records/UX-004-record.md`
- FeatureList: `docs/external/Briefly_FeatureList.md` (search for UX-004)

- [ ] **Step 1: Run doc-doc sync**
- [ ] **Step 2: Run doc-code sync**
- [ ] **Step 3: Report findings**

---

### Task 28: UX-005 Audit

**Files:**
- Spec: `docs/specs/UX-005.md`
- Record: `docs/records/UX-005-record.md`
- FeatureList: `docs/external/Briefly_FeatureList.md` (search for UX-005)

- [ ] **Step 1: Run doc-doc sync**
- [ ] **Step 2: Run doc-code sync**
- [ ] **Step 3: Report findings**

---

### Task 29: UX-006 Audit

**Files:**
- Spec: `docs/specs/UX-006.md`
- Record: `docs/records/UX-006-record.md`
- FeatureList: `docs/external/Briefly_FeatureList.md` (search for UX-006)

- [ ] **Step 1: Run doc-doc sync**
- [ ] **Step 2: Run doc-code sync**
- [ ] **Step 3: Report findings**

---

### Task 30: ADV-001, ADV-002, ADV-003 Audit

**Files:**
- Specs: `docs/specs/ADV-001.md`, `docs/specs/ADV-002.md`, `docs/specs/ADV-003.md`
- Records: `docs/records/ADV-001-record.md`, `docs/records/ADV-002-record.md`, `docs/records/ADV-003-record.md`
- FeatureList: `docs/external/Briefly_FeatureList.md` (search for F-024, F-025, F-026, ADV-*)

- [ ] **Step 1: Run doc-doc sync for all three**
- [ ] **Step 2: Run doc-code sync for all three**
- [ ] **Step 3: Report findings**

---

### Task 31: Consolidate Findings

**Files:**
- All agent reports from Tasks 1-30

- [ ] **Step 1: Aggregate all findings**
  - Create summary table of conflicts by feature ID
  - Create summary table of gaps by feature ID
  - Identify patterns (e.g., "all SEC specs have missing code")

- [ ] **Step 2: Prioritize issues**
  - P0: Spec-code gaps for "complete" features
  - P1: Doc-doc conflicts affecting implementation
  - P2: Minor documentation inconsistencies

- [ ] **Step 3: Present final report to user**
  - Summary of total issues found
  - Recommendation for next steps

---

## Agent Dispatch Protocol

**For each task:**
1. User assigns task to agent via `superpowers:subagent-driven-development`
2. Agent performs doc-doc sync AND doc-code sync
3. Agent reports findings in this format:

```
=== AUDIT REPORT: {ID} ===

DOC-DOC SYNC:
- Conflicts found: {N}
  - {list conflicts or "none"}

DOC-CODE SYNC:
- MISSING endpoints: {list or "none"}
- MISSING models: {list or "none"}
- UNIMPLEMENTED criteria: {list or "none"}
- UNDOCUMENTED code: {list or "none"}
- Status consistency: {OK | MISMATCH}

READY for next assignment.
```

4. User acknowledges, assigns next task
5. Repeat until all 30 features audited

---

## Self-Review

**1. Spec coverage:** All 30 specs listed as individual tasks. ✓

**2. Placeholder scan:** No "TBD" or "TODO" in task steps. Each task has clear file paths and steps. ✓

**3. Type consistency:** All tasks use same audit protocol (doc-doc + doc-code). ✓

---

Plan complete and saved to `docs/superpowers/plans/2026-04-18-doc-sync-audit.md`.

**Two execution options:**

**1. Subagent-Driven (recommended)** - I dispatch a fresh subagent per task, review between tasks, fast iteration

**2. Inline Execution** - Execute tasks in this session using executing-plans, batch execution with checkpoints

**Which approach?**
