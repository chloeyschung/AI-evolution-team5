# Briefly Project Management Framework

> Process reference for AI-assisted development.

---

## Roles

| Role | Responsibilities |
|---|---|
| **Human (Architect)** | Decides, defines interfaces, approves designs, ALL final decisions |
| **Agent (Implementer)** | Implements, executes tests, thinking partner during planning |

Agent proposes options. Human makes all final decisions. Never implement without a spec.

---

## Atomic Spec Principle

- **Self-contained:** dependency interfaces inline → spec alone defines the feature
- **Minimal context:** agent reads spec + assembled context, not the entire codebase
- **@ cross-references:** `@specs/{ID}.md` and `@src/{path}` for dependency tracking
- **Atomic:** implementable in one session, ≤5 files changed, clear "done" state

---

## Workflow

### Planning (Human-led)

| Stage | Output |
|---|---|
| Vision Capture | `docs/mps.md` |
| Product Feature List | `docs/external/Briefly_FeatureList.md` |
| Engineering Registry | `docs/feature-inventory.md` |
| Spec Development | `docs/specs/{ID}.md` |
| Dependency Analysis | `docs/dependency-matrix.md` |
| Implementation Plan | `docs/plans/implementation-plan.md` |

`docs/external/Briefly_FeatureList.md` is the product-side feature list and Markdown mirror of colleague-owned upstream material.
`feature-inventory.md` is the engineering registry used for repo-scoped implementation tracking.

### Implementation (Agent-led)

Mandatory sequential pipeline — see CLAUDE.md:

```
pre-flight → TDD → code → /simplify → sensory-verification → briefly-commit
```

---

## Directory Structure

```
docs/
├── mps.md                          # Vision (planning only; may be stale)
├── PROJECT-MANAGEMENT-FRAMEWORK.md
├── feature-inventory.md            # Engineering feature registry
├── external/                       # Optional upstream inputs (feedback, meeting results, doc mirrors)
│   ├── Briefly_FeatureList.md      # Product-side feature list / Markdown mirror
│   ├── Briefly_FeatureList.xlsx    # Upstream spreadsheet source
│   └── {category}/{name}.md        # Other Markdown mirrors or external inputs
├── dependency-matrix.md            # Dependency graph
├── decisions/
│   └── ARCH-NNN-{slug}.md          # Architectural Decision Records
├── specs/
│   └── {ID}.md                     # One spec per feature
├── plans/
│   └── implementation-plan.md      # Phase tracking and progress
├── records/
│   └── {ID}-record.md              # Completion log per feature
└── templates/                      # Document templates (git-tracked)
    ├── spec-template.md
    ├── record-template.md
    ├── adr-template.md
    ├── impl-plan-template.md
    ├── dependency-matrix-template.md
    ├── briefly-design-language-template.md
    └── external-input-addendum-template.md

```

---

## Document Source-of-Truth Hierarchy

When documents conflict, highest wins:

1. `docs/external/Briefly_FeatureList.md` — product-side feature source; authoritative for product intent
2. `docs/specs/{ID}.md` — feature-authoritative for implementation details
3. `docs/feature-inventory.md` — engineering registry; authoritative for repo-scoped implementation status
4. `docs/decisions/ARCH-NNN-{slug}.md` — architectural constraints specs must respect
5. `mps.md` — background/vision; may be stale
6. `records/` — retrospective, not prescriptive

A spec that conflicts with an ADR means either the spec missed the constraint (fix spec) or the decision is outdated (supersede the ADR).
External inputs and their mirrors are upstream context, not authoritative for repo implementation status until normalized into internal docs.

---

## Document Lifecycle: Snapshot vs. Up-to-Date

Documents fall into two categories with different sync behaviors.

### Snapshot Documents (Immutable)

**Definition**: Point-in-time captures that should **never** be modified after creation. New analysis = new file.

| Location | Rule |
|----------|------|
| `docs/audit/` | Filename contains date → immutable (e.g., `critical-questions-audit-YYYYMMDD.md`) |
| `docs/plans/` | Historical record of "how we intended to build X"; once committed, immutable |
| `docs/PREMORTEM.md` | Risk analysis at a point in time |
| `docs/WHYTREE.md` | Why-tree analysis for a decision |

### Up-to-Date Documents (Mutable)

**Definition**: Must reflect current codebase state; **should** be modified regularly.

