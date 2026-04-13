# Dependency Matrix

Feature dependency mapping for optimal implementation order.

**Note:** Engineering IDs (ING-xxx, AI-xxx, UX-xxx, DAT-xxx, AUTH-xxx) track implementation. Product requirements use F-xxx IDs from `docs/Briefly_FeatureList.md`. Cross-references provided where applicable.

## Legend

- `→` : Depends on (must be implemented before)
- `↔` : Bidirectional dependency (tightly coupled)
- `⇢` : Soft dependency (recommended but not required)

## Dependency Tables

### Authentication Layer (AUTH)

| Feature | Depends On | Blocked By | Notes | F-xxx Mapping |
|---------|------------|------------|-------|---------------|
| **AUTH-001** App Entry & Login | - | - | Prerequisite for all features | F-000 |
| **AUTH-002** Social Login (Google) | AUTH-001 | - | One-tap login, auto-create account | F-001 |
| **AUTH-003** Logout | AUTH-002 | - | Session end, local data retained | F-002 |
| **AUTH-004** Account Delete | AUTH-001 | - | 2-step confirmation, 30-day block | F-003 |

### Ingestion Layer

| Feature | Depends On | Blocked By | Notes | F-xxx Mapping |
|---------|------------|------------|-------|---------------|
| **ING-001** Mobile Share Sheet | - | - | Entry point | F-004 |
| **ING-002** URL Extraction | ING-001 | - | Needs URL from share sheet | F-005 |

### AI & Processing Layer

| Feature | Depends On | Blocked By | Notes | F-xxx Mapping |
|---------|------------|------------|-------|---------------|
| **AI-001** Core Summarizer | ING-002 | - | Needs extracted text. ⚠️ Spec requires 300-char limit update for F-005 compliance. | F-005 |
| **AI-002** Metadata Extraction | ING-001 | - | Works with URL directly. ⚠️ OG image thumbnail crawling not implemented (F-007). | F-007 |
| **AI-003** AI Categorization | ING-002 | - | LLM-based auto-tagging (max 3 tags). ⏸️ Spec pending. | F-006 |

### UX Layer

| Feature | Depends On | Blocked By | Notes | F-xxx Mapping |
|---------|------------|------------|-------|---------------|
| **UX-001** Swipe Card Stack | AI-001, AI-002 | - | Needs summary + metadata. Provides F-008/F-009/F-010. | F-008, F-009, F-010 |
| **UX-002** Swipe Actions | UX-001, DAT-001 | - | Persists Keep/Discard. ⚠️ Requires `status` field update (INBOX/ARCHIVED). | F-009, F-011 |
| **UX-003** Detail View | UX-001, AI-002 | - | Shows source content. ⚠️ Requires F-012 state transition logic ("읽었어요" button, INBOX→ARCHIVED). | F-012 |

### Data Layer

| Feature | Depends On | Blocked By | Notes | F-xxx Mapping |
|---------|------------|------------|-------|---------------|
| **DAT-001** Hybrid Storage | AI-002 | - | Stores metadata + summary. ⚠️ Requires `status` field for INBOX/ARCHIVED (F-012). | F-018 |
| **DAT-002** User Profile | DAT-001 | - | Preferences, stats, interest tags. ⚠️ `InterestTag` is for user-created tags, not AI-generated tags (F-014 gap). | F-017, F-015 |

*DAT-002 provides data models for F-015 (default_sort preference). F-014 AI category filtering requires AI-003 first.

## Implementation Order

### Wave 1: Authentication Foundation
1. **AUTH-001** App Entry & Login State

### Wave 2: Core Ingestion & Processing
2. **ING-001** Mobile Share Sheet Integration
3. **AI-002** Metadata Extraction ✅
4. **ING-002** URL Extraction & Cleaning
5. **AI-001** Core 3-Line Summarizer ✅

### Wave 3: AI Enhancements
6. **AI-003** AI Categorization (F-006)

### Wave 4: Data Persistence
7. **DAT-001** Hybrid Storage Engine ✅

### Wave 5: User Experience
8. **UX-001** Swipe Card Stack ✅ Backend
9. **UX-002** Swipe Actions ✅
10. **UX-003** Detail View

### Wave 6: User Management
11. **AUTH-002** Social Login (Google)
12. **AUTH-003** Logout
13. **AUTH-004** Account Delete
14. **DAT-002** User Profile ✅ (Models exist, API complete)

## Critical Path

```
AUTH-001 → AUTH-002 → AUTH-003 → AUTH-004
    ↓
ING-001 → ING-002 → AI-001 → UX-001 → UX-002
    ↓        ↓        ↓
  AI-002 → DAT-001 → DAT-002
    ↓
  AI-003
    ↓
  UX-003
```

