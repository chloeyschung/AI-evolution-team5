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
| **AI-001** Core Summarizer | ING-002 | - | Needs extracted text. 300-char limit enforced. | F-005 |
| **AI-002** Metadata Extraction | ING-001 | - | Works with URL directly. OG image thumbnail extraction implemented. | F-007 |
| **AI-003** AI Categorization | ING-002 | - | LLM-based auto-tagging (max 3 tags). ⏸️ Spec pending. | F-006 |

### UX Layer

| Feature | Depends On | Blocked By | Notes | F-xxx Mapping |
|---------|------------|------------|-------|---------------|
| **UX-001** Swipe Card Stack | AI-001, AI-002 | - | Needs summary + metadata. Provides F-008/F-009/F-010. | F-008, F-009, F-010 |
| **UX-002** Swipe Actions | UX-001, DAT-001 | - | Persists Keep/Discard. ✅ `status` field (INBOX/ARCHIVED) implemented. | F-009, F-011 |
| **UX-003** Detail View | UX-001, AI-002 | - | Shows source content with swipe history. ✅ Implemented (`GET /content/{id}`). | F-012 |
| **UX-004** Filter by Platform | UX-001 | - | Filter by source platform. Dynamic list from user's save history. ⏸️ Spec pending | F-013 |
| **UX-005** Search by Title/Tag | UX-001 | - | Real-time search across titles and tags. Scope: INBOX + Archive. ⏸️ Spec pending | F-016 |
| **UX-006** Delete Content | UX-001 | - | Permanent deletion with 1-step confirmation. Irreversible. ⏸️ Spec pending | F-019 |

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
| AUTH-001 | ✅ [`AUTH-001.md`](specs/AUTH-001.md) | ✅ [`AUTH-001-record.md`](records/AUTH-001-record.md) | ✅ Implemented | `src/auth/tokens.py`, `src/data/auth_repository.py` | F-000 | ✅ JWT auth, token refresh |
| AUTH-002 | ✅ [`AUTH-002.md`](specs/AUTH-002.md) | ✅ [`AUTH-002-record.md`](records/AUTH-002-record.md) | ✅ Implemented | `src/auth/google_oauth.py`, `src/api/routes.py` | F-001 | ✅ Google OAuth, 30-day block |
| AUTH-003 | ✅ [`AUTH-003.md`](specs/AUTH-003.md) | ✅ [`AUTH-003-record.md`](records/AUTH-003-record.md) | ✅ Implemented | `src/api/routes.py` | F-002 | ✅ Token revocation |
| AUTH-004 | ✅ [`AUTH-004.md`](specs/AUTH-004.md) | ✅ [`AUTH-004-record.md`](records/AUTH-004-record.md) | ✅ Implemented | `src/api/routes.py` | F-003 | ✅ 2-step delete, cascade |
| AI-001 | ✅ [`AI-001.md`](specs/AI-001.md) | ✅ [`AI-001-record.md`](records/AI-001-record.md) | ✅ Implemented | `src/ai/summarizer.py` | F-005 | ✅ 300-char limit enforced |
| AI-002 | ✅ [`AI-002.md`](specs/AI-002.md) | ✅ [`AI-002-record.md`](records/AI-002-record.md) | ✅ Implemented | `src/ai/metadata_extractor.py` | F-007 | ✅ OG image thumbnail extraction added |
| AI-003 | ✅ [`AI-003.md`](specs/AI-003.md) | ✅ [`AI-003-record.md`](records/AI-003-record.md) | ✅ Implemented | `src/ai/categorizer.py` | F-006 | ✅ LLM-based auto-tagging (max 3 tags) |
| ING-001 | ✅ [`ING-001.md`](specs/ING-001.md) | ✅ [`ING-001-record.md`](records/ING-001-record.md) | ✅ Implemented | `src/ingestion/share_handler.py` | F-004 | - |
| ING-002 | ✅ [`ING-002.md`](specs/ING-002.md) | ✅ [`ING-002-record.md`](records/ING-002-record.md) | ✅ Implemented | `src/ingestion/extractor.py` | F-005 | - |
| DAT-001 | ✅ [`DAT-001.md`](specs/DAT-001.md) | ✅ [`DAT-001-record.md`](records/DAT-001-record.md) | ✅ Implemented | `src/data/models.py`, `src/data/repository.py` | F-018 | ⚠️ Requires `status` field for INBOX/ARCHIVED (F-012) |
| DAT-002 | ✅ [`DAT-002.md`](specs/DAT-002.md) | ✅ [`DAT-002-record.md`](records/DAT-002-record.md) | ✅ Implemented | `src/data/models.py`, `src/data/repository.py`, `src/api/routes.py` | F-017, F-015 | ⚠️ `InterestTag` is user-created, not AI-generated (F-014 gap) |
| UX-001 | ✅ [`UX-001.md`](specs/UX-001.md) | ✅ [`UX-001-record.md`](records/UX-001-record.md) | ✅ Backend | `src/api/routes.py` (/content/pending) | F-008, F-009, F-010 | - |
| UX-002 | ✅ [`UX-002.md`](specs/UX-002.md) | ✅ [`UX-002-record.md`](records/UX-002-record.md) | ✅ Implemented | `src/api/routes.py` (/swipe, /content/kept, /content/discarded, /stats) | F-009, F-011 | ⚠️ Requires status field integration |
| UX-003 | ✅ [`UX-003.md`](specs/UX-003.md) | ✅ [`UX-003-record.md`](records/UX-003-record.md) | ✅ Implemented | `src/api/routes.py` (GET /content/{id}) | F-012 | ✅ Content detail with swipe history |
| UX-004 | ✅ [`UX-004.md`](specs/UX-004.md) | ✅ [`UX-004-record.md`](records/UX-004-record.md) | ✅ Implemented | `src/api/routes.py`, `src/data/repository.py` | F-013 | ✅ Filter by platform |
| UX-005 | ✅ [`UX-005.md`](specs/UX-005.md) | ✅ [`UX-005-record.md`](records/UX-005-record.md) | ✅ Implemented | `src/api/routes.py`, `src/data/repository.py` | F-016 | ✅ Search by title/author |
| UX-006 | ✅ [`UX-006.md`](specs/UX-006.md) | ✅ [`UX-006-record.md`](records/UX-006-record.md) | ✅ Implemented | `src/api/routes.py` | F-019 | ✅ Delete content |
| EXT-001 | ✅ [`EXT-001.md`](specs/EXT-001.md) | ✅ [`EXT-001-record.md`](records/EXT-001-record.md) | ✅ Implemented | `browser-extension/` | - | ✅ Chrome/Whale extension (Phase 2) |
| EXT-002 | ✅ [`EXT-002.md`](specs/EXT-002.md) | ✅ [`EXT-002-record.md`](records/EXT-002-record.md) | ✅ Implemented | `web-dashboard/` | - | ✅ Vue 3 web dashboard (Phase 2) |
| INT-001 | ✅ [`INT-001.md`](specs/INT-001.md) | ✅ [`INT-001-record.md`](records/INT-001-record.md) | ✅ Implemented | `src/integrations/youtube/`, `src/integrations/repositories/` | - | ✅ OAuth, sync configs, manual trigger |
| INT-002 | ✅ [`INT-002.md`](specs/INT-002.md) | ✅ [`INT-002-record.md`](records/INT-002-record.md) | ✅ Implemented (MVP) | `src/api/routes.py` | - | ✅ Manual import via public URLs; OAuth flow ready for future activation |
| ADV-001 | ✅ [`ADV-001.md`](specs/ADV-001.md) | ✅ [`ADV-001-record.md`](records/ADV-001-record.md) | ✅ Implemented | `src/ai/trend_analyzer.py`, `src/api/routes.py` | - | ✅ Relevance scoring with interest match, tag similarity, recency, engagement |
| ADV-002 | ✅ [`ADV-002.md`](specs/ADV-002.md) | ✅ [`ADV-002-record.md`](records/ADV-002-record.md) | ✅ Implemented | `src/ai/achievement_engine.py`, `src/api/routes.py` | - | ✅ 16 achievements across streak, volume, diversity, curation categories |
| ADV-003 | ✅ [`ADV-003.md`](specs/ADV-003.md) | ✅ [`ADV-003-record.md`](records/ADV-003-record.md) | ✅ Implemented | `src/ai/reminder_engine.py`, `src/api/routes.py` | - | ✅ 4 reminder types: backlog, streak, time-based, reengagement |

## Next: AUTH-001 (App Entry & Login State)

**Rationale:**
- All features require authenticated user context
- AUTH-001 is prerequisite for AUTH-002/003/004
- Enables user-specific data access (DAT-001, DAT-002)
- Blocker for F-000 (no login → no INBOX/Archive access)
