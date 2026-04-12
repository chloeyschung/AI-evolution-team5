# Dependency Matrix

Feature dependency mapping for optimal implementation order.

## Legend

- `→` : Depends on (must be implemented before)
- `↔` : Bidirectional dependency (tightly coupled)
- `⇢` : Soft dependency (recommended but not required)

## Dependency Tables

### Ingestion Layer

| Feature | Depends On | Blocked By | Notes |
|---------|------------|------------|-------|
| **ING-001** Mobile Share Sheet | - | - | Entry point |
| **ING-002** URL Extraction | ING-001 | - | Needs URL from share sheet |

### AI & Processing Layer

| Feature | Depends On | Blocked By | Notes |
|---------|------------|------------|-------|
| **AI-001** Core Summarizer | ING-002 | - | Needs extracted text |
| **AI-002** Metadata Extraction | ING-001 | - | Works with URL directly |

### UX Layer

| Feature | Depends On | Blocked By | Notes |
|---------|------------|------------|-------|
| **UX-001** Swipe Card Stack | AI-001, AI-002 | - | Needs summary + metadata |
| **UX-002** Swipe Actions | UX-001, DAT-001 | - | Persists Keep/Discard |
| **UX-003** Detail View | UX-001, AI-002 | - | Shows source content |

### Data Layer

| Feature | Depends On | Blocked By | Notes |
|---------|------------|------------|-------|
| **DAT-001** Hybrid Storage | AI-002 | - | Stores metadata + summary |
| **DAT-002** User Profile | DAT-001 | - | Extends storage engine |

## Implementation Order

### Wave 1: Foundation
1. **ING-001** Mobile Share Sheet Integration

### Wave 2: Core Processing
2. **AI-002** Metadata Extraction ✅
3. **ING-002** URL Extraction & Cleaning
4. **AI-001** Core 3-Line Summarizer ✅

### Wave 3: Data Persistence
5. **DAT-001** Hybrid Storage Engine ✅

### Wave 4: User Experience
6. **UX-001** Swipe Card Stack ✅ Backend
7. **UX-002** Swipe Actions ✅
8. **UX-003** Detail View
9. **DAT-002** User Profile

## Critical Path

```
ING-001 → ING-002 → AI-001 → UX-001 → UX-002
     ↓        ↓
   AI-002 → DAT-001 → DAT-002
```

## Current Status

| Feature | Spec | Implementation | Files |
|---------|------|----------------|-------|
| AI-001 | ✅ [`AI-001.md`](specs/AI-001.md) | ✅ Implemented | `src/ai/summarizer.py` |
| AI-002 | ✅ [`AI-002.md`](specs/AI-002.md) | ✅ Implemented | `src/ai/metadata_extractor.py` |
| ING-001 | ✅ [`ING-001.md`](specs/ING-001.md) | ✅ Implemented | `src/ingestion/share_handler.py` |
| ING-002 | ✅ [`ING-002.md`](specs/ING-002.md) | ✅ Implemented | `src/ingestion/extractor.py` |
| DAT-001 | ✅ [`DAT-001.md`](specs/DAT-001.md) | ✅ Implemented | `src/data/models.py`, `src/data/repository.py` |
| UX-001 | ✅ [`UX-001.md`](specs/UX-001.md) | ✅ Backend | `src/api/routes.py` (/content/pending) |
| UX-002 | ✅ [`UX-002.md`](specs/UX-002.md) | ✅ Implemented | `src/api/routes.py` (/swipe, /content/kept, /content/discarded, /stats) |
| UX-003 | ⏸️ Pending | ⏸️ Pending | - |
| DAT-002 | ⏸️ Pending | ⏸️ Pending | - |

## Next: UX-003 (Detail View)

**Rationale:**
- UX-001 backend complete (`/content/pending` API)
- UX-002 complete (swipe persistence: `/swipe`, `/content/kept`, `/content/discarded`, `/stats`)
- UX-003 depends on UX-001 + AI-002, both ready
