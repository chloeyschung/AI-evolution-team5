# Briefly Setup and Integration Guide

This guide is written for non-developers who need to run Briefly locally, connect the browser extension and web dashboard, test a local LLM server, or understand how native iOS clients should call the backend.

한국어 설명이 먼저 나오고, 영어 설명이 뒤에 나옵니다.

---

## Korean

### 1. 전체 그림

Briefly는 로컬 컴퓨터에서 네 가지를 함께 띄워서 테스트합니다.

| 이름 | 무슨 일을 하나요? | 기본 주소 |
|---|---|---|
| Backend API | 데이터를 저장하고 로그인, 요약, 스와이프를 처리합니다. | `http://localhost:8000` |
| Web Dashboard | 저장된 콘텐츠를 눈으로 보고 정리합니다. | `http://localhost:3001` |
| Browser Extension | Chrome에서 보고 있는 페이지를 저장합니다. | Chrome 확장 |
| Mail Catcher | 이메일 인증, 비밀번호 재설정 메일을 로컬에서 보여줍니다. | `http://localhost:8025` |

`localhost`는 "내 컴퓨터 안에서만 열리는 주소"라는 뜻입니다.

### 2. macOS 준비

1. Terminal을 엽니다.
2. Apple Silicon 또는 Intel Mac 모두 Python 3.13, Node.js 18 이상, Chrome이 필요합니다.
3. `uv`를 설치합니다.

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

4. Terminal을 새로 열고 설치 확인을 합니다.

```bash
uv --version
python --version
node --version
npm --version
```

5. repo 폴더에서 실행합니다.

```bash
cd /path/to/Briefly
./scripts/run-stack.sh start
```

중지:

```bash
./scripts/run-stack.sh stop
```

상태 확인:

```bash
./scripts/run-stack.sh status
```

### 3. Windows 준비

1. PowerShell 또는 Windows Terminal을 엽니다.
2. Python 3.13, Node.js 18 이상, Chrome을 설치합니다.
3. `uv`를 설치합니다.

```powershell
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

4. 터미널을 새로 열고 설치 확인을 합니다.

```powershell
uv --version
python --version
node --version
npm --version
```

5. repo 폴더에서 실행합니다.

```bat
cd C:\project\Briefly
scripts\run-stack.bat start
```

중지:

```bat
scripts\run-stack.bat stop
```

상태 확인:

```bat
scripts\run-stack.bat status
```

Windows 스크립트는 각 서비스를 별도 창으로 띄우고 PID 파일을 `C:\project\Briefly\.stack.pids`에 저장합니다.

### 4. 의존성 동기화와 dist build

자동 스크립트를 쓰면 보통 직접 할 필요가 없습니다. 그래도 수동으로 확인하려면 아래 순서를 사용합니다.

Backend:

```bash
uv sync
uv run pytest
```

Web Dashboard:

```bash
cd web-dashboard
npm install
npm run build
```

빌드 결과는 `web-dashboard/dist/`에 생깁니다.

Browser Extension:

```bash
cd browser-extension
npm install
npm run build
```

빌드 결과는 `browser-extension/dist/`에 생깁니다. Chrome에는 이 폴더를 Load unpacked로 넣습니다.

### 5. Browser Extension 설치

1. `browser-extension/.env`를 준비합니다.

```env
VITE_GOOGLE_CLIENT_ID=your-client-id.apps.googleusercontent.com
VITE_API_BASE_URL=http://localhost:8000
VITE_SHOW_API_URL_SETTING=false
```

2. 확장을 빌드합니다.

```bash
cd browser-extension
npm run build
```

3. Chrome에서 `chrome://extensions/`를 엽니다.
4. Developer mode를 켭니다.
5. Load unpacked를 누르고 `browser-extension/dist/` 폴더를 선택합니다.
6. Briefly 아이콘을 눌러 로그인하고 현재 페이지 저장을 테스트합니다.

Google 로그인은 extension 코드에서 Chrome의 `chrome.identity.launchWebAuthFlow`를 사용합니다. 실제 운영 OAuth 설정은 Google Cloud Console의 Client ID와 redirect URI 정책을 확인해야 합니다.

### 6. Web Dashboard 실행

`web-dashboard/.env` 예시:

```env
VITE_GOOGLE_CLIENT_ID=your-google-client-id.apps.googleusercontent.com
VITE_API_BASE_URL=/api
```

