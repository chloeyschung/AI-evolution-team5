# Briefly

Swipe-based knowledge management app. Save articles, videos, links, and notes from a browser extension or native client, then decide what to keep with a lightweight inbox workflow.

한국어 README가 먼저 나오고, 같은 내용을 영어로 다시 제공합니다. 자세한 설치, 로컬 LLM, iOS 연동, 문서 업데이트 규칙은 [docs/SETUP_AND_INTEGRATION_GUIDE.md](docs/SETUP_AND_INTEGRATION_GUIDE.md)에 정리했습니다.

---

## 한국어

### 한눈에 보기

Briefly는 세 부분으로 구성됩니다.

| 영역 | 위치 | 역할 |
|---|---|---|
| Backend API | `src/` | FastAPI 서버. 인증, 콘텐츠 저장, 스와이프, DB, AI 요약, 외부 연동을 담당합니다. |
| Web Dashboard | `web-dashboard/` | React/Vite 웹앱. 저장한 콘텐츠를 보고 keep/discard/archive 합니다. |
| Browser Extension | `browser-extension/` | Chrome Manifest V3 확장. 현재 페이지나 선택 텍스트를 Briefly로 저장합니다. |
| Database | `briefly.db` | 로컬 개발용 SQLite DB. 서버 시작 시 필요한 테이블을 준비합니다. |
| Docs | `docs/` | 제품 의도, 스펙, 구현 순서, 완료 기록, 의사결정 문서가 있습니다. |

기본 로컬 주소는 다음과 같습니다.

| 서비스 | 주소 |
|---|---|
| API | `http://localhost:8000` |
| API 문서 | `http://localhost:8000/docs` |
| Health check | `http://localhost:8000/health` |
| Web Dashboard | `http://localhost:3001` |
| Mail catcher UI | `http://localhost:8025` |
| Local SMTP | `localhost:1025` |

### 빠른 시작

macOS:

```bash
git clone <repo-url> Briefly
cd Briefly
./scripts/run-stack.sh start
```

Windows:

```bat
git clone <repo-url> Briefly
cd Briefly
scripts\run-stack.bat start
```

실행 후 브라우저에서 `http://localhost:3001`을 엽니다. API 상태는 `http://localhost:8000/health`에서 확인합니다.

### 처음 준비해야 하는 것

1. Python 3.13
2. `uv`
3. Node.js 18 이상
4. Chrome 또는 Chromium 계열 브라우저
5. Google OAuth Client ID, Google 로그인을 테스트할 경우
6. 선택 사항: LM Studio 또는 Ollama 같은 로컬 LLM 서버

`run-stack` 스크립트는 로컬 개발에 필요한 `.env` 기본값을 만들고, 빠진 의존성을 설치한 뒤 다음 프로세스를 실행합니다.

| 프로세스 | 명령 |
|---|---|
| Mail catcher | `uv run python -m src.utils.mail_catcher` |
| Backend | `uv run uvicorn src.api.app:app --host 0.0.0.0 --port 8000 --reload` |
| Dashboard | `npm run dev` in `web-dashboard/` |
| Extension watch build | `npm run dev` in `browser-extension/` |

### 수동 실행

자동 스크립트 대신 터미널을 나누어 실행할 수도 있습니다.

```bash
uv sync
uv run uvicorn src.api.app:app --host 0.0.0.0 --port 8000 --reload
```

```bash
cd web-dashboard
npm install
npm run dev
```

```bash
cd browser-extension
npm install
npm run build
```

Chrome에서 `chrome://extensions/`를 열고 Developer mode를 켠 뒤 `browser-extension/dist/`를 Load unpacked로 불러옵니다.

### API와 환경 변수

Backend는 `/api/v1` 아래에 주요 API를 제공합니다. 모든 인증 필요 요청에는 다음 헤더를 붙입니다.

```http
Authorization: Bearer <access_token>
```

중요한 환경 변수:

| 변수 | 설명 |
|---|---|
| `JWT_SECRET_KEY` | 32자 이상 임의 문자열 |
| `ENCRYPTION_KEY` | Fernet 키. OAuth 토큰 암호화용 |
| `GOOGLE_CLIENT_ID` | Google OAuth Client ID |
| `GOOGLE_CLIENT_SECRET` | Google OAuth Client Secret |
| `GOOGLE_REDIRECT_URI` | 웹 OAuth callback 주소 |
| `EMAIL_LOOKUP_KEY` | 이메일 로그인 lookup 보호 키 |
| `DATABASE_URL` | 기본값 `sqlite+aiosqlite:///./briefly.db` |
| `SUMMARY_PROVIDER` | `auto`, `anthropic`, `openai`, `gemini` |
| `SUMMARY_BASE_URL` | 로컬 LLM 또는 외부 LLM API endpoint |
| `SUMMARY_MODEL` | 사용할 모델 이름 |
| `SUMMARY_API_KEY` | 로컬 서버면 더미 값 가능 |