## Current Status

| Feature | Spec | Record | Implementation | Files | F-xxx | Status Notes |
|---------|------|--------|----------------|-------|-------|--------------|
| AUTH-001 | ⏸️ Pending | ⏸️ - | ⏸️ Pending | - | F-000 | Authentication layer not implemented |
| AUTH-002 | ⏸️ Pending | ⏸️ - | ⏸️ Pending | - | F-001 | Google social login not implemented |
| AUTH-003 | ⏸️ Pending | ⏸️ - | ⏸️ Pending | - | F-002 | Logout not implemented |
| AUTH-004 | ⏸️ Pending | ⏸️ - | ⏸️ Pending | - | F-003 | Account delete not implemented |
| AI-001 | ✅ [`AI-001.md`](specs/AI-001.md) | ✅ [`AI-001-record.md`](records/AI-001-record.md) | ✅ Implemented | `src/ai/summarizer.py` | F-005 | ⚠️ Spec requires 300-char limit update |
| AI-002 | ✅ [`AI-002.md`](specs/AI-002.md) | ✅ [`AI-002-record.md`](records/AI-002-record.md) | ✅ Implemented | `src/ai/metadata_extractor.py` | F-007 | ⚠️ OG image thumbnail not implemented |
| AI-003 | ⏸️ Pending | ⏸️ - | ⏸️ Pending | - | F-006 | Spec not created |
| ING-001 | ✅ [`ING-001.md`](specs/ING-001.md) | ✅ [`ING-001-record.md`](records/ING-001-record.md) | ✅ Implemented | `src/ingestion/share_handler.py` | F-004 | - |
| ING-002 | ✅ [`ING-002.md`](specs/ING-002.md) | ✅ [`ING-002-record.md`](records/ING-002-record.md) | ✅ Implemented | `src/ingestion/extractor.py` | F-005 | - |
| DAT-001 | ✅ [`DAT-001.md`](specs/DAT-001.md) | ✅ [`DAT-001-record.md`](records/DAT-001-record.md) | ✅ Implemented | `src/data/models.py`, `src/data/repository.py` | F-018 | ⚠️ Requires `status` field for INBOX/ARCHIVED (F-012) |
| DAT-002 | ✅ [`DAT-002.md`](specs/DAT-002.md) | ✅ [`DAT-002-record.md`](records/DAT-002-record.md) | ✅ Implemented | `src/data/models.py`, `src/data/repository.py`, `src/api/routes.py` | F-017, F-015 | ⚠️ `InterestTag` is user-created, not AI-generated (F-014 gap) |
| UX-001 | ✅ [`UX-001.md`](specs/UX-001.md) | ✅ [`UX-001-record.md`](records/UX-001-record.md) | ✅ Backend | `src/api/routes.py` (/content/pending) | F-008, F-009, F-010 | - |
| UX-002 | ✅ [`UX-002.md`](specs/UX-002.md) | ✅ [`UX-002-record.md`](records/UX-002-record.md) | ✅ Implemented | `src/api/routes.py` (/swipe, /content/kept, /content/discarded, /stats) | F-009, F-011 | ⚠️ Requires status field integration |
| UX-003 | ✅ [`UX-003.md`](specs/UX-003.md) | ⏸️ Pending | ⏸️ Pending | - | F-012 | ⚠️ Requires F-012 state transition logic |

## Next: AUTH-001 (App Entry & Login State)

**Rationale:**
- All features require authenticated user context
- AUTH-001 is prerequisite for AUTH-002/003/004
- Enables user-specific data access (DAT-001, DAT-002)
- Blocker for F-000 (no login → no INBOX/Archive access)

## Spec Updates Required

The following specs require updates to align with F-xxx requirements:

1. **AI-001**: Add 300-character limit constraint (F-005)
2. **AI-002**: Add OG image thumbnail crawling logic (F-007)
3. **DAT-001**: Add `status` field for INBOX/ARCHIVED states (F-012)
4. **UX-003**: Integrate F-012 state transition logic ("읽었어요" button, INBOX→ARCHIVED)
5. **Create AI-003**: AI Categorization spec for F-006

## Implementation Priority

1. **Phase 1A: Spec Alignment** (Documentation updates)
   - Update AI-001, AI-002 specs with F-xxx constraints
   - Create AI-003 spec
   - Update UX-003 with F-012 logic

2. **Phase 1B: Core Features** (Implementation)
   - AUTH-001 → AUTH-004 (Authentication layer)
   - DAT-001 update (status field for INBOX/ARCHIVED)
   - UX-003 implementation with state transitions

3. **Phase 1C: AI Enhancements**
   - AI-003 implementation (AI-generated tags)
   - AI-001/002 updates (300-char limit, OG images)