로컬 개발에서는 `/api`를 유지하면 Vite가 API 요청을 `http://localhost:8000`으로 proxy합니다.

실행:

```bash
cd web-dashboard
npm run dev
```

브라우저에서 `http://localhost:3001`을 엽니다.

### 7. Backend 환경 변수

루트 `.env`에 들어가는 핵심 값입니다. `run-stack` 스크립트가 로컬 기본값을 만들어 주지만, Google 로그인이나 실제 LLM을 쓰려면 직접 값을 넣어야 합니다.

| 변수 | 예시 | 설명 |
|---|---|---|
| `JWT_SECRET_KEY` | 긴 랜덤 문자열 | 로그인 토큰 서명 |
| `ENCRYPTION_KEY` | Fernet key | OAuth token 암호화 |
| `GOOGLE_CLIENT_ID` | `...apps.googleusercontent.com` | Google 로그인 |
| `GOOGLE_CLIENT_SECRET` | Google secret | OAuth code exchange |
| `GOOGLE_REDIRECT_URI` | `http://localhost:3001/oauth-callback` | 웹 callback |
| `EMAIL_LOOKUP_KEY` | 긴 랜덤 문자열 | 이메일 로그인 보호 |
| `SMTP_HOST` | `localhost` | 로컬 메일 서버 |
| `SMTP_PORT` | `1025` | 로컬 SMTP 포트 |
| `DATABASE_URL` | `sqlite+aiosqlite:///./briefly.db` | DB 위치 |
| `APP_BASE_URL` | `http://localhost:3001` | 이메일 링크 base URL |
| `ALLOWED_ORIGINS` | `http://localhost:3001` | 브라우저 CORS 허용 origin |
| `ALLOWED_ORIGIN_REGEX` | `chrome-extension://[a-z]{32}` | Chrome extension origin 허용 |

### 8. 로컬 LLM 서버

Briefly의 AI 요약은 `src/ai/summarizer.py`가 담당합니다. 서버 시작 시 `src/api/app.py`가 다음 값을 읽어 summarizer를 구성합니다.

| 변수 | 설명 |
|---|---|
| `SUMMARY_PROVIDER` | `auto`, `anthropic`, `openai`, `gemini` |
| `SUMMARY_BASE_URL` | API 요청을 보낼 전체 URL |
| `SUMMARY_MODEL` | 모델 이름 |
| `SUMMARY_API_KEY` | API 키. 로컬 서버는 더미 문자열 가능 |

#### LM Studio

LM Studio는 GUI로 모델을 받고 서버를 켤 수 있어서 비개발자에게 가장 쉽습니다.

1. LM Studio를 설치합니다.
2. 모델을 하나 다운로드합니다.
3. Developer 탭에서 Start server를 켭니다.
4. 기본 OpenAI-compatible 주소는 보통 `http://localhost:1234/v1`입니다.
5. Briefly `.env`에 아래처럼 넣습니다.

```env
SUMMARY_PROVIDER=openai
SUMMARY_BASE_URL=http://localhost:1234/v1/chat/completions
SUMMARY_MODEL=<LM Studio에 표시되는 모델 이름>
SUMMARY_API_KEY=local
```

#### Ollama

Ollama는 설치 후 백그라운드에서 `http://localhost:11434` API를 제공합니다.

```bash
ollama pull llama3.2
ollama run llama3.2
```

Briefly `.env`:

```env
SUMMARY_PROVIDER=openai
SUMMARY_BASE_URL=http://localhost:11434/v1/chat/completions
SUMMARY_MODEL=llama3.2
SUMMARY_API_KEY=ollama
```

#### vLLM helper

`scripts/vllm-server.sh`는 고급 사용자용입니다. 기본 포트는 `8180`이고, 환경 변수로 모델 경로와 포트를 바꿀 수 있습니다. 일반 로컬 테스트는 LM Studio 또는 Ollama를 권장합니다.

### 9. 주요 API 양식

모든 API는 기본적으로 `http://localhost:8000/api/v1` 아래에 있습니다.

인증된 요청:

```http
Authorization: Bearer <access_token>
Content-Type: application/json
```

#### 이메일 회원가입

```http
POST /api/v1/auth/register
Content-Type: application/json
```