| Category | Files | Sync Behavior |
|----------|-------|---------------|
| **Source of Truth** | `Briefly_FeatureList.md`, `dependency-matrix.md`, `feature-inventory.md` | Always sync |
| **Specs** | `docs/specs/{ID}.md` | Evolve with requirements |
| **Records** | `docs/records/{ID}-record.md` | Append-only (add sections, don't overwrite) |
| **ADRs** | `docs/decisions/ARCH-NNN-{slug}.md` | Immutable once created (versioned) |
| **Templates** | `docs/templates/*` | Evolve with best practices |

### Reference/Static Documents

**Definition**: Documentation about the project, updated infrequently.

- `mps.md`, `README.md`, `MANIFEST.md`, `PROJECT-MANAGEMENT-FRAMEWORK.md`
- `criticalquestions_Briefly.md`, `frontend_design.md`, `impact-tracking-design.md`

---

### Key Rules

1. **Snapshot files have timestamps** in filenames or capture point-in-time analysis
2. **Up-to-date files track live state** (implementation status, requirements, test results)
3. **ADRs are versioned immutables** — each decision gets its own numbered file, never modified
4. **Records are append-only** — add new test results but don't overwrite old ones
5. **Specs evolve with requirements** — update when requirements change or bugs are fixed

This categorization informs `doc-doc-sync` and `doc-code-sync` skills: snapshot documents are excluded from sync operations; up-to-date documents are validated for consistency.

---

## External Inputs

Use external inputs for product intent, feedback, and discussion context. Do not use them as repo implementation truth.

- Prefer `docs/external/` for colleague-owned docs, feedback summaries, and Markdown mirrors of spreadsheets or shared notes.
- If an upstream doc must stay outside `docs/external/`, attach an external-input addendum or equivalent header that states owner, role, and edit policy.
- Use Markdown mirrors for agent-readable context. Keep `.xlsx` or other binary sources as upstream references, not primary reading targets.
- Normalize accepted deltas into internal docs:
  - product intent source / mirror → `docs/external/Briefly_FeatureList.md`
  - repo status → `feature-inventory.md`
  - implementation detail → `docs/specs/{ID}.md`
  - architecture → `docs/decisions/`
  - sequencing/progress → `docs/plans/implementation-plan.md`

---

## Context Assembly

> Assemble the minimum context package for a single feature session. Do not dump all docs — curate only what is needed.

### 6-Step Procedure

1. **Feature Spec** — load `docs/specs/{ID}.md` in full; this is the primary blueprint
2. **Dependency Context** — follow all `@` references in the spec:
   - `@specs/{DEP-ID}.md` → understand the dependency's interface
   - `@src/{path}` → understand how it is already implemented
   - Do NOT recurse into transitive dependencies (direct only)
3. **Repo Status Context** — load `docs/feature-inventory.md` only when the task depends on repo-scoped completion/status, doc synchronization, or implementation coverage checks
4. **Phase Guidance** — extract from `docs/plans/implementation-plan.md`:
   - Which phase this feature belongs to
   - That phase's completion criteria and validation strategy
   - Legacy but still useful when implementing from scratch; during stabilization/exploration treat it as optional context
   - Update stale entries before relying on it
   - Do NOT load the full plan
5. **External Input Context** — load only when the task is driven by colleague feedback, upstream product docs, or shared discussion results:
   - Use the relevant file in `docs/external/` or the explicitly marked legacy upstream doc
   - Treat it as intent/context, not as shipped-state evidence
6. **Sensor Instructions** — identify needed sensors from acceptance criteria (see Sensory Verification below); load only the relevant section

### Anti-patterns
- ❌ Include `mps.md` by default during implementation
- ❌ Load `feature-inventory.md` when the task is code-only and the spec already provides sufficient context
- ❌ Include specs for features in other phases
- ❌ Load the full implementation plan
- ❌ Treat external inputs as proof that a feature is implemented in this repo
- ❌ Rely on prior session conversation history

---

## Sensory Verification

> Tests tell you **what** failed. Sensors tell you **why** it failed.
> Feature is done only when: all tests pass AND all active sensors report clean.

### Visual Sense — what was created, what exists

Captures: UI rendering, layout, styling; DB state, config values, session data; actual file structure and content.

Apply when acceptance criteria contain: "shows", "displays", "renders", "visible".

### Auditory Sense — what the system reports

Captures: logs, errors/warnings, API responses, stack traces.

Apply when acceptance criteria contain: "log", "error", "response", "exception".

### Tactile Sense — how interactions respond

Captures: user workflows end-to-end; request-response cycles; performance (response time, resource use); auth/authz behavior; integration with other features.

Apply when acceptance criteria contain: "click", "submit", "complete", "workflow", "request".

### Correlation Analysis

- Multiple sensors flag the same issue → diagnosis confirmed
- Sensors conflict → hidden complexity exists; investigate before proceeding
- Tests pass + sensor anomaly → tests are incomplete or spec is missing a criterion

---

## Dependency Matrix

### Format

| | A | B | C |
|---|---|---|---|
| **A** | — | | |
| **B** | X | — | |
| **C** | | X | — |

**X = row depends on column**

### Binary Dependency Test

> "Does row require column's concrete output, configuration, or functionality to operate?"

- **Yes** → real dependency, keep
- **No** → remove (tool sharing or convenience is not a dependency)

### Deriving Implementation Phases (Topological Sort)

1. Features with no dependencies → **Phase 1**
2. Remove Phase 1; features whose dependencies are all in Phase 1 → **Phase 2**
3. Repeat until all features are assigned
4. **Critical Path** = longest chain (delays here delay the whole project)

### Cycle Resolution (in order)

1. Re-apply binary test — eliminate false dependency
2. Revise spec interface to remove coupling
3. Split feature into independent parts
4. Consolidate features (last resort)

---

## Workflow Router

| Task | Use |
|---|---|
| Write a spec | `docs/templates/spec-template.md` → `docs/specs/{ID}.md` |
| Plan implementation order | `docs/templates/impl-plan-template.md` → `docs/plans/implementation-plan.md` |
| Record completion | `docs/templates/record-template.md` → `docs/records/{ID}-record.md` |
| Record architectural decision | `docs/templates/adr-template.md` → `docs/decisions/ARCH-NNN-{slug}.md` |
| Register external input | `docs/templates/external-input-addendum-template.md` → add to the upstream doc or its Markdown mirror |
| Verify doc consistency | `briefly-workflows:doc-doc-sync` skill |
| Verify code matches spec | `briefly-workflows:doc-code-sync` skill |

---

## Critical Rules

1. **No spec, no code** — propose spec first; wait for approval
2. **Load minimal context** — spec is self-contained; skip mps/inventory during implementation
3. **Feature done** = tests pass AND sensors clean (both required)
4. **Commit locally** — never push without explicit request
5. **Escalate ambiguity** — sensor conflict or spec gap → propose options, wait for human
6. **One feature per session** — prevents context bloat; start fresh for each feature
