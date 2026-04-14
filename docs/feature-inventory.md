# Feature Inventory

This document tracks all identified features for the **Briefly** project, categorized by their implementation phase.

**Note:** This inventory uses engineering IDs (ING-xxx, AI-xxx, UX-xxx, DAT-xxx, AUTH-xxx) for implementation tracking. Product requirements are defined in `docs/Briefly_FeatureList.md` with F-xxx IDs. Cross-references are provided where applicable.

## Phase 1: MVP (Mobile Focus)

### Authentication (AUTH)
- [x] **[AUTH-001] App Entry & Login State** (F-000): Check login state on app launch. If unauthenticated, show login screen immediately. Maintain login state across app restarts with token auto-refresh. ✅ Implemented
- [x] **[AUTH-002] Social Login — Google** (F-001): One-tap Google sign-in. Auto-create account on first login. Rejection of re-registration for deleted accounts within 30 days. ✅ Implemented
- [x] **[AUTH-003] Logout** (F-002): End current session. Local data retained, syncs on re-login. ✅ Implemented
- [x] **[AUTH-004] Account Delete** (F-003): Permanent deletion of account and all data. 2-step confirmation. 30-day re-registration block. Full server + local data deletion. ✅ Implemented

### Ingestion
- [x] **[ING-001] Mobile Share Sheet Integration** (F-004): Implement the ability for users to trigger "Save to Briefly" via the native OS share menu on iOS/Android. ✅ Implemented
- [x] **[ING-002] URL Extraction & Cleaning** (F-005): A backend service to extract clean text/content from various shared URLs (News, Blogs, etc.). ✅ Implemented

### AI & Processing
- [x] **[AI-001] Core 3-Line Summarizer** (F-005): An AI-powered service that takes raw content and generates a high-density, 3-line summary (max 300 chars). ✅ Implemented (300-char limit enforced)
- [x] **[AI-002] Multi-Modal Metadata Extraction** (F-007): Extract source platform, content type (video/text/image), timestamp, and OG image thumbnails. ✅ Implemented
- [x] **[AI-003] AI Categorization** (F-006): Auto-classify content into AI-generated category tags (max 3 tags per content) using LLM. Free-form tags, no predefined category list. ✅ Implemented

### User Experience (UX)
- [x] **[UX-001] Swipe Card Stack** (F-008, F-009, F-010): A mobile UI component that presents content as a deck of cards for rapid interaction. Provides card components (F-008), swipe view (F-009), and list view (F-010). ✅ Backend (`/content/pending`)
- [x] **[UX-002] Swipe Actions (Keep/Discard)** (F-009, F-011): Implementation of the Right-Swipe (Keep) and Left-Swipe (Discard/Archive) logic. Provides Archive tab functionality (F-011). ✅ Implemented
- [x] **[UX-003] Summary Detail View** (F-012): An "On-Demand" expansion view to see more details with swipe history. ✅ Implemented (`GET /content/{id}`)
- [x] **[UX-004] Filter by Platform** (F-013): Filter saved content by source platform (YouTube, LinkedIn, etc.). Platform list dynamically generated from user's save history. ✅ Implemented
- [x] **[UX-005] Search by Title/Tag** (F-016): Real-time search across content titles, authors, and AI-generated tags. Search scope: INBOX + Archive integrated. ✅ Implemented
- [x] **[UX-006] Delete Content** (F-019): Permanently delete individual saved content. 1-step confirmation popup. Irreversible. ✅ Implemented

### Data & Sync
- [x] **[DAT-001] Hybrid Storage Engine** (F-018): Implementation of local on-device storage with background synchronization to the cloud. ✅ Implemented
- [x] **[DAT-002] User Profile & Preferences** (F-017, F-015): Storage for user settings, preferences, statistics, and swipe history. ✅ Implemented
- [x] **[UX-007] Filter by AI Category** (F-014): Filter saved content by AI-generated category tags. ✅ Implemented (`tags` query parameter on `/content/pending`, `/content/kept`, `/content/discarded`)

## Phase 2: Ecosystem Expansion

### Desktop/Web
- [x] **[EXT-001] Browser Extension (MVP)** (F-020): A lightweight extension for Chrome/Whale to allow one-click saving from the desktop. ⚠️ Backend API ready; frontend not in repo
- [x] **[EXT-002] Web Dashboard** (F-021): A web-based view for users to manage their "Knowledge Library" on a larger screen. ⚠️ Backend API ready; frontend not in repo

### Integrations
- [x] **[INT-001] YouTube Auto-Sync** (F-022): Automatically ingest "Watch Later" or specific playlists via API. ⚠️ Backend API ready (src/integrations/youtube/)
- [x] **[INT-002] LinkedIn/Social Sync** (F-023): Integration to pull saved posts from major professional networks. ⚠️ Backend API ready (MVP: manual import via public URLs; OAuth flow ready)

## Phase 3: Advanced Features

### Intelligence & Community
- [x] **[ADV-001] Personalized Trend Feed** (F-024): A curated feed of trending summaries based on the user's swipe history. ⚠️ Backend API ready (interest match 35%, tag similarity 30%, recency 20%, engagement 15%; hard limit 1000 items)
- [x] **[ADV-002] Gamified Achievement System** (F-025): Visualizing "Knowledge Gained" to encourage daily consumption. ⚠️ Backend API ready (16 achievements across streak, volume, diversity, curation categories)
- [x] **[ADV-003] Smart Reminders** (F-026): Push notifications triggered by user-defined "knowledge consumption windows." ⚠️ Backend API ready (4 reminder types: backlog, streak, time-based, reengagement; quiet hours, frequency limits)

## Security & Infrastructure

### Security (SEC)
- [x] **[SEC-001] Security Hardening**: Comprehensive security measures for authentication, data protection, and access control. ✅ Implemented
  - **JWT Token Security**: SHA-256 hashing before storage, minimum 32-char secret key validation, signature verification
  - **OAuth Token Encryption**: Fernet-based symmetric encryption for OAuth tokens at rest
  - **Rate Limiting**: Token bucket algorithm with per-endpoint limits (10/minute for share, 30/minute for ingest)
  - **SSRF Protection**: DNS rebinding prevention, private IP blocking, strict URL validation
  - **Multi-User Data Isolation**: user_id filtering on all repository methods, unique constraints

### Code Quality (QOL)
- [x] **[QOL-001] Code Quality Improvements**: Centralized constants, standardized type hints, improved maintainability. ✅ Implemented
  - **Enum Consolidation**: All enums (SwipeAction, Theme, DefaultSort, ContentStatus, Provider, ErrorCode) centralized in `src/constants.py`
  - **Type Hint Standardization**: Python 3.10+ union syntax (`X | None`) throughout codebase
  - **Constants Centralization**: 20+ constants for pagination, limits, time-based values, scoring weights
  - **Error Code Standardization**: `ErrorCode` enum for consistent API error responses