```json
{
  "email": "user@example.com",
  "password": "safe-password",
  "display_name": "Jane"
}
```

#### 이메일 로그인

```http
POST /api/v1/auth/login
Content-Type: application/json
```

```json
{
  "email": "user@example.com",
  "password": "safe-password"
}
```

응답에는 `access_token`, `refresh_token`, `expires_at`, `user`가 포함됩니다.

#### Google ID token 로그인

```http
POST /api/v1/auth/google
Content-Type: application/json
```

```json
{
  "google_id_token": "<token-from-google-sdk>",
  "google_user_info": {
    "id": "1234567890",
    "email": "user@example.com",
    "name": "Jane Doe",
    "picture": "https://example.com/avatar.png"
  }
}
```

#### 토큰 갱신

```http
POST /api/v1/auth/refresh
Content-Type: application/json
```

```json
{
  "refresh_token": "<stored-refresh-token>"
}
```

#### 콘텐츠 직접 추가

```http
POST /api/v1/content
Authorization: Bearer <access_token>
Content-Type: application/json
```

```json
{
  "platform": "web",
  "content_type": "article",
  "url": "https://example.com/article",
  "title": "Example Article",
  "author": "Example Author"
}
```

#### Share Sheet 또는 Extension 저장

```http
POST /api/v1/share
Authorization: Bearer <access_token>
Content-Type: application/json
```

```json
{
  "content": "https://example.com/article",
  "platform": "web",
  "metadata": {
    "url": "https://example.com/article",
    "title": "Example Article",
    "author": "Example Author",
    "description": "Short description",
    "content_type": "article"
  },
  "options": {
    "auto_summarize": true
  }
}
```

#### Keep 또는 Discard

```http
POST /api/v1/swipe
Authorization: Bearer <access_token>
Content-Type: application/json
```

```json
{
  "content_id": 1,
  "action": "keep"
}
```

`action`은 `keep` 또는 `discard`입니다.

### iOS / Native Client Integration Korean

iOS 앱은 Web Dashboard를 거치지 않고 Backend API와 직접 통신합니다.

#### 앱 시작 시

1. `GET /api/v1/config/app` 호출
2. `is_maintenance=true`이면 점검 화면 표시
3. `min_version`, `min_ios_version`이 앱보다 높으면 업데이트 안내
4. 저장된 refresh token이 있으면 `POST /api/v1/auth/refresh`

#### 로그인

Google Sign-In SDK 또는 Apple Sign-In SDK에서 받은 토큰을 backend로 보냅니다.

Google:

```http
POST /api/v1/auth/google
```

Apple:

```http
POST /api/v1/auth/apple
```

응답 token은 Keychain에 저장합니다. `access_token`은 API 호출마다 Authorization header에 넣습니다.

#### Share Extension

iOS Share Extension은 URL 또는 텍스트를 `POST /api/v1/share`로 보냅니다. 사용자가 보고 있는 URL, title, author, description을 `metadata`에 넣으면 backend가 저장하고 필요하면 요약합니다.

#### DB 연결

iOS가 DB에 직접 연결하지 않습니다. DB는 backend 내부 구현입니다. iOS는 API 응답만 신뢰해야 합니다.

#### Universal Links

루트 `.env`:

```env
APPLE_TEAM_ID=XXXXXXXXXX
APPLE_BUNDLE_ID=com.briefly.app
```

서버가 `GET /.well-known/apple-app-site-association`를 제공합니다. Xcode에서는 Associated Domains에 다음을 추가합니다.

```text
applinks:<your-domain>
```

로컬 `localhost`는 실제 iOS Universal Links 검증에 적합하지 않습니다. 실기기 검증에는 HTTPS 도메인이 필요합니다.

#### Swift 날짜 파싱

API datetime은 문자열입니다. 안전하게 처리하려면 custom decoder를 둡니다.

```swift
let decoder = JSONDecoder()
let formatter = DateFormatter()
formatter.dateFormat = "yyyy-MM-dd'T'HH:mm:ss"
formatter.locale = Locale(identifier: "en_US_POSIX")
decoder.dateDecodingStrategy = .formatted(formatter)
```

### 10. iOS 시뮬레이터 로컬 테스트 (IOS-001)

iOS 시뮬레이터는 Mac의 `localhost`를 그대로 공유하므로, 백엔드를 `./scripts/run-stack.sh start`로 띄운 뒤 별도 IP 설정 없이 바로 연결됩니다.