자세한 API 요청 예시는 [상세 가이드](docs/SETUP_AND_INTEGRATION_GUIDE.md#ios--native-client-integration-korean)를 보세요.

### 로컬 LLM 테스트

초보자에게는 GUI가 있는 LM Studio가 가장 쉽고, 터미널이 편하면 Ollama도 좋습니다.

LM Studio 기본 설정:

```env
SUMMARY_PROVIDER=openai
SUMMARY_BASE_URL=http://localhost:1234/v1/chat/completions
SUMMARY_MODEL=<LM Studio에서 로드한 모델 이름>
SUMMARY_API_KEY=local
```

Ollama 기본 설정:

```env
SUMMARY_PROVIDER=openai
SUMMARY_BASE_URL=http://localhost:11434/v1/chat/completions
SUMMARY_MODEL=<ollama model name>
SUMMARY_API_KEY=ollama
```

이 repo의 `scripts/vllm-server.sh`는 별도 vLLM 서버를 `8180` 포트로 띄우는 고급 사용자용 helper입니다. 현재 FastAPI 런타임은 `SUMMARY_*` 값을 통해 요약 서버를 연결합니다.

### iOS 연동 포인트

iOS 앱은 Backend API를 직접 호출하면 됩니다.

| 목적 | Endpoint |
|---|---|
| 앱 설정, 강제 업데이트, 점검 모드 | `GET /api/v1/config/app` |
| Google ID token 로그인 | `POST /api/v1/auth/google` |
| Apple 로그인 | `POST /api/v1/auth/apple` |
| access token 갱신 | `POST /api/v1/auth/refresh` |
| Share Sheet 저장 | `POST /api/v1/share` |
| 콘텐츠 목록 | `GET /api/v1/content` |
| Inbox | `GET /api/v1/content/pending` |
| Keep/Discard | `POST /api/v1/swipe` |
| Push token 등록 | `POST /api/v1/user/device-token` |
| Universal Links | `GET /.well-known/apple-app-site-association` |

iOS 날짜 파싱 주의: API datetime은 문자열입니다. Swift `Codable` 기본 ISO8601 전략과 맞지 않는 값이 있을 수 있으므로 앱 쪽에서 custom `DateFormatter`를 준비하세요.

### 문서 업데이트 원칙

`docs/PROJECT-MANAGEMENT-FRAMEWORK.md` 기준으로 문서는 다음처럼 관리합니다.

| 상황 | 업데이트 문서 |
|---|---|
| 제품 의도나 기능 목록 변경 | `docs/external/Briefly_FeatureList.md` |
| 기능 요구사항 변경 | `docs/specs/{ID}.md` |
| 구현 상태 변경 | `docs/feature-inventory.md` |
| 기능 간 의존성 변경 | `docs/dependency-matrix.md` |
| 아키텍처 결정 | 새 `docs/decisions/ARCH-NNN-{slug}.md` |
| 기능 완료 | `docs/records/{ID}-record.md`에 append |
| README, 사용법, 운영 절차 변경 | `README.md` 또는 관련 guide 문서 |

스펙이나 FeatureList가 바뀌면 `doc-doc-sync` 후 `doc-code-sync` 순서로 검증합니다.

### 테스트

```bash
uv run pytest
```

```bash
cd web-dashboard
npm run typecheck
npm run test
npm run test:e2e
```

```bash
cd browser-extension
npm run typecheck
npm run test
npm run build
```

---

## English

### Overview

Briefly has three main runtime parts.

| Area | Path | Responsibility |
|---|---|---|
| Backend API | `src/` | FastAPI server for auth, content, swipes, DB, AI summaries, and integrations. |
| Web Dashboard | `web-dashboard/` | React/Vite dashboard for reviewing saved content. |
| Browser Extension | `browser-extension/` | Chrome MV3 extension for saving the current page or selected text. |
| Database | `briefly.db` | Local SQLite database for development. |
| Docs | `docs/` | Product intent, specs, implementation plans, records, and decisions. |

Default local URLs:

| Service | URL |
|---|---|
| API | `http://localhost:8000` |
| API docs | `http://localhost:8000/docs` |
| Health check | `http://localhost:8000/health` |
| Web Dashboard | `http://localhost:3001` |
| Mail catcher UI | `http://localhost:8025` |
| Local SMTP | `localhost:1025` |

### Quick Start

macOS:

```bash
git clone <repo-url> Briefly
cd Briefly
./scripts/run-stack.sh start
```

Windows:

```bat
git clone <repo-url> Briefly
cd Briefly
scripts\run-stack.bat start
```

Then open `http://localhost:3001`. Check the API at `http://localhost:8000/health`.

### Prerequisites

1. Python 3.13
2. `uv`
3. Node.js 18 or newer
4. Chrome or Chromium
5. Google OAuth Client ID if you want Google sign-in
6. Optional: LM Studio or Ollama for a local LLM API server

The stack launcher creates local `.env` defaults, installs missing dependencies, and starts:

| Process | Command |
|---|---|
| Mail catcher | `uv run python -m src.utils.mail_catcher` |
| Backend | `uv run uvicorn src.api.app:app --host 0.0.0.0 --port 8000 --reload` |
| Dashboard | `npm run dev` in `web-dashboard/` |
| Extension watch build | `npm run dev` in `browser-extension/` |

### Manual Run

```bash
uv sync
uv run uvicorn src.api.app:app --host 0.0.0.0 --port 8000 --reload
```

```bash
cd web-dashboard
npm install
npm run dev
```

```bash
cd browser-extension
npm install
npm run build
```

Open `chrome://extensions/`, enable Developer mode, and load `browser-extension/dist/` as an unpacked extension.

### API and Environment

Backend routes are served under `/api/v1`. Authenticated requests use:

```http
Authorization: Bearer <access_token>
```

Important environment variables:

| Variable | Meaning |
|---|---|
| `JWT_SECRET_KEY` | Random string, 32+ chars |
| `ENCRYPTION_KEY` | Fernet key for OAuth token encryption |
| `GOOGLE_CLIENT_ID` | Google OAuth Client ID |
| `GOOGLE_CLIENT_SECRET` | Google OAuth Client Secret |
| `GOOGLE_REDIRECT_URI` | Web OAuth callback URL |
| `EMAIL_LOOKUP_KEY` | Email login lookup protection key |
| `DATABASE_URL` | Defaults to `sqlite+aiosqlite:///./briefly.db` |
| `SUMMARY_PROVIDER` | `auto`, `anthropic`, `openai`, or `gemini` |
| `SUMMARY_BASE_URL` | Local or hosted LLM endpoint |
| `SUMMARY_MODEL` | Model name |
| `SUMMARY_API_KEY` | Can be a dummy value for local servers |

For request examples, see the [detailed guide](docs/SETUP_AND_INTEGRATION_GUIDE.md#ios--native-client-integration-english).

### Local LLM Testing

LM Studio is the easiest GUI option. Ollama is also friendly if you are comfortable with a terminal.

LM Studio:

```env
SUMMARY_PROVIDER=openai
SUMMARY_BASE_URL=http://localhost:1234/v1/chat/completions
SUMMARY_MODEL=<model loaded in LM Studio>
SUMMARY_API_KEY=local
```

Ollama:

```env
SUMMARY_PROVIDER=openai
SUMMARY_BASE_URL=http://localhost:11434/v1/chat/completions
SUMMARY_MODEL=<ollama model name>
SUMMARY_API_KEY=ollama
```

`scripts/vllm-server.sh` is an advanced helper for a separate vLLM server on port `8180`. The FastAPI app connects summaries through the `SUMMARY_*` variables.

### iOS Integration Points

Native clients should call the Backend API directly.

| Purpose | Endpoint |
|---|---|
| App config, force update, maintenance | `GET /api/v1/config/app` |
| Google ID token login | `POST /api/v1/auth/google` |
| Apple login | `POST /api/v1/auth/apple` |
| Refresh access token | `POST /api/v1/auth/refresh` |
| Share Sheet ingestion | `POST /api/v1/share` |
| Content list | `GET /api/v1/content` |
| Inbox | `GET /api/v1/content/pending` |
| Keep/Discard | `POST /api/v1/swipe` |
| Push token registration | `POST /api/v1/user/device-token` |
| Universal Links | `GET /.well-known/apple-app-site-association` |

Datetime fields are API strings. Some values may not include a timezone suffix, so Swift clients should use an explicit decoder strategy.

### Documentation Rules

The repo follows `docs/PROJECT-MANAGEMENT-FRAMEWORK.md`.

| Change | Update |
|---|---|
| Product intent or feature list | `docs/external/Briefly_FeatureList.md` |
| Feature requirements | `docs/specs/{ID}.md` |
| Implementation status | `docs/feature-inventory.md` |
| Feature dependencies | `docs/dependency-matrix.md` |
| Architecture decision | New `docs/decisions/ARCH-NNN-{slug}.md` |
| Completed feature | Append to `docs/records/{ID}-record.md` |
| Usage or operation docs | `README.md` or a guide under `docs/` |

When a spec or FeatureList changes, run doc-doc sync before doc-code sync.

### Tests

```bash
uv run pytest
```

```bash
cd web-dashboard
npm run typecheck
npm run test
npm run test:e2e
```

```bash
cd browser-extension
npm run typecheck
npm run test
npm run build
```
