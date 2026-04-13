# Master Project Spec (MPS): Briefly

## 1. Vision & Core Principles

**Briefly** is a knowledge management solution that transforms the "Information Cemetery" (saved but unread links) into an enjoyable, "bite-sized" consumption experience. We aim to reduce cognitive load and FOMO by providing instant, high-density summaries.

### Core Principles
- **Consumption over Collection**: We value understanding over mere saving. If a feature only encourages "hoarding," it is rejected.
- **Radical Brevity**: Everything must be "bite-sized." If a summary isn't digestible in 10 seconds, it's not a Briefly summary.
- **Guilt-Free Experience**: The UX should feel like a rewarding game (gamified achievement) rather than a mounting pile of chores.

## 2. Target Audience
- **Primary**: "Time-Poor" professionals and students (ages 20-40) who consume newsletters, LinkedIn, and YouTube but struggle to find time for deep reading.

## 3. High-Level Architecture

### 3.1. Tech Stack
- **Backend**: Python 3.13 (Managed with `uv`).
- **API Framework**: FastAPI (High performance, asynchronous).
- **AI Engine**: Cloud-based LLM APIs (Anthropic/OpenAI) for primary summarization, with potential for local LLM fallback/hybrid optimization.
- **Mobile App (MVP)**: React Native (Cross-platform iOS/Android).
- **Browser Extension (Phase 2)**: React-based extension.
- **Data Layer**: Hybrid approach.
    - **Local**: On-device storage for immediate access and privacy.
    - **Cloud**: Centralized DB for seamless cross-device synchronization (Mobile $\leftrightarrow$ Extension).

### 3.2. Core Workflow
1. **Authentication**:
    - App launch checks login state (AUTH-001).
    - Google social login (AUTH-002), logout (AUTH-003), account delete (AUTH-004).
2. **Ingestion**:
    - **Mobile**: OS-level "Share" sheet integration (e.g., user clicks 'Share' $\rightarrow$ 'Save to Briefly').
    - **Desktop**: Browser extension one-click save (Phase 2).
3. **Processing**: Content is sent to the backend $\rightarrow$ AI generates a 3-line summary $\rightarrow$ Metadata (source, type, date) is extracted.
4. **Consumption (The Swipe UX)**:
    - Users interact with a "Card Stack" of summaries.
    - **Right Swipe (Keep)**: Categorize/Tag for later.
    - **Left Swipe (Discard)**: Archive/Clear.

## 4. Roadmap

### Phase 1: MVP (Mobile Focus)
- [ ] **Authentication**: App entry, Google login, logout, account delete (AUTH-001 to AUTH-004).
- [ ] Core Ingestion (Mobile Share Sheet).
- [ ] AI Summarization Engine (3-line core) + AI Categorization.
- [ ] Swipe-based Card Stack UI.
- [ ] Basic Local/Cloud Sync.
- [ ] User Profile & Preferences.

### Phase 2: Ecosystem Expansion
- [ ] Browser Extension (Chrome/Whale).
- [ ] API-based auto-sync for LinkedIn/YouTube.

### Phase 3: Community & Personalization
- [ ] Interest-based "Trend Summary" community feeds.
- [ ] Advanced AI personalization based on swipe history.

## 5. Development Process (Spec-Driven Development)
Briefly follows a strict **Spec-Driven Development** workflow to eliminate "vibe coding" and technical debt.

### ID System
- **Engineering IDs** (AUTH-xxx, ING-xxx, AI-xxx, UX-xxx, DAT-xxx): Track implementation in specs, records, and code.
- **Product IDs** (F-xxx): High-level product requirements from `Briefly_FeatureList.md`.
- Cross-references maintained in `docs/feature-inventory.md` and `docs/dependency-matrix.md`.

### The Workflow Cycle
1. **Kickoff**: Define project vision in `docs/mps.md`.
2. **Discovery**: Inventory features in `docs/feature-inventory.md`.
3. **Specification**: Create atomic specs in `docs/specs/{ID}.md` using the template in `.local/atomic-spec-template.md`.
4. **Dependency Analysis**: Map relationships in `docs/dependency-matrix.md`.
5. **Planning**: Order implementation in `docs/plans/implementation-plan.md`.
6. **Implementation**: Code based on the spec.
7. **Recording**: Document completion in `docs/records/{ID}-record.md`.

### Operational Rules
- **No Spec $\rightarrow$ No Implementation**: No code is written without an approved atomic spec.
- **Sensory Verification**: Every feature must pass Visual, Auditory, and Tactile checks.
- **Atomic Commits**: Use `feat({ID}): summary` format, including Spec, Test, and Sensor results.
- **Context Assembly**: Use the principle in `.local/context-assembly.md` to curate only necessary files for a task.
