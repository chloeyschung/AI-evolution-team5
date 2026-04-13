# Dependency Matrix

Feature dependency mapping for optimal implementation order.

**Note:** Engineering IDs (ING-xxx, AI-xxx, UX-xxx, DAT-xxx, AUTH-xxx) track implementation. Product requirements use F-xxx IDs from `Briefly_FeatureList.md`. Cross-references provided where applicable.

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
| **AI-001** Core Summarizer | ING-002 | - | Needs extracted text | F-005 |
| **AI-002** Metadata Extraction | ING-001 | - | Works with URL directly | F-007 |
| **AI-003** AI Categorization | ING-002 | - | LLM-based auto-tagging (max 3 tags) | F-006 |

### UX Layer

| Feature | Depends On | Blocked By | Notes | F-xxx Mapping |
|---------|------------|------------|-------|---------------|
| **UX-001** Swipe Card Stack | AI-001, AI-002 | - | Needs summary + metadata | F-008, F-009, F-010 |
| **UX-002** Swipe Actions | UX-001, DAT-001 | - | Persists Keep/Discard | F-009, F-011 |
| **UX-003** Detail View | UX-001, AI-002 | - | Shows source content, "읽었어요" transition | F-012 |

### Data Layer

| Feature | Depends On | Blocked By | Notes | F-xxx Mapping |
|---------|------------|------------|-------|---------------|
| **DAT-001** Hybrid Storage | AI-002 | - | Stores metadata + summary | F-018 |
| **DAT-002** User Profile | DAT-001 | - | Preferences, stats, interest tags | F-017, F-014*, F-015* |

*DAT-002 provides data models for F-014/F-015, but API integration pending.

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

| Feature | Spec | Record | Implementation | Files | F-xxx |
|---------|------|--------|----------------|-------|-------|
| AUTH-001 | ⏸️ Pending | ⏸️ - | ⏸️ Pending | - | F-000 |
| AUTH-002 | ⏸️ Pending | ⏸️ - | ⏸️ Pending | - | F-001 |
| AUTH-003 | ⏸️ Pending | ⏸️ - | ⏸️ Pending | - | F-002 |
| AUTH-004 | ⏸️ Pending | ⏸️ - | ⏸️ Pending | - | F-003 |
| AI-001 | ✅ [`AI-001.md`](specs/AI-001.md) | ✅ [`AI-001-record.md`](records/AI-001-record.md) | ✅ Implemented | `src/ai/summarizer.py` | F-005 |
| AI-002 | ✅ [`AI-002.md`](specs/AI-002.md) | ✅ [`AI-002-record.md`](records/AI-002-record.md) | ✅ Implemented | `src/ai/metadata_extractor.py` | F-007 |
| AI-003 | ⏸️ Pending | ⏸️ - | ⏸️ Pending | - | F-006 |
| ING-001 | ✅ [`ING-001.md`](specs/ING-001.md) | ✅ [`ING-001-record.md`](records/ING-001-record.md) | ✅ Implemented | `src/ingestion/share_handler.py` | F-004 |
| ING-002 | ✅ [`ING-002.md`](specs/ING-002.md) | ✅ [`ING-002-record.md`](records/ING-002-record.md) | ✅ Implemented | `src/ingestion/extractor.py` | F-005 |
| DAT-001 | ✅ [`DAT-001.md`](specs/DAT-001.md) | ✅ [`DAT-001-record.md`](records/DAT-001-record.md) | ✅ Implemented | `src/data/models.py`, `src/data/repository.py` | F-018 |
| DAT-002 | ✅ [`DAT-002.md`](specs/DAT-002.md) | ✅ [`DAT-002-record.md`](records/DAT-002-record.md) | ✅ Implemented | `src/data/models.py`, `src/data/repository.py`, `src/api/routes.py` | F-017, F-014*, F-015* |
| UX-001 | ✅ [`UX-001.md`](specs/UX-001.md) | ✅ [`UX-001-record.md`](records/UX-001-record.md) | ✅ Backend | `src/api/routes.py` (/content/pending) | F-008, F-009, F-010 |
| UX-002 | ✅ [`UX-002.md`](specs/UX-002.md) | ✅ [`UX-002-record.md`](records/UX-002-record.md) | ✅ Implemented | `src/api/routes.py` (/swipe, /content/kept, /content/discarded, /stats) | F-009, F-011 |
| UX-003 | ✅ [`UX-003.md`](specs/UX-003.md) | ⏸️ Pending | ⏸️ Pending | - | F-012 |

*DAT-002 provides data models (InterestTag, default_sort) but API filter/sort endpoints not yet integrated.

## Next: AUTH-001 (App Entry & Login State)

**Rationale:**
- All features require authenticated user context
- AUTH-001 is prerequisite for AUTH-002/003/004
- Enables user-specific data access (DAT-001, DAT-002)
- Blocker for F-000 (no login → no INBOX/Archive access)
