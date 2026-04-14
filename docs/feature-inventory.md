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
- [x] **[AI-002] Multi-Modal Metadata Extraction** (F-007): Extract source platform, content type (video/text/image), timestamp, and OG image thumbnails. ✅ Implemented (OG thumbnail extraction added)
- [x] **[AI-003] AI Categorization** (F-006): Auto-classify content into AI-generated category tags (max 3 tags per content) using LLM. Free-form tags, no predefined category list. ✅ Implemented

### User Experience (UX)
- [x] **[UX-001] Swipe Card Stack** (F-008, F-009, F-010): A mobile UI component that presents content as a deck of cards for rapid interaction. Provides both swipe view (F-009) and list view (F-010). ✅ Backend (`/content/pending`)
- [x] **[UX-002] Swipe Actions (Keep/Discard)** (F-009, F-011): Implementation of the Right-Swipe (Keep) and Left-Swipe (Discard/Archive) logic. ✅ Implemented
- [x] **[UX-003] Summary Detail View** (F-012): An "On-Demand" expansion view to see more details with swipe history. ✅ Implemented (`GET /content/{id}`)
- [x] **[UX-004] Filter by Platform** (F-013): Filter saved content by source platform (YouTube, LinkedIn, etc.). Platform list dynamically generated from user's save history. ✅ Implemented
- [x] **[UX-005] Search by Title/Tag** (F-016): Real-time search across content titles and category tags. Search scope: INBOX + Archive integrated. ✅ Implemented
- [x] **[UX-006] Delete Content** (F-019): Permanently delete individual saved content. 1-step confirmation popup. Irreversible. ✅ Implemented

### Data & Sync
- [x] **[DAT-001] Hybrid Storage Engine** (F-018): Implementation of local on-device storage with background synchronization to the cloud. ✅ Implemented
- [x] **[DAT-002] User Profile & Preferences** (F-017, F-015): Storage for user settings, preferences, statistics, and swipe history. ⚠️ F-014 AI category filtering not implemented—`InterestTag` is for user-created tags, not AI-generated tags. ✅ Implemented

## Phase 2: Ecosystem Expansion

### Desktop/Web
- [x] **[EXT-001] Browser Extension (MVP)**: A lightweight extension for Chrome/Whale to allow one-click saving from the desktop. ✅ Implemented
- [x] **[EXT-002] Web Dashboard**: A web-based view for users to manage their "Knowledge Library" on a larger screen. ✅ Implemented

### Integrations
- [x] **[INT-001] YouTube Auto-Sync**: Automatically ingest "Watch Later" or specific playlists via API. ✅ Implemented
- [x] **[INT-002] LinkedIn/Social Sync**: Integration to pull saved posts from major professional networks. ✅ Implemented (MVP: manual import via public URLs; OAuth flow ready for future activation)

## Phase 3: Advanced Features

### Intelligence & Community
- [x] **[ADV-001] Personalized Trend Feed**: A curated feed of trending summaries based on the user's swipe history. ✅ Implemented (relevance scoring with interest match, tag similarity, recency, engagement)
- [x] **[ADV-002] Gamified Achievement System**: Visualizing "Knowledge Gained" to encourage daily consumption. ✅ Implemented (16 achievements across streak, volume, diversity, curation categories)
- [x] **[ADV-003] Smart Reminders**: Push notifications triggered by user-defined "knowledge consumption windows." ✅ Implemented (4 reminder types: backlog, streak, time-based, reengagement; quiet hours, frequency limits, activity pattern learning)