#### 사전 인증 개발 계정 생성

```bash
# 이메일 인증 없이 즉시 로그인 가능한 개발 계정 생성 (최초 1회)
uv run python scripts/seed_dev_user.py
# 이미 존재하면 "Dev user already exists" 출력 후 종료
```

생성된 계정:

| 이메일 | 비밀번호 |
|--------|---------|
| `test@localhost` | `testpass123` |

#### 추가 테스트 계정 생성 (컨텍스트별)

```bash
uv run python scripts/create_test_user.py "기능명-또는-버그명"
# 예: uv run python scripts/create_test_user.py "ios-share-ext-test"
# 출력: debug-ios-share-ext-test-20260430-01@test.com / testtest
```

#### 시뮬레이터 테스트 절차

1. 백엔드 실행: `./scripts/run-stack.sh start`
2. Xcode에서 Briefly 스킴 선택 → 시뮬레이터 빌드 및 실행
3. 앱의 **Account** 탭 이동
4. 이메일: `test@localhost`, 비밀번호: `testpass123` 입력 → 로그인 버튼
5. 로그인 성공 시 이메일 표시 확인, 로그아웃 후 폼으로 복귀 확인

#### 유의 사항

- `Info.plist`에 `localhost` HTTP ATS 예외가 설정되어 있습니다. 실기기(실제 기기)에서는 HTTPS 서버가 필요합니다.
- 토큰은 App Group UserDefaults(`group.com.briefly.shared`)에 저장되어 Share Extension과 공유됩니다.
- 현재는 토큰 만료 시 재로그인이 필요합니다 (자동 갱신은 IOS-004에서 구현 예정).

### 11. Project Management Framework 문서 업데이트 규칙

`docs/PROJECT-MANAGEMENT-FRAMEWORK.md`는 어떤 문서가 현재 상태를 대표하고, 어떤 문서가 과거 기록인지 구분합니다.

#### Source of truth 순서

1. `docs/external/Briefly_FeatureList.md` - 제품 의도
2. `docs/specs/{ID}.md` - 기능별 구현 요구사항
3. `docs/feature-inventory.md` - repo 기준 구현 상태
4. `docs/decisions/ARCH-NNN-{slug}.md` - 아키텍처 제약
5. `docs/mps.md` - 배경 설명
6. `docs/records/` - 완료 후 기록

#### 언제 무엇을 업데이트하나요?

| 상황 | 문서 | 형식 |
|---|---|---|
| 새 기능을 정의 | `docs/specs/{ID}.md` | `docs/templates/spec-template.md` 사용 |
| 제품 기능 목록 변경 | `docs/external/Briefly_FeatureList.md` | upstream 내용을 Markdown mirror로 정리 |
| 구현 상태 변경 | `docs/feature-inventory.md` | feature ID, status, evidence 갱신 |
| 기능 간 선후관계 변경 | `docs/dependency-matrix.md` | row depends on column 형식 유지 |
| 구현 순서 계획 | `docs/plans/implementation-plan.md` | snapshot 성격. 새 계획은 새 파일 고려 |
| 아키텍처 결정 | `docs/decisions/ARCH-NNN-{slug}.md` | ADR template 사용, 기존 ADR 수정 대신 새 ADR |
| 기능 완료 | `docs/records/{ID}-record.md` | append-only. 테스트와 sensor 결과 추가 |
| README와 사용법 변경 | `README.md`, `docs/*guide*.md` | 실제 코드와 실행 명령 기준으로 업데이트 |

#### Snapshot 문서

`docs/audit/`, `docs/plans/`, `docs/PREMORTEM.md`, `docs/WHYTREE.md`는 특정 시점의 기록입니다. 새 분석이 필요하면 기존 파일을 고치기보다 새 파일을 만듭니다.

#### Live 문서

FeatureList, specs, feature inventory, dependency matrix는 현재 코드와 제품 의도를 반영해야 합니다. 스펙이나 FeatureList가 바뀌면 doc-doc sync 후 doc-code sync를 수행합니다.

---

## English

### 1. Mental Model

Briefly runs four local pieces during development.

