# TODOS — Briefly

/autoplan에서 자동으로 생성됨. 2026-04-10.

---

## Phase 2 (AI 요약) — prototype-1 이후

- [ ] Claude API (claude-haiku-4-5) 연동
- [ ] URLSession + SwiftSoup HTML 파싱
- [ ] async/await 비동기 처리
- [ ] API 키 관리 (Keychain 사용, 하드코딩 금지)
- [ ] 요약 결과 SavedItem에 저장

## Phase 3 (Swipe UX) — Phase 2 이후

- [ ] DragGesture 카드 스택 구현
- [ ] CardStackView.swift
- [ ] SummaryCardView.swift
- [ ] Right Swipe → Keep (태그 저장)
- [ ] Left Swipe → Discard (아카이브)
- [ ] 게이미피케이션: 하루 소화 카드 수 표시

## 배포 인프라 — 필요시

- [ ] Apple Developer 계정 설정 확인 (팀 내 보유자)
- [ ] TestFlight Ad-hoc 배포 설정
- [ ] GitHub Actions CI (빌드 확인)

## 전략 (CEO 리뷰에서 도출)

- [ ] Readwise Reader 대비 Briefly 차별점 1줄 정의
- [ ] 5명 유저 인터뷰 (3줄 요약 포맷 검증)
- [ ] 성공 지표 정의: "5명이 1주일 안에 각 3개 이상 링크 저장"

## 코드 품질

- [ ] BrieflyTests/ 유닛 테스트 작성 (test plan: ~/.gstack/projects/...)
- [ ] DESIGN.md 작성 (Phase 2 전에 /design-consultation 실행)
