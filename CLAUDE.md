# Briefly — Project Configuration

## Project
- **앱명:** Briefly (iOS)
- **브랜치 전략:** `main` (기준), `prototype-1` (현재 개발 브랜치)
- **계획 파일:** `docs/plan.md`

## gstack Skills

This project uses [gstack](https://github.com/garrytan/gstack) — AI-powered software factory skills.

Available slash commands:

| Command | Phase | Description |
|---------|-------|-------------|
| `/think` or `/investigate` | Think | Root-cause debugging, systematic analysis |
| `/autoplan` | Plan | Auto-review pipeline (CEO → Design → Eng → DX) |
| `/plan-ceo-review` | Plan | Product/strategy evaluation |
| `/plan-eng-review` | Plan | Engineering architecture review |
| `/review` | Review | Pre-landing PR review with specialist analysis |
| `/qa` | Test | Systematic QA with auto-fix |
| `/ship` | Ship | Complete shipping workflow |
| `/retro` | Reflect | Retrospective with learning capture |
| `/browse` | Utility | Headless browser (use instead of built-in web tools) |
| `/careful` | Safety | Safety guardrails |

Use `/browse` for all web browsing tasks instead of built-in browser tools.

## Development (iOS)

- **Language:** Swift / SwiftUI
- **Min Target:** iOS 16.0
- **Key targets:** `Briefly` (main app), `BrieflyShareExtension` (Share Extension)
- **App Group:** `group.com.briefly.shared`
- **Build:** Xcode

## Progress Tracking

All feature progress is tracked in `docs/plan.md`. Update the progress log and checklist after each working session.