| Name | What it does | Default URL |
|---|---|---|
| Backend API | Stores data and handles auth, summaries, and swipes. | `http://localhost:8000` |
| Web Dashboard | Shows and organizes saved content. | `http://localhost:3001` |
| Browser Extension | Saves the current Chrome page. | Chrome extension |
| Mail Catcher | Shows local email verification and reset messages. | `http://localhost:8025` |

`localhost` means "an address on your own computer."

### 2. macOS Setup

1. Open Terminal.
2. Install Python 3.13, Node.js 18 or newer, and Chrome.
3. Install `uv`.

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

4. Open a new Terminal and verify:

```bash
uv --version
python --version
node --version
npm --version
```

5. Start the stack:

```bash
cd /path/to/Briefly
./scripts/run-stack.sh start
```

Stop:

```bash
./scripts/run-stack.sh stop
```

Status:

```bash
./scripts/run-stack.sh status
```

### 3. Windows Setup

1. Open PowerShell or Windows Terminal.
2. Install Python 3.13, Node.js 18 or newer, and Chrome.
3. Install `uv`.

```powershell
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

4. Open a new terminal and verify:

```powershell
uv --version
python --version
node --version
npm --version
```

5. Start the stack:

```bat
cd C:\project\Briefly
scripts\run-stack.bat start
```

Stop:

```bat
scripts\run-stack.bat stop
```

Status:

```bat
scripts\run-stack.bat status
```

The Windows script opens each service in its own window and stores process IDs in `C:\project\Briefly\.stack.pids`.

### 4. Dependency Sync and dist Builds

Backend:

```bash
uv sync
uv run pytest
```

Web Dashboard:

```bash
cd web-dashboard
npm install
npm run build
```

The output is `web-dashboard/dist/`.

Browser Extension:

```bash
cd browser-extension
npm install
npm run build
```

The output is `browser-extension/dist/`. Load that folder in Chrome.

### 5. Browser Extension Setup

1. Prepare `browser-extension/.env`.

```env
VITE_GOOGLE_CLIENT_ID=your-client-id.apps.googleusercontent.com
VITE_API_BASE_URL=http://localhost:8000
VITE_SHOW_API_URL_SETTING=false
```

2. Build:

```bash
cd browser-extension
npm run build
```

3. Open `chrome://extensions/`.
4. Turn on Developer mode.
5. Click Load unpacked and select `browser-extension/dist/`.
6. Click the Briefly extension icon, sign in, and save the current page.

### 6. Web Dashboard

`web-dashboard/.env`:

```env
VITE_GOOGLE_CLIENT_ID=your-google-client-id.apps.googleusercontent.com
VITE_API_BASE_URL=/api
```

For local development, `/api` lets Vite proxy requests to `http://localhost:8000`.

Run:

```bash
cd web-dashboard
npm run dev
```

Open `http://localhost:3001`.

### 7. Backend Environment

Root `.env` values:

| Variable | Example | Meaning |
|---|---|---|
| `JWT_SECRET_KEY` | long random string | Token signing |
| `ENCRYPTION_KEY` | Fernet key | OAuth token encryption |
| `GOOGLE_CLIENT_ID` | `...apps.googleusercontent.com` | Google sign-in |
| `GOOGLE_CLIENT_SECRET` | Google secret | OAuth code exchange |
| `GOOGLE_REDIRECT_URI` | `http://localhost:3001/oauth-callback` | Web callback |
| `EMAIL_LOOKUP_KEY` | long random string | Email auth lookup protection |
| `SMTP_HOST` | `localhost` | Local mail server |
| `SMTP_PORT` | `1025` | Local SMTP port |
| `DATABASE_URL` | `sqlite+aiosqlite:///./briefly.db` | DB location |
| `APP_BASE_URL` | `http://localhost:3001` | Email link base URL |
| `ALLOWED_ORIGINS` | `http://localhost:3001` | Browser CORS origins |
| `ALLOWED_ORIGIN_REGEX` | `chrome-extension://[a-z]{32}` | Chrome extension CORS origin |

### 8. Local LLM Server

AI summaries are handled by `src/ai/summarizer.py`. At startup, `src/api/app.py` reads:

| Variable | Meaning |
|---|---|
| `SUMMARY_PROVIDER` | `auto`, `anthropic`, `openai`, or `gemini` |
| `SUMMARY_BASE_URL` | Full API URL to call |
| `SUMMARY_MODEL` | Model name |
| `SUMMARY_API_KEY` | Can be a dummy string for local servers |

