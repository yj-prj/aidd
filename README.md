# 🤖 AI 개발도구 트렌드 Slack 봇 v5

매일 오전 9시 / 오후 6시 KST, 해외·국내 6개 소스에서 AI 개발도구 트렌드를 수집하고
Gemini가 필터링·번역·분석을 **단 1회 호출**로 처리해 Slack으로 발송합니다.

---

## 전체 흐름

```
1. 수집       해외 3 + 국내 3, 총 6개 소스에서 뉴스 가져오기
      ↓
2. Gemini     필터링 + 번역 + 분석을 단 1번 호출로 처리
      ↓
3. Slack      분석 → 개별 뉴스 + 링크 → 한 줄 요약 순서로 발송
```

---

## 수집 소스

### 해외 3곳 (영문 → 한국어 자동 번역)

| 소스 | 수집 방식 | 쿼터 |
|------|-----------|------|
| 🟠 Hacker News | Firebase REST API — 상위 200개 중 점수 20점 이상 | 최대 3개 |
| 🔴 Product Hunt | GraphQL API (토큰 있을 때) / RSS 자동 전환 — 오늘 상위 30개 | 최대 3개 |
| ⚫ GitHub Trending | gitterapp API → 실패 시 스크래핑 자동 전환 | 최대 3개 |

### 국내 3곳 (번역 없이 원문 그대로)

| 소스 | 수집 방식 | 쿼터 |
|------|-----------|------|
| 🟢 GeekNews (긱뉴스) | Atom RSS — 최신 50개 | 최대 2개 |
| 🟡 Velog 트렌딩 | RSS — 트렌딩 상위 40개 | 최대 2개 |
| 🟣 요즘IT | RSS — 최신 30개 | 최대 2개 |

---

## 수집 기준 — 키워드 2단계

### 🔧 TIER 1 — AI 개발도구 / 바이브코딩 / AI Assistant / AIDD (우선 수집)

| 분류 | 키워드 |
|------|--------|
| 바이브코딩 / AI 코드 에디터 | cursor, copilot, lovable, bolt, v0, windsurf, codeium, aider, devin, cline, supermaven, vibe coding |
| AI 개발도구 일반 | ai coding, ai ide, ai editor, coding assistant, code generation, code completion, ai pair programmer |
| AI assistant / agent | ai assistant, coding agent, mcp server, mcp tool, agentic development |
| AI-Driven Development | ai code review, ai pull request, ai dev workflow, aidd |

### 🌐 TIER 2 — AI 전반 (TIER1 부족 시 보충)

| 분류 | 키워드 |
|------|--------|
| AI 회사 / 모델 | openai, anthropic, google ai, gpt, claude, gemini, llama, deepseek |
| 기술 | llm, generative ai, rag, fine-tuning, prompt engineering |
| 비즈니스 | ai startup, ai product, ai platform, ai automation |

### 소스별 쿼터 보장

키워드에 아무것도 안 걸려도 각 소스에서 최소 1개는 나오도록 fallback이 작동합니다.

```
1순위: TIER1 매칭 글
2순위: TIER2 매칭 글
3순위: 위 둘 다 없으면 해당 소스 인기글 1개 (점수/스타 순)
```

---

## Gemini 처리 — 단 1회 호출

기존 3번 호출(필터링 → 번역 → 분석)을 `gemini_process()` 함수 하나로 통합해
**실행당 Gemini 1회만 호출**합니다. (하루 2회 실행 기준 총 2번)

### 한 번에 처리하는 3가지 작업

**① 필터링**
수집된 뉴스 중 AI 개발도구 관점에서 읽을 가치가 있는 소식만 추려냅니다.

통과 기준 — 하나라도 해당되면 통과:
- AI IDE / 코드 에디터 (Cursor, Copilot, Windsurf, Lovable, Bolt 등)
- Vibe coding / AI-Driven Development
- AI coding assistant / coding agent
- MCP (Model Context Protocol)
- 새로운 AI 개발도구 출시 또는 주요 업데이트
- 개발자 워크플로우를 바꾸는 AI 툴·기능

제외 기준 — 해당되면 제외:
- 단순 모델 벤치마크·성능 비교
- AI 규제·정책·윤리
- AI 투자·인수합병 (툴과 무관한 것)
- 학술 논문·연구

**② 번역 + 요약**
필터링 통과한 해외 소스(HN, Product Hunt, GitHub)를 한국어로 번역합니다.
- 제목: 자연스러운 한국어 (툴 이름·고유명사는 영문 유지)
- 요약: 20자 이내, 어떤 툴인지 / 왜 화제인지
- 국내 소스는 번역 없이 그대로

**③ 분석**
통과된 뉴스 전체를 바탕으로 AI 개발도구 관점 인사이트를 생성합니다.
분석 범위: Vibe coding / AIDD 흐름, AI IDE 경쟁 구도, coding agent 동향, MCP 생태계, 신규 툴

---

## Slack 메시지 구조

```
🤖 AI 개발도구 트렌드  🌅 오전 브리핑
📅 2026년 03월 10일  09:00 KST  |  총 11개  🔧 개발도구 8개  🌐 AI전반 3개
──────────────────────────────────────────
🧠 오늘의 AI 개발도구 트렌드 분석

📌 오늘의 핵심 트렌드
Cursor의 에이전트 모드 출시를 기점으로 AI 코드 에디터들이 자율 실행
방향으로 빠르게 이동하고 있습니다...

🔥 주목할 움직임
MCP 생태계 관련 레포가 GitHub Trending 상위권을 장악...

💡 개발자가 챙겨볼 것
Windsurf의 오프라인 모드 지원으로 보안 환경에서도...
──────────────────────────────────────────
🟠 [Hacker News]  `🔧 개발도구`
*Cursor, 새 에이전트 모드 출시*
› 자율 코딩 에이전트
_Cursor launches agent mode with autonomous code execution_
⬆️ 847점  💬 234댓글
🔗 원문 보기  ›  💬 토론 보기
──────────────────────────────────────────
🔴 [Product Hunt]  `🔧 개발도구`
...
🟠 🔴 ⚫ 🟢 🟡 🟣 (6개 소스 순서대로)
──────────────────────────────────────────
🗞️ 오늘의 트렌딩 한 줄 요약
AI 코드 에디터가 단순 완성을 넘어 자율 에이전트로 진화하는 한 주.
──────────────────────────────────────────
📡 해외: HN · ProductHunt · GitHub  국내: GeekNews · Velog · 요즘IT
🤖 필터링·분석·번역: Gemini 2.0 Flash
```

---

## 비용

| 항목 | 비용 |
|------|------|
| GitHub Actions | 무료 (월 2,000분 제공 / 이 봇 월 ~60분 사용) |
| 모든 소스 API / RSS | 무료 |
| Gemini 2.0 Flash | 무료 — 하루 1,500 요청 제공 / 이 봇 하루 **2회** 호출 (1회 실행 = 1번 호출) |
| **합계** | **$0 / 월** |

---

## 파일 구조

```
ai-trend-bot/
├── main.py
└── .github/
    └── workflows/
        ├── daily-bot.yml      # 자동 실행 (매일 9시 / 18시 KST)
        └── manual-run.yml     # 수동 실행
```
