# Briefly — Design System

> **Single source of truth for design tokens, components, and interaction patterns.**
> Audience: Claude Code (HTML/CSS/JS today, iOS Swift later).
> Manifesto link: every decision below ties back to one of the three core values — *Consumption over Collection*, *Radical Brevity*, *Guilt-Free Experience*.

---

## 1. Brand & Mood

### 1.1 Visual tone — 5 adjectives

| Adjective | What it means in pixels |
|---|---|
| **Calm** | 채도 낮은 색, 충분한 여백, 부드러운 그림자. 정보 과잉의 반대편에 선다. |
| **Editorial** | 잡지처럼 정돈된 타이포그래피. 세리프 디스플레이 + 산세리프 본문 페어. |
| **Warm** | 화이트 베이스 위에 따뜻한 다크 올리브 그린으로 차분한 무게감. "공부 앱"의 차가운 느낌이 아니라 "잘 만든 잡지" 같은 점잖은 톤. |
| **Crisp** | 한 화면에 한 가지 일만. 카드 한 장 = 한 정보. 군더더기 0. |
| **Encouraging** | 빨간 경고/미완료 대신 응원하는 톤. 비주얼도 압박감 없이. |

### 1.2 References (닮고 싶은 것)

| 앱 / 브랜드 | 왜 |
|---|---|
| **Reeder 5** (RSS 리더) | 한 화면에 한 글, 압도하지 않는 정보 밀도. 우리 카드 1장 = 1정보 원칙과 일치. |
| **Things 3** (To-do) | "오늘 할 일"의 가벼움. 빈 상태(empty state)를 죄책감이 아닌 성취로 보여줌. |
| **Readwise / Matter** | 따뜻한 페이퍼 톤, 세리프 + 산세리프 페어링, AI 요약을 점잖게 다루는 방식. |
| **Arc Browser** | 색을 절제하지만 결정적인 순간(전환, 성취)에 과감히 씀. |
| **Headspace** | "Guilt-Free" 톤. 압박 대신 응원. 일러스트보다 톤이 우선. |

### 1.3 Anti-references (피해야 할 것)

- **빨강/주황 위주의 알림형 디자인** (Todoist의 미완료 빨간 점) — Guilt-Free 원칙 위반.
- **Notion 식 무한 캔버스 / 다중 패널** — Radical Brevity 위반. 우리는 모으는 곳이 아니라 소화하는 곳.
- **Duolingo 식 게이미피케이션의 과잉** (스트릭 잃었다는 위협, 불꽃 이모지 도배) — 응원의 선을 넘는 순간 피로.
- **다크 모드 = 새카만 #000** — 따뜻한 톤을 잃음. 우리의 다크는 *warm dark*.
- **AI 슬롭 그라데이션 보라/파랑** — 신뢰감과 무관, 정체성도 없음.

---

## 2. Color System

기본 톤: **클린한 화이트 + 다크 올리브 그린**. 화이트 베이스 위에 절제된 다크 카키 그린으로 진지하고 잡지스러운 분위기.

### 2.1 Primary — Olive Forest (지식 / Keep / 메인 액션)

> "오래된 군용 노트의 카키" — 진중하게 깊고, 채도를 낮춰 텍스트와도 자연스럽게 어울리는 다크 올리브 그린. Keep 액션의 시각적 앵커.

| Token | Hex | 용도 |
|---|---|---|
| `--color-primary-50`  | `#F0F2EA` | Hover/selected 배경 (사이드바 선택 상태) |
| `--color-primary-100` | `#DDE0CE` | 칩 배경, 부드러운 강조 |
| `--color-primary-200` | `#B8BFA1` | 비활성 보더 |
| `--color-primary-300` | `#929977` | 보조 텍스트 위 강조 |
| `--color-primary-400` | `#6E7654` | 링크 hover |
| `--color-primary-500` | `#4F5938` | **Primary 액션 기본** (Keep 버튼, 토글 on) |
| `--color-primary-600` | `#3A4229` | **로고 / 헤더 강조** (브랜드 메인 다크 카키 그린) |
| `--color-primary-700` | `#2B311E` | Pressed 상태 |
| `--color-primary-800` | `#1F2415` | 다크모드 표면 |
| `--color-primary-900` | `#15180D` | 다크모드 깊은 표면 |

### 2.2 Secondary — Paper (보조 표면 / 디바이더)