#### LM Studio

1. Install LM Studio.
2. Download a model.
3. Open the Developer tab and start the server.
4. The common OpenAI-compatible base is `http://localhost:1234/v1`.
5. Set Briefly:

```env
SUMMARY_PROVIDER=openai
SUMMARY_BASE_URL=http://localhost:1234/v1/chat/completions
SUMMARY_MODEL=<model name shown in LM Studio>
SUMMARY_API_KEY=local
```

#### Ollama

Ollama serves its API on `http://localhost:11434`.

```bash
ollama pull llama3.2
ollama run llama3.2
```

Briefly `.env`:

```env
SUMMARY_PROVIDER=openai
SUMMARY_BASE_URL=http://localhost:11434/v1/chat/completions
SUMMARY_MODEL=llama3.2
SUMMARY_API_KEY=ollama
```

#### vLLM helper

`scripts/vllm-server.sh` is for advanced users. It defaults to port `8180`; use LM Studio or Ollama for basic local testing.

### 9. Main API Shapes

All API paths are under `http://localhost:8000/api/v1`.

Authenticated requests:

```http
Authorization: Bearer <access_token>
Content-Type: application/json
```

#### Register

```http
POST /api/v1/auth/register
Content-Type: application/json
```

```json
{
  "email": "user@example.com",
  "password": "safe-password",
  "display_name": "Jane"
}
```

#### Login

```http
POST /api/v1/auth/login
Content-Type: application/json
```

```json
{
  "email": "user@example.com",
  "password": "safe-password"
}
```

The response includes `access_token`, `refresh_token`, `expires_at`, and `user`.

#### Google ID Token Login

```http
POST /api/v1/auth/google
Content-Type: application/json
```

```json
{
  "google_id_token": "<token-from-google-sdk>",
  "google_user_info": {
    "id": "1234567890",
    "email": "user@example.com",
    "name": "Jane Doe",
    "picture": "https://example.com/avatar.png"
  }
}
```

#### Refresh Token

```http
POST /api/v1/auth/refresh
Content-Type: application/json
```

```json
{
  "refresh_token": "<stored-refresh-token>"
}
```

#### Add Content

```http
POST /api/v1/content
Authorization: Bearer <access_token>
Content-Type: application/json
```

```json
{
  "platform": "web",
  "content_type": "article",
  "url": "https://example.com/article",
  "title": "Example Article",
  "author": "Example Author"
}
```

#### Share Sheet or Extension Save

```http
POST /api/v1/share
Authorization: Bearer <access_token>
Content-Type: application/json
```

```json
{
  "content": "https://example.com/article",
  "platform": "web",
  "metadata": {
    "url": "https://example.com/article",
    "title": "Example Article",
    "author": "Example Author",
    "description": "Short description",
    "content_type": "article"
  },
  "options": {
    "auto_summarize": true
  }
}
```

#### Keep or Discard

```http
POST /api/v1/swipe
Authorization: Bearer <access_token>
Content-Type: application/json
```

```json
{
  "content_id": 1,
  "action": "keep"
}
```

`action` is `keep` or `discard`.

### iOS / Native Client Integration English

Native iOS clients should call the Backend API directly.

#### App Launch

1. Call `GET /api/v1/config/app`.
2. If `is_maintenance=true`, show maintenance UI.
3. Compare `min_version` and `min_ios_version`.
4. If a refresh token exists, call `POST /api/v1/auth/refresh`.

#### Login

Send provider tokens from the native SDK to the backend.

Google:

```http
POST /api/v1/auth/google
```

Apple:

```http
POST /api/v1/auth/apple
```

Store returned tokens in Keychain. Send `access_token` in the Authorization header.

#### Share Extension

The iOS Share Extension should send URLs or text to `POST /api/v1/share`. Put URL, title, author, and description in `metadata`; the backend stores the item and may summarize it.

#### DB Connection

iOS never connects to the DB directly. The database is an internal backend detail. iOS should trust only API responses.

#### Universal Links

Root `.env`:

```env
APPLE_TEAM_ID=XXXXXXXXXX
APPLE_BUNDLE_ID=com.briefly.app
```

The backend serves `GET /.well-known/apple-app-site-association`. In Xcode, add Associated Domains:

```text
applinks:<your-domain>
```

