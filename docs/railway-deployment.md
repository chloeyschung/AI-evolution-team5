# Briefly 백엔드 Railway 배포 안내

## 구조 요약

```
iOS 앱 (Xcode 빌드)
웹 대시보드 (별도 배포)     →  Railway 백엔드 서버  →  PostgreSQL DB
브라우저 확장프로그램
```

Railway는 `src/` 안의 FastAPI 백엔드만 실행합니다.
나머지(iOS, 웹, 확장프로그램)는 이 서버에 API 요청을 보내는 클라이언트입니다.

---

## 백엔드 URL

```
https://briefly-api-production-2a40.up.railway.app/api/v1
```

---

## 영향도

| 작업 | Railway에 영향 | 로컬 코드에 영향 |
|------|--------------|----------------|
| `git pull` (백엔드 코드 수정) | ❌ 자동 반영 안 됨 | ✅ |
| `railway up` 실행 | ✅ 현재 로컬 코드 배포됨 | ❌ |
| iOS 앱 Xcode 빌드 | ❌ | ❌ |
| Railway 환경변수 변경 | ✅ 서버에만 저장됨 | ❌ |

---

## 백엔드 배포 방법

팀원이 백엔드 코드를 수정했을 때:

```bash
git pull
railway up
```

이 두 줄로 끝납니다. 환경변수, DB 세팅은 건드릴 필요 없습니다.

---

## 앱 개발자 (iOS) 유의사항

- Railway 서버는 24/7 운영 중이므로 **로컬 백엔드를 직접 켤 필요 없음**
- **cloudflared도 필요 없음**
- Xcode 빌드 후 폰에서 바로 테스트 가능
- 단, **시뮬레이터**는 자동으로 `localhost:8000` 사용 → 시뮬레이터 테스트 시에만 로컬 백엔드 실행 필요

---

## 백엔드 개발자 유의사항

- 코드 수정 후 `railway up` 실행해야 서버에 반영됨 (자동 배포 아님)
- DB는 PostgreSQL (Railway) — 로컬 SQLite와 별개, 데이터 공유 안 됨
- 환경변수는 Railway 서버에 저장되어 있어 별도 세팅 불필요

---

## URL 변경이 필요한 경우 (긴급 시)

Account 탭 → 우상단 안테나 아이콘 → URL 직접 입력 → 저장 → 앱 재시작
