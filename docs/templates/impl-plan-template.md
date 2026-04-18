# Implementation Plan

**Last Updated:** {YYYY-MM-DD}
**Status:** {Active planning | Legacy plan retained | Stabilization}
**Dependency Basis:** `docs/dependency-matrix.md`

---

## Phase Summary

| Phase | Status | Description |
|---|---|---|
| Phase 1 - {name} | {Not Started/In Progress/Partially Met/Met} | {short scope and current state} |
| Phase 2 - {name} | {Not Started/In Progress/Partially Met/Met} | {short scope and current state} |
| Phase 3 - {name} | {Not Started/In Progress/Partially Met/Met} | {short scope and current state} |

---

## Critical Path

`{ID} -> {ID} -> {ID}`

Rationale: {why this chain is schedule-critical}

---

## Phase Gates and Validation Strategy

### Phase 1 - {name}
- Completion criteria:
  - {criterion}
  - {criterion}
- Validation strategy:
  - {test/integration strategy}
  - {sensor/UX verification strategy}

### Phase 2 - {name}
- Completion criteria:
  - {criterion}
  - {criterion}
- Validation strategy:
  - {test/integration strategy}
  - {cross-phase compatibility strategy}

### Phase N - {name}
- Completion criteria:
  - {criterion}
- Validation strategy:
  - {strategy}

---

## Legacy Implementation Order

### Wave 1: {name}
1. **{ID}** {feature name} ({optional F-IDs})
2. **{ID}** {feature name} ({optional F-IDs})

Outcome: {implemented/not implemented and scope notes}

### Wave 2: {name}
1. **{ID}** {feature name}

Outcome: {implemented/not implemented and scope notes}

<!-- Add additional waves as needed -->

---

## Open Gaps

| ID | Area | Gap | Priority |
|---|---|---|---|
| {ID} | {area} | {what is missing} | {P0/P1/P2/P3} |

---

## Agent Task Selection Guidance

1. Select work from the highest-priority open gap that has all dependencies met.
2. If this plan is marked legacy, treat phase order as advisory and dependency correctness as mandatory.
3. Verify status in `docs/feature-inventory.md` and `docs/specs/{ID}.md` before implementation.

## Blocker Management Protocol

| Situation | Action |
|---|---|
| Dependency incomplete | Pause task and complete/unblock dependency first |
| Spec ambiguity | Stop coding, update spec, then resume |
| Unexpected technical constraint | Record in spec/ADR, define workaround, then resume |
| Tests pass but sensory issue remains | Update acceptance criteria and verification steps before merge |

---

## References

- **Master Spec:** `docs/mps.md`
- **Product Feature List:** `docs/external/Briefly_FeatureList.md`
- **Engineering Registry:** `docs/feature-inventory.md`
- **Dependencies:** `docs/dependency-matrix.md`
- **Specs:** `docs/specs/{ID}.md`
- **Records:** `docs/records/{ID}-record.md`