`localhost` is not suitable for real Universal Links validation. Use an HTTPS domain for device testing.

#### Swift Date Parsing

Use an explicit date decoder for API datetime strings.

```swift
let decoder = JSONDecoder()
let formatter = DateFormatter()
formatter.dateFormat = "yyyy-MM-dd'T'HH:mm:ss"
formatter.locale = Locale(identifier: "en_US_POSIX")
decoder.dateDecodingStrategy = .formatted(formatter)
```

### 10. iOS Simulator Local Testing (IOS-001)

The iOS Simulator shares the Mac's `localhost`, so no additional IP configuration is needed. Start the backend with `./scripts/run-stack.sh start` before running the simulator.

#### Create a pre-verified dev account

```bash
# Creates a dev account that skips email verification (run once)
uv run python scripts/seed_dev_user.py
# Prints "Dev user already exists" if already present
```

Credentials:

| Email | Password |
|-------|----------|
| `test@localhost` | `testpass123` |

#### Create additional test accounts (per context)

```bash
uv run python scripts/create_test_user.py "feature-or-bug-name"
# Example: uv run python scripts/create_test_user.py "ios-share-ext-test"
# Output: debug-ios-share-ext-test-20260430-01@test.com / testtest
```

#### Simulator test procedure

1. Start the backend: `./scripts/run-stack.sh start`
2. In Xcode, select the Briefly scheme → build and run in the Simulator
3. Navigate to the **Account** tab
4. Enter email `test@localhost` and password `testpass123` → tap Login
5. Confirm the email address appears; tap Logout and confirm the form returns

#### Notes

- `Info.plist` includes an ATS exception for `localhost` HTTP only. A physical device requires an HTTPS backend.
- Tokens are stored in App Group UserDefaults (`group.com.briefly.shared`), shared with the Share Extension.
- Token expiry currently requires manual re-login (automatic refresh is planned for IOS-004).

### 11. Project Management Framework Documentation Rules

`docs/PROJECT-MANAGEMENT-FRAMEWORK.md` separates current truth from historical records.

#### Source-of-truth order

1. `docs/external/Briefly_FeatureList.md` - product intent
2. `docs/specs/{ID}.md` - feature requirements
3. `docs/feature-inventory.md` - repo implementation status
4. `docs/decisions/ARCH-NNN-{slug}.md` - architecture constraints
5. `docs/mps.md` - background
6. `docs/records/` - retrospective records

#### What to update and when

| Situation | Document | Format |
|---|---|---|
| Define a new feature | `docs/specs/{ID}.md` | Use `docs/templates/spec-template.md` |
| Product feature list changes | `docs/external/Briefly_FeatureList.md` | Keep as Markdown mirror of upstream intent |
| Implementation status changes | `docs/feature-inventory.md` | Update feature ID, status, evidence |
| Feature dependency changes | `docs/dependency-matrix.md` | Keep row-depends-on-column matrix format |
| Implementation sequencing | `docs/plans/implementation-plan.md` | Snapshot style. Consider a new file for a new plan |
| Architecture decision | `docs/decisions/ARCH-NNN-{slug}.md` | Use ADR template. Prefer new ADR over editing old ADR |
| Feature completed | `docs/records/{ID}-record.md` | Append-only test and sensor evidence |
| Usage docs change | `README.md`, `docs/*guide*.md` | Match real code and commands |

#### Snapshot docs

`docs/audit/`, `docs/plans/`, `docs/PREMORTEM.md`, and `docs/WHYTREE.md` are point-in-time records. For new analysis, create a new file instead of rewriting history.

#### Live docs

FeatureList, specs, feature inventory, and dependency matrix should reflect current product intent and code. When a spec or FeatureList changes, run doc-doc sync before doc-code sync.

---

## Sources Checked for Current Install Notes

- [uv installation docs](https://docs.astral.sh/uv/getting-started/installation/)
- [LM Studio local server docs](https://lmstudio.ai/docs/developer/core/server)
- [LM Studio OpenAI-compatible endpoints](https://lmstudio.ai/docs/app/api/endpoints/openai/)
- [Ollama macOS docs](https://docs.ollama.com/macos)
- [Ollama Windows docs](https://docs.ollama.com/windows)
- [Ollama OpenAI compatibility docs](https://docs.ollama.com/openai)