> 기본 배경은 **미세하게 따뜻한 오프화이트**(`#FAFAF8`). 순백(#FFFFFF)은 카드 표면에 사용해 배경과 살짝 분리. (이전 버전의 크림 베이스는 deprecated.)

| Token | Hex | 용도 |
|---|---|---|
| `--color-paper-50`  | `#FAFAF8` | **앱 기본 배경 (라이트) — warm off-white** |
| `--color-paper-100` | `#FFFFFF` | 카드 표면 (배경보다 한 톤 밝게) |
| `--color-paper-200` | `#F2F2EE` | 디바이더, 비활성 면 |
| `--color-paper-300` | `#E5E5DE` | 보더 |
| `--color-paper-400` | `#C7C7BD` | 비활성 텍스트 위 |

### 2.3 Accent — Sunrise (성취 / Gain / 스트릭)

> "No Pain, **Yes Gain**"의 Gain. 카드를 다 비웠을 때, 스트릭이 늘었을 때만 등장. 절제해서 써야 의미가 있음.

| Token | Hex | 용도 |
|---|---|---|
| `--color-accent-50`  | `#FDF4E8` |
| `--color-accent-100` | `#FBE6CB` |
| `--color-accent-300` | `#F2BE85` |
| `--color-accent-500` | `#E89B5C` | **성취 강조** (Cleared 카운트, streak badge) |
| `--color-accent-700` | `#B26F3A` |
| `--color-accent-900` | `#7A4920` |

### 2.4 Neutral — Ink (텍스트 / 보더)

| Token | Hex | 용도 |
|---|---|---|
| `--color-ink-900` | `#1A1D14` | 본문 텍스트 (제목) |
| `--color-ink-700` | `#3D4135` | 본문 텍스트 (기본) |
| `--color-ink-500` | `#71756A` | 보조 텍스트 |
| `--color-ink-400` | `#909488` | 메타데이터 (날짜 등) |
| `--color-ink-300` | `#B8BCB0` | 비활성 텍스트, 보더 강조 |
| `--color-ink-200` | `#D7DAD0` | 보더 |
| `--color-ink-100` | `#EAECE3` | 디바이더 |
| `--color-ink-50`  | `#F5F6F0` | 미묘한 표면 |

### 2.5 Semantic

| 의미 | Token | Hex | 메모 |
|---|---|---|---|
| Success | `--color-success` | `#4F5938` | Primary-500 재사용. 일관성. |
| Info    | `--color-info`    | `#5A7AA8` | 차분한 슬레이트 블루. |
| Warning | `--color-warning` | `#D89A3A` | Sunrise 계열에서 차용. |
| Error   | `--color-error`   | `#B65A4E` | **빨강이 아니라 테라코타.** Guilt-Free 원칙상 공격적 빨강 금지. |

### 2.6 Light vs Dark

| Role | Light | Dark |
|---|---|---|
| `--bg-app`       | `#FAFAF8` (paper-50)  | `#1A1D14` (ink-900) |
| `--bg-surface`   | `#FFFFFF` (paper-100) | `#222619` |
| `--bg-elevated`  | `#FFFFFF`             | `#2B2F22` |
| `--text-primary` | `#1A1D14` (ink-900)   | `#F5F6F0` (ink-50) |
| `--text-secondary` | `#71756A` (ink-500) | `#B8BCB0` (ink-300) |
| `--border`       | `#E5E5DE` (paper-300) | `#3D4135` (ink-700) |
| `--brand`        | `#3A4229` (primary-600) | `#929977` (primary-300) |

다크모드 원칙: **순흑(#000) 금지.** Primary-900 톤의 warm dark 사용. 본문 텍스트도 순백 금지 (ink-50).

---

## 3. Typography

### 3.1 폰트 선택

| 역할 | 폰트 | 근거 |
|---|---|---|
| Display (영문) | **Instrument Serif** (Google Fonts) | 잡지 헤드라인 톤. *Editorial* 형용사. 한 줄 카피의 무게감. |
| Body (영문) | **IBM Plex Sans** (Google Fonts) | 산세리프지만 따뜻함이 있음. Inter보다 캐릭터 있음. |
| Body (한글) | **Pretendard** (free, [pretendard.cdn-fonts.com](https://cdn.jsdelivr.net/gh/orioncactus/pretendard/dist/web/static/pretendard.css)) | 한국어 UI의 사실상 표준. 시스템 한글과 자연스럽게 호환. |
| Mono | **JetBrains Mono** (Google Fonts) | 메타데이터, 날짜, 라벨. 현재 프로토타입의 SEARCH/TODAY'S READING FLOW 같은 라벨에서 이미 사용 중인 톤 계승. |

폰트 스택 (CSS):
```css
--font-display: "Instrument Serif", "Pretendard", ui-serif, Georgia, serif;
--font-sans:    "IBM Plex Sans", "Pretendard", -apple-system, BlinkMacSystemFont, sans-serif;
--font-mono:    "JetBrains Mono", ui-monospace, SFMono-Regular, Menlo, monospace;
```

### 3.2 Type scale (모바일 기준; 데스크탑은 +2~4px 가능)

| Token | Size / Line / Weight | 폰트 | 용도 |
|---|---|---|---|
| `--text-display` | 40 / 44 / 400 | Serif | Onboarding 헤드라인, "Cleared!" 같은 성취 화면 |
| `--text-h1`      | 28 / 34 / 500 | Serif | 페이지 제목 ("Library", "Archive") |
| `--text-h2`      | 22 / 28 / 600 | Sans  | 카드 제목 |
| `--text-h3`      | 18 / 24 / 600 | Sans  | 섹션 헤더 |
| `--text-h4`      | 16 / 22 / 600 | Sans  | 인라인 강조 |
| `--text-body`    | 15 / 22 / 400 | Sans  | 본문 |
| `--text-body-sm` | 13 / 20 / 400 | Sans  | 카드 요약 본문 |
| `--text-label`   | 12 / 16 / 500 | Sans  | 버튼, 칩 |
| `--text-meta`    | 11 / 14 / 400 / +0.08em letterspacing / **uppercase** | **Mono** | "TODAY'S READING FLOW", 날짜, 출처 |
| `--text-caption` | 11 / 14 / 400 | Sans  | 설명 |

### 3.3 "Radical Brevity"의 타이포그래픽 표현

- **하나의 카드에 H2 하나, 본문 3줄 max.** AI 요약은 항상 3줄, 각 줄 최대 60자.
- **여백 > 글자.** 카드 내부 padding은 글자 영역보다 크게. (`24px` padding > 본문 행간)
- **세리프는 한 줄, 짧게.** Display/H1는 한 번에 한 메시지. 두 줄 넘어가면 문구를 줄여라.
- **번호 매겨진 리스트 금지** — 요약은 글머리표(•) 3줄로 통일. 순서가 없는 정보라는 신호.
- **말줄임표(…) 미사용.** 잘리면 잘렸다고 말하지 말고 그냥 잘라라. "더보기" CTA로 처리.

ASCII 예시:
```
┌──────────────────────────────────┐
│ HACKER NEWS · APR 29              │ ← Mono meta, uppercase
│                                   │
│ The Python Tutorial               │ ← H2 Sans 600
│                                   │
│ • Easy-to-learn syntax            │ ← 3-line bullets, Sans 400
│ • Efficient high-level structures │
│ • Object-oriented approach        │
│                                   │
└──────────────────────────────────┘
```

---

## 4. Spacing, Radius, Elevation

### 4.1 Spacing scale — 4px 베이스

| Token | px | 용도 |
|---|---|---|
| `--space-0` | 0  | — |
| `--space-1` | 4  | 아이콘-텍스트 간격 |
| `--space-2` | 8  | 칩 내부, tight grouping |
| `--space-3` | 12 | 버튼 vertical padding |
| `--space-4` | 16 | **카드 본문 내부 기본** |
| `--space-5` | 20 | 카드 내 섹션 간격 |
| `--space-6` | 24 | **카드 외곽 padding, 화면 좌우 margin (모바일)** |
| `--space-8` | 32 | 섹션 간격 |
| `--space-10` | 40 | 큰 섹션 간격 |
| `--space-12` | 48 | 화면 상하 여백 |
| `--space-16` | 64 | Hero/empty-state 여백 |

### 4.2 Border radius

| Token | px | 용도 |
|---|---|---|
| `--radius-xs` | 4  | 칩, 작은 인풋 |
| `--radius-sm` | 8  | 버튼, 인풋 |
| `--radius-md` | 12 | 작은 카드, 모달 보더 |
| `--radius-lg` | 16 | 메인 카드 |
| `--radius-xl` | 24 | 시트 상단 (bottom sheet) |
| `--radius-full` | 9999 | 아바타, 토글, "더보기" pill |

### 4.3 Elevation (shadow) — 카드 스택용 핵심

> 빛은 위에서 약간 앞으로. 그림자는 따뜻한 톤. 순흑 그림자 금지 (rgba(26, 29, 20, ...)).

| Token | 값 | 용도 |
|---|---|---|
| `--shadow-0` | none | flat |
| `--shadow-1` | `0 1px 2px rgba(26,29,20,0.04), 0 1px 1px rgba(26,29,20,0.03)` | 인풋, 작은 칩 |
| `--shadow-2` | `0 2px 6px rgba(26,29,20,0.06), 0 1px 2px rgba(26,29,20,0.04)` | **카드 기본** |
| `--shadow-3` | `0 8px 20px rgba(26,29,20,0.08), 0 2px 6px rgba(26,29,20,0.05)` | 드래그/포커스 상태 카드 |
| `--shadow-4` | `0 20px 40px rgba(26,29,20,0.12)` | Bottom sheet, 모달 |

---

## 5. Iconography & Imagery

### 5.1 아이콘

- **Library: [Lucide](https://lucide.dev) (open source, free).** 라인 스타일, 1.5px stroke, 24px viewbox.
- 사이즈 토큰: `--icon-sm: 16px`, `--icon-md: 20px`, `--icon-lg: 24px`, `--icon-xl: 32px`.
- 색: 기본 `--text-secondary` (#71756A), 활성 `--brand`, 비활성 `--color-ink-300`.
- **이모지 사용 금지** (Brevity + 톤). 단 예외: 알림 카피에서 의도적으로 1개까지 (예: "오늘 클리어 ✓" 같은 단순 체크).
- 절대 SVG로 일러스트를 그리지 않는다. 필요하면 플레이스홀더만.

#### 5.1.1 Cross-platform 일관성 (Web ↔ iOS)

> **원칙: 같은 의미 = 같은 그림.** Web과 iOS에서 동일한 메뉴/액션은 반드시 시각적으로 동일한 아이콘을 사용한다. 한 쪽에만 아이콘이 있고 다른 쪽이 다른 그림이면 안 된다.

**1차 소스 = Lucide.** Web은 Lucide SVG를 그대로 사용. iOS는 다음 두 가지 중 하나로 처리:

| 옵션 | 방법 | 권장 상황 |
|---|---|---|
| **A. Lucide SVG를 Asset Catalog에 직접 등록** | `Image("nav-library")` → `nav-library.svg` (Single Scale, Preserve Vector Data ON). Lucide 24×24를 그대로 import. | **기본 권장.** 픽셀까지 동일. |
| **B. SF Symbols 매핑** | 의미가 동일한 SF Symbol로 치환. Lucide와 시각이 유사한 것만 허용. | Lucide에 없는 시스템 액션 (공유 시트, 백 버튼 등). |

**핵심 메뉴/액션 아이콘 매핑 (Single Source of Truth)**

| 의미 | Lucide (Web) | iOS Asset 이름 | SF Symbol 대체 (Fallback) |
|---|---|---|---|
| Dashboard | `layout-grid` | `nav-dashboard` | `square.grid.2x2` |
| Library (Inbox) | `inbox` | `nav-library` | `tray` |
| Archive | `archive` | `nav-archive` | `archivebox` |
| Trash | `trash-2` | `nav-trash` | `trash` |
| Analytics | `trending-up` | `nav-analytics` | `chart.line.uptrend.xyaxis` |
| Settings | `settings` | `nav-settings` | `gearshape` |
| You / Profile | `circle-user` | `nav-you` | `person.crop.circle` |
| Search | `search` | `ui-search` | `magnifyingglass` |
| Share / Save to Briefly | `share` | `ui-share` | `square.and.arrow.up` |
| Expand summary | `chevron-right` | `ui-chevron-right` | `chevron.right` |
| Copy link | `link` | `ui-link` | `link` |
| Undo | `rotate-ccw` | `ui-undo` | `arrow.uturn.backward` |

**규칙**
- 새 메뉴/액션을 추가할 때는 **이 표에 한 행을 먼저 추가**한 뒤 web/iOS 양쪽에 동시에 반영. 한쪽만 먼저 만드는 것 금지.
- **iOS에서 SF Symbol을 쓰더라도 의미는 같아야 한다.** 예: Web에서 `archive`(상자 모양)를 쓰면서 iOS에서 `square.and.arrow.down`(다운로드 모양)을 쓰면 안 됨.
- **stroke weight 통일:** Lucide 1.5px stroke. SF Symbol은 `.weight(.regular)` 사용 (절대 `.thin` 또는 `.bold` 금지).
- **사이즈 토큰 동기화:** Web의 `--icon-md: 20px` ↔ iOS `IconSize.md = 20pt`. (Phase 2 §9.4 참조.)
- **다국어 안전:** 한글 라벨이 1~2자(예: "나")로 짧아질 때도 아이콘이 있으면 hit-target과 스캔 가능성이 확보됨. → 데스크탑 사이드바에도 아이콘 유지를 권장.

### 5.2 로고 시스템 (UX-008)

공식 로고 에셋 두 종류를 상황에 따라 사용. 색상은 배경에 따라 전환.

**에셋 위치**
- `images/logo_full.svg` — 가로형 워드마크 "Briefly" (viewBox 1530×546)
- `images/logo_short.png` — B 레터마크 PNG (600×600), 브라우저 확장 전용
- `images/logo_ios.png` — iOS 앱 아이콘용 PNG (1024×1024)

**사용 기준**

| 맥락 | 로고 종류 | 배경 | 로고 색 |
|---|---|---|---|
| 웹 로그인 페이지 | `LogoFull` (워드마크) | 카키 `#3A4229` | 흰색 |
| 웹 사이드바 / 회원가입 / 파비콘 / 확장 | `LogoShort` (B 레터마크) | 카키 `#3A4229` | 흰색 |
| **iOS 스플래시 / 밝은 배경** | `LogoFull` (워드마크) | 라이트 `#FAFAF8` | 카키 `--color-primary-600` |

**색상 전환 규칙**
- 카키 배경(`#3A4229`) 위: `color: #FFFFFF` → 흰색 로고
- 밝은 배경(투명/화이트) 위: `color: var(--color-primary-600)` → 카키 로고
- Web: `fill="currentColor"` + 부모 CSS `color` 속성으로 제어
- iOS: `.renderingMode(.template)` + `.foregroundStyle(Color.brieflyPrimary600)`

**iOS 구현 (Asset Catalog)**
- `Assets.xcassets/logo_full.imageset` — `preserves-vector-representation: true`, `template-rendering-intent: template`
- 사용: `Image("logo_full").renderingMode(.template).foregroundStyle(Color.brieflyPrimary600)`

### 5.3 썸네일 이미지 처리

세 가지 케이스, 항상 16:9 비율, `--radius-md`:

**A. 원본 이미지 있음**  
원본을 그대로. `object-fit: cover`. 좌상단에 출처 favicon (16px, mono 톤).

**B. 텍스트만 (원본 이미지 없음) — AI가 카드뉴스 생성**  
요약 첫 문장을 큰 세리프 텍스트로 (Display 32px), 배경은 `--color-paper-200` ~ `--color-paper-300` 그라데이션, 출처 favicon은 우상단.

**C. 둘 다 없음 / 로딩**  
줄무늬 SVG placeholder + mono 캡션 `"NO PREVIEW"`. **현재 프로토타입의 "B" 로고 박스는 deprecated** — 추상 줄무늬로 교체.

```
A. ┌─────────────────────┐   B. ┌─────────────────────┐   C. ┌─────────────────────┐
   │ [원본 이미지]        │     │ "Python is easy to   │     │ ░░░░░░░░░░░░░░░░░░░ │
   │                     │     │  learn but powerful" │     │ ░░░░░░ NO PREVIEW ░ │
   │              [icon] │     │              [icon]  │     │ ░░░░░░░░░░░░░░░░░░░ │
   └─────────────────────┘     └─────────────────────┘     └─────────────────────┘
```

---

## 6. Core Components

> 모든 컴포넌트 상태: `default → hover → pressed → focus → disabled` 순.
> 모바일에서 hover는 보통 생략하고 pressed만 의미 있음.

### 6.1 Button

Anatomy: `[ icon? ][ label ][ icon? ]`, height `40px` (md) / `48px` (lg) / `32px` (sm), horizontal padding `--space-4`, `--radius-sm`.

| Variant | default bg | default text | pressed | disabled |
|---|---|---|---|---|
| **Primary** | `--color-primary-500` `#4F5938` | `#FFFFFF` | `--color-primary-700` `#2B311E` | bg `--color-ink-200`, text `--color-ink-400` |
| **Secondary** | transparent, 보더 `--border` 1px | `--text-primary` | bg `--color-paper-200` | 보더 `--color-ink-200`, text `--color-ink-400` |
| **Ghost** | transparent | `--brand` | bg `--color-primary-50` | text `--color-ink-400` |
| **Danger** (드물게) | transparent, 보더 `--color-error` | `--color-error` | bg `--color-error` 10% tint | — |

Focus ring: `0 0 0 3px rgba(79,89,56,0.25)` (primary-500 @ 25%).

### 6.2 Card (일반)

```
┌─────────────────────────────────┐  ← --radius-lg (16), --shadow-2
│ padding: --space-6 (24)         │
│ ┌─ header: source chip + status chip ─┐
│ ┌─ thumbnail (16:9, --radius-md) ─┐   │
│ ┌─ title (--text-h2) ─┐               │
│ ┌─ body (--text-body-sm, max 3 lines)─┐
│ ┌─ footer: meta (mono) + actions ──┐  │
└─────────────────────────────────┘
```

배경 `--bg-surface`, 보더 없음 (그림자만). Hover에서 살짝 위로 (`translateY(-2px)`, transition 160ms).

### 6.3 Tab Bar (모바일 — Inbox / Archive / My Page)

높이 `64px` + safe-area-inset-bottom, 배경 `--bg-surface`, 상단 보더 `--border` 0.5px.
3 균등 분할, 각 탭: 아이콘 (`--icon-md` 20px) 위 + 라벨 (`--text-caption` 11px) 아래, 간격 `--space-1`.

| State | Icon | Label |
|---|---|---|
| Inactive | `--color-ink-400` | `--color-ink-400` |
| Active   | `--brand` (`--color-primary-600`, `#3A4229`) | `--brand`, weight 600 |
| Pressed  | scale 0.94, 120ms |  |

탭 3개:
- **Inbox** (Lucide `inbox`) — 미소화 카드
- **Archive** (Lucide `archive`) — 처리 완료된 카드 보관
- **You** (Lucide `circle-user`) — Analytics, Settings, Streak

### 6.4 Input

높이 `44px` (모바일 hit-target), padding `0 --space-4`, `--radius-sm`, 보더 `--border` 1px, 폰트 `--text-body`, 배경 `--bg-surface`.

| State | Border | Background |
|---|---|---|
| default | `--border` | `--bg-surface` |
| focus | `--brand` 1.5px + focus ring | `--bg-surface` |
| error | `--color-error` | `--color-error` 4% tint |
| disabled | `--color-ink-200` | `--color-paper-200` |

Placeholder: `--color-ink-400`.

### 6.5 Tag / Chip

높이 `24px`, padding `0 --space-2`, `--radius-full`, 폰트 `--text-meta` (Mono 11/14).

| Variant | bg | text | border |
|---|---|---|---|
| Source (Hacker News, Docs…) | `--color-paper-200` | `--text-secondary` | `--border` |
| Status: inbox | `--color-ink-100` | `--text-secondary` | none |
| Status: kept | `--color-primary-100` | `--color-primary-700` | none |
| Status: archived | `--color-ink-100` | `--color-ink-700` | none |
| Tag (사용자) | `--color-accent-50` | `--color-accent-700` | none |

### 6.6 Empty State (Guilt-Free 핵심)

빈 인박스를 만났을 때:
- **죄책감 0, 응원 100.** "할 일이 쌓였습니다" 금지.
- 중앙 정렬, 상단 80px 떨어진 위치.
- 1. 추상 아이콘 (line, 48px, `--color-ink-300`)
- 2. Display 제목 (Serif): `"오늘 클리어!"` / `"All caught up."`
- 3. 본문 (`--text-body`, `--text-secondary`): 응원 한 줄.
- 4. (선택) Ghost 버튼: `"Library 둘러보기"`

```
                   ╭───╮
                   │ ✓ │       ← 라인 아이콘
                   ╰───╯
                  
              오늘 클리어!         ← Serif Display
       
   새 카드가 도착하면 알려드릴게요.  ← --text-body, secondary
              
            [ Library 둘러보기 ]    ← Ghost 버튼
```

---

## 7. Motion & Interaction

원칙: **빠르게, 그러나 부드럽게.** Radical Brevity = 동작도 짧게.

### 7.1 Duration tokens

| Token | ms | 용도 |
|---|---|---|
| `--motion-instant` | 80   | 색상 변경, focus ring |
| `--motion-fast`    | 160  | hover, 작은 transform |
| `--motion-base`    | 240  | **카드 전환 기본** |
| `--motion-slow`    | 320  | 카드 퇴장 / 큰 transform |
| `--motion-page`    | 400  | 페이지 / 시트 전환 |

### 7.2 Easing tokens

| Token | value | 용도 |
|---|---|---|
| `--ease-out`    | `cubic-bezier(0.2, 0.8, 0.2, 1)` | 등장 (대부분의 경우 기본값) |
| `--ease-in`     | `cubic-bezier(0.4, 0, 1, 1)` | 사라짐 |
| `--ease-in-out` | `cubic-bezier(0.4, 0, 0.2, 1)` | 양방향 전환 |
| `--ease-spring` | `cubic-bezier(0.34, 1.56, 0.64, 1)` | 복귀 / overshoot 필요한 곳 |

### 7.3 마이크로 인터랙션 원칙

1. **모든 상태 변화는 transition이 있다.** (단 instant 토큰 사용 가능)
2. **scale은 0.94 미만으로 내려가지 않는다.** (찌그러진 느낌 방지)
3. **opacity로 등장/퇴장할 때 반드시 translateY 4~8px 동반.** 평면 fade 금지.
4. **튀는 spring은 카드 복귀에만.** 일반 transition에서 overshoot 금지.

---

## 8. Layout

### 8.1 모바일 (Primary target)

- 디자인 기준 너비: **390px** (iPhone 14/15/16). 375px (iPhone SE/mini)에서 깨지지 않게 검증.
- 좌우 화면 padding: `--space-6` (24px). 단 카드 그리드는 가장자리까지 가능 (full-bleed 칩).
- **Safe area:**  
  - top: `env(safe-area-inset-top)` + 8px  
  - bottom: `env(safe-area-inset-bottom)` + tab-bar 64px
- 최대 컨텐츠 너비 (큰 폰): `420px` 중앙 정렬.

### 8.2 데스크탑/웹 (현 프로토타입)

- 컨텐츠 max-width: `1200px`, 중앙 정렬.
- 사이드바: 고정 너비 `240px`. (현재 프로토타입의 사이드바 유지)
- 카드 그리드: `repeat(auto-fill, minmax(320px, 1fr))`, gap `--space-6`.

### 8.3 Grid

4 컬럼 모바일, 12 컬럼 데스크탑. Gutter = `--space-4` (16px).

---

## 9. Implementation Notes for Claude Code

### 9.1 CSS variable 네이밍 컨벤션

```
--color-<role>-<scale>     예: --color-primary-500
--color-<semantic>         예: --color-success
--bg-<surface>             예: --bg-app, --bg-surface, --bg-elevated
--text-<role>              예: --text-primary, --text-secondary
--border                   (단수 — 단일 의미)
--brand                    (단수 — 단일 의미, 현재 테마의 강조색)
--space-<n>                4 곱하기 n (n은 0,1,2,3,4,5,6,8,10,12,16)
--radius-<size>            xs / sm / md / lg / xl / full
--shadow-<n>               0..4
--text-<role>              display / h1..h4 / body / body-sm / label / meta / caption
--motion-<speed>           instant / fast / base / slow / page
--ease-<curve>             out / in / in-out / spring
--font-<family>            display / sans / mono
--icon-<size>              sm / md / lg / xl
```

### 9.2 Tailwind config (필요 시)

```js
// tailwind.config.js
module.exports = {
  theme: {
    extend: {
      colors: {
        primary: {
          50: "#F0F2EA", 100: "#DDE0CE", 200: "#B8BFA1", 300: "#929977",
          400: "#6E7654", 500: "#4F5938", 600: "#3A4229", 700: "#2B311E",
          800: "#1F2415", 900: "#15180D",
        },
        paper: {
          50: "#FAFAF8", 100: "#FFFFFF", 200: "#F2F2EE",
          300: "#E5E5DE", 400: "#C7C7BD",
        },
        accent: {
          50: "#FDF4E8", 100: "#FBE6CB", 300: "#F2BE85",
          500: "#E89B5C", 700: "#B26F3A", 900: "#7A4920",
        },
        ink: {
          50: "#F5F6F0", 100: "#EAECE3", 200: "#D7DAD0", 300: "#B8BCB0",
          400: "#909488", 500: "#71756A", 700: "#3D4135", 900: "#1A1D14",
        },
        success: "#4F5938", info: "#5A7AA8",
        warning: "#D89A3A", error: "#B65A4E",
      },
      fontFamily: {
        display: ['"Instrument Serif"', '"Pretendard"', "serif"],
        sans: ['"IBM Plex Sans"', '"Pretendard"', "system-ui", "sans-serif"],
        mono: ['"JetBrains Mono"', "ui-monospace", "monospace"],
      },
      borderRadius: { xs: "4px", sm: "8px", md: "12px", lg: "16px", xl: "24px" },
      boxShadow: {
        1: "0 1px 2px rgba(26,29,20,0.04), 0 1px 1px rgba(26,29,20,0.03)",
        2: "0 2px 6px rgba(26,29,20,0.06), 0 1px 2px rgba(26,29,20,0.04)",
        3: "0 8px 20px rgba(26,29,20,0.08), 0 2px 6px rgba(26,29,20,0.05)",
        4: "0 20px 40px rgba(26,29,20,0.12)",
      },
      transitionTimingFunction: {
        "out-soft": "cubic-bezier(0.2, 0.8, 0.2, 1)",
        spring: "cubic-bezier(0.34, 1.56, 0.64, 1)",
      },
      transitionDuration: { instant: "80ms", fast: "160ms", base: "240ms", slow: "320ms", page: "400ms" },
    },
  },
};
```

### 9.3 토큰 import 패턴

권장 구조:
```
/styles
  tokens.css       ← :root { --color-... } 정의만. 다른 곳에서 import.
  base.css         ← reset + font-face + body 기본
  components.css   ← .btn, .card 등
```

```css
/* tokens.css */
:root {
  --color-primary-500: #4F5938;
  --color-primary-600: #3A4229;
  /* ... 위 표 그대로 ... */
  --bg-app: var(--color-paper-50);    /* #FAFAF8 — warm off-white */
  --bg-surface: var(--color-paper-100); /* #FFFFFF — cards */
  --text-primary: var(--color-ink-900);
  --brand: var(--color-primary-600);
}

:root[data-theme="dark"] {
  --bg-app: var(--color-ink-900);
  --bg-surface: #222619;
  --text-primary: var(--color-ink-50);
  --brand: var(--color-primary-300);
}
```

JS에서 토큰 접근 (애니메이션, 캔버스 등):
```js
const brand = getComputedStyle(document.documentElement)
  .getPropertyValue("--brand").trim();
```

### 9.4 iOS Swift로 옮길 때 (Phase 2)

- 동일한 토큰 이름을 그대로 `Color+Briefly.swift` / `Spacing+Briefly.swift` enum으로 옮길 것.
- 예: `Color.primary500 = Color(hex: 0x4F5938)`, `Spacing.s6 = 24`.
- 다크모드는 `Color(light: ..., dark: ...)` 어셋으로 일괄 등록.
- 폰트: Instrument Serif / IBM Plex Sans / Pretendard / JetBrains Mono 모두 OFL 라이선스 — `.ttf`를 Info.plist `UIAppFonts`에 등록.

---

## Appendix — 디자인 토큰 요약 (한눈에)

```
COLOR        PRIMARY  #4F5938 (500)   #3A4229 (600)  ← Dark Olive Forest
             PAPER    #FAFAF8 (bg)    #FFFFFF (card)  ← Warm off-white base
             ACCENT   #E89B5C
             INK      #1A1D14  #71756A  #B8BCB0
SPACE        4 / 8 / 12 / 16 / 20 / 24 / 32 / 40 / 48 / 64
RADIUS       4 / 8 / 12 / 16 / 24 / full
SHADOW       1: card subtle   2: card  3: card-drag  4: modal
TYPE         Serif: Instrument Serif   Sans: IBM Plex / Pretendard   Mono: JetBrains
MOTION       80 / 160 / 240 / 320 / 400 ms
```

> *— Briefly is a place to consume, not to collect.*
