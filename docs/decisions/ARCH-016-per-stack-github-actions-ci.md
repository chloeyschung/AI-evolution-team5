# ARCH-016: Per-Stack GitHub Actions CI Workflows

**Date:** 2026-04-30  
**Status:** accepted  
**ADR Version:** 1.0.0  
**Last Updated:** 2026-04-30  
**Owners:** suyoung (initiator), all team members

---

## Context

초기에는 `ios-ci.yml`이 `prototype-1` 브랜치에만 적용되어 있었다. 팀이 여러 브랜치에서 병렬로 작업하고, 프로젝트가 iOS / Python 백엔드 / Web Dashboard / Browser Extension 등 이질적인 스택으로 구성되어 있어 다음 문제가 발생했다:

- 다른 브랜치에서 작업하는 팀원은 CI 피드백을 전혀 받지 못함
- 단일 CI 파일로 모든 스택을 관리하면 iOS 변경 시 Python 테스트도 실행되는 등 불필요한 실행이 발생
- 스택별 빌드 환경(macOS vs ubuntu, Xcode vs Node vs Python)이 상이하여 하나의 job으로 통합이 어려움

## Decision

스택별로 독립된 GitHub Actions workflow 파일을 유지하고, `paths` 필터로 관련 파일이 변경될 때만 해당 CI가 실행되도록 한다. 모든 workflow는 `branches: ['**']`로 전 브랜치에 적용한다.

## Rationale

- **스택 독립성:** 각 스택은 실행 환경(runner OS, 언어 버전)이 다르므로 분리가 자연스럽다
- **효율성:** `paths` 필터로 관련 없는 CI 실행을 방지해 GitHub Actions 크레딧을 절약한다
- **팀 자율성:** 각 담당자가 자신의 workflow 파일만 수정하면 되므로 충돌이 없다
- **가시성:** Actions 탭에서 스택별로 CI 결과를 구분해서 볼 수 있다

## Alternatives Considered

| Option | Why rejected |
|---|---|
| 단일 `ci.yml`에 matrix로 모든 스택 통합 | iOS는 macOS runner 필수라 matrix 구성이 복잡해지고, paths 분기 로직이 지저분해짐 |
| `prototype-1` 브랜치만 유지 | 다른 팀원 브랜치에서 CI 피드백 불가 |
| 브랜치별로 별도 workflow | 브랜치가 늘어날수록 관리 불가 |

## Consequences

**Positive:**
- 모든 브랜치에서 push 시 즉시 CI 피드백을 받을 수 있음
- 관련 파일만 변경 시 해당 CI만 실행되어 빠른 피드백 루프
- 스택 담당자가 자신의 workflow 파일을 독립적으로 관리 가능

**Negative / trade-offs:**
- workflow 파일이 4개로 늘어남 (관리 포인트 증가)
- 이 변경사항이 `main`에 머지되어야 전 팀원에게 적용됨 (GitHub Actions는 main의 workflow를 기준으로 동작)

## Workflow 파일 구조

```
.github/workflows/
├── ios-ci.yml            # Briefly/ 변경 시 → xcodegen + xcodebuild (macOS runner)
├── python-ci.yml         # src/, tests/, pyproject.toml 변경 시 → ruff + black + pytest
├── web-ci.yml            # web-dashboard/ 변경 시 → tsc + vitest + vite build
└── browser-ext-ci.yml    # browser-extension/ 변경 시 → tsc + vite build
```

## Related git history

- 2026-04-30 `127087c`: ios-ci.yml 브랜치 필터를 prototype-1 → 전 브랜치('**')로 확장
- 2026-04-30 `7d530ec`: python-ci, web-ci, browser-ext-ci workflow 파일 추가
- Source scope: `suyoung-v1`

## Revision History

| Version | Date | Changes | Commit |
|---|---|---|---|
| 1.0.0 | 2026-04-30 | Initial ADR | 7d530ec |

## Related

- Other ADRs: `ARCH-011` (conventional commit governance — commit 메시지 규칙이 CI와 연관)
