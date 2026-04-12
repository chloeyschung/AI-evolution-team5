# Feature Inventory

This document tracks all identified features for the **Briefly** project, categorized by their implementation phase.

## Phase 1: MVP (Mobile Focus)

### Ingestion
- [ ] **[ING-001] Mobile Share Sheet Integration**: Implement the ability for users to trigger "Save to Briefly" via the native OS share menu on iOS/Android.
- [ ] **[ING-002] URL Extraction & Cleaning**: A backend service to extract clean text/content from various shared URLs (News, Blogs, etc.).

### AI & Processing
- [x] **[AI-001] Core 3-Line Summarizer**: An AI-powered service that takes raw content and generates a high-density, 3-line summary. ✅ Implemented
- [x] **[AI-002] Multi-Modal Metadata Extraction**: Extract source platform, content type (video/text/image), and timestamp. ✅ Implemented

### User Experience (UX)
- [x] **[UX-001] Swipe Card Stack**: A mobile UI component that presents content as a deck of cards for rapid interaction. ✅ Backend (`/content/pending`)
- [x] **[UX-002] Swipe Actions (Keep/Discard)**: Implementation of the Right-Swipe (Keep/Tag) and Left-Swipe (Discard/Archive) logic. ✅ Implemented
- [ ] **[UX-003] Summary Detail View**: An "On-Demand" expansion view to see more details if the user wants to dive deeper.

### Data & Sync
- [x] **[DAT-001] Hybrid Storage Engine**: Implementation of local on-device storage with background synchronization to the cloud. ✅ Implemented
- [ ] **[DAT-002] User Profile & Preferences**: Basic storage for user settings and swipe history.

## Phase 2: Ecosystem Expansion

### Desktop/Web
- [ ] **[EXT-001] Browser Extension (MVP)**: A lightweight extension for Chrome/Whale to allow one-click saving from the desktop.
- [ ] **[EXT-002] Web Dashboard**: A web-based view for users to manage their "Knowledge Library" on a larger screen.

### Integrations
- [ ] **[INT-001] YouTube Auto-Sync**: Automatically ingest "Watch Later" or specific playlists via API.
- [ ] **[INT-002] LinkedIn/Social Sync**: Integration to pull saved posts from major professional networks.

## Phase 3: Advanced Features

### Intelligence & Community
- [ ] **[ADV-001] Personalized Trend Feed**: A curated feed of trending summaries based on the user's swipe history.
- [ ] **[ADV-002] Gamified Achievement System**: Visualizing "Knowledge Gained" to encourage daily consumption.
- [ ] **[ADV-003] Smart Reminders**: Push notifications triggered by user-defined "knowledge consumption windows."