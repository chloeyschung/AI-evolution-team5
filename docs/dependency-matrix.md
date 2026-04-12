# Dependency Matrix

This document maps feature dependencies to determine optimal implementation order.

## Legend

- `→` : Depends on (must be implemented before)
- `↔` : Bidirectional dependency (tightly coupled)
- `⇢` : Soft dependency (recommended but not required)

## Phase 1: MVP Dependencies

### Ingestion Layer

| Feature | Depends On | Blocked By | Notes |
|---------|------------|------------|-------|
| **ING-001** Mobile Share Sheet | - | - | Entry point, no dependencies |
| **ING-002** URL Extraction | ING-001 | - | Needs URL from share sheet |

### AI & Processing Layer

| Feature | Depends On | Blocked By | Notes |
|---------|------------|------------|-------|
| **AI-001** Core Summarizer | ING-002 | - | Needs extracted text |
| **AI-002** Metadata Extraction | ING-001 | - | Can work with URL directly |

### UX Layer

| Feature | Depends On | Blocked By | Notes |
|---------|------------|------------|-------|
| **UX-001** Swipe Card Stack | AI-001, AI-002 | - | Needs summary + metadata to display |
| **UX-002** Swipe Actions | UX-001, DAT-001 | - | Needs storage for Keep/Discard |
| **UX-003** Detail View | UX-001, AI-002 | - | Needs metadata for source link |

### Data Layer

| Feature | Depends On | Blocked By | Notes |
|---------|------------|------------|-------|
| **DAT-001** Hybrid Storage | AI-002 | - | Stores metadata + summary |
| **DAT-002** User Profile | DAT-001 | - | Extends storage engine |

## Implementation Order (Topologically Sorted)

### Wave 1: Foundation (No Dependencies)
1. **ING-001** Mobile Share Sheet Integration
   - Entry point for all content
   - Provides URL to downstream features

### Wave 2: Core Processing
2. **AI-002** Multi-Modal Metadata Extraction ✅ *Completed*
   - Can work independently with URL
   - Provides platform/type classification

3. **ING-002** URL Extraction & Cleaning
   - Depends on ING-001 for URL source
   - Provides clean text for summarizer

4. **AI-001** Core 3-Line Summarizer ✅ *Completed*
   - Depends on ING-002 for input text
   - Generates final summary output

### Wave 3: Data Persistence
5. **DAT-001** Hybrid Storage Engine ✅
   - Depends on AI-002 metadata structure
   - Stores summaries + metadata

### Wave 4: User Experience
6. **UX-001** Swipe Card Stack ⚠️ Backend Only
   - Depends on AI-001 + AI-002 output
   - Backend: pending content API implemented
   - Frontend: React Native component (pending)

7. **UX-002** Swipe Actions
   - Depends on UX-001 + DAT-001
   - Persists Keep/Discard decisions

8. **UX-003** Detail View
   - Depends on UX-001 + AI-002
   - Shows source content

9. **DAT-002** User Profile
   - Depends on DAT-001
   - Adds user preferences

## Critical Path

```
ING-001 → ING-002 → AI-001 → UX-001 → UX-002
     ↓        ↓
   AI-002 → DAT-001 → DAT-002
```

## Next Recommended: UX-003

**Rationale:**
- UX-001 backend support complete (pending content API implemented)
- UX-002 (Swipe Actions) complete - all CRUD operations for swipe decisions
- UX-003 (Detail View) depends on UX-001 + AI-002, both ready
- Unlocks source content viewing after swipe decisions

## Current Status

| Feature | Spec | Implementation | Files |
|---------|------|----------------|-------|
| AI-001 | ⏸️ Pending | ✅ Implemented | `src/ai/summarizer.py` |
| AI-002 | ⏸️ Pending | ✅ Implemented | `src/ai/metadata_extractor.py` |
| ING-001 | ✅ [`docs/specs/ING-001.md`](specs/ING-001.md) | ✅ Implemented | `src/ingestion/share_handler.py` |
| ING-002 | ⏸️ Pending | ✅ Implemented | `src/ingestion/extractor.py` |
| DAT-001 | ✅ [`docs/specs/DAT-001.md`](specs/DAT-001.md) | ✅ Implemented | `src/data/models.py`, `src/data/repository.py`, `src/api/app.py` |
| UX-001 | ✅ [`docs/specs/UX-001.md`](specs/UX-001.md) | ⚠️ Backend Only | `src/data/repository.py` (get_pending), `src/api/routes.py` (/content/pending) |
| UX-002 | ✅ [`docs/specs/UX-002.md`](specs/UX-002.md) | ✅ Implemented | `src/api/schemas.py`, `src/data/repository.py`, `src/api/routes.py` |
| UX-003 | ⏸️ Pending | ⏸️ Pending | - |
| DAT-002 | ⏸️ Pending | ⏸️ Pending | - |
