# 🤖 AI 트렌드 Slack 봇 v4

매일 오전 9시 / 오후 6시 KST, 6개 소스에서 AI 트렌드를 수집해 Slack으로 발송합니다.

---

## 🗂️ 수집 기준 — 키워드 2단계

모든 소스에 동일한 2단계 키워드를 적용합니다.  
**TIER1을 우선 채우고**, 부족하면 TIER2로 보충합니다.

### 🔧 TIER1 — AI 개발도구 / 바이브코딩 / AI Assistant / AIDD

| 분류 | 키워드 |
|------|--------|
| 바이브코딩 / AI 코드 에디터 | cursor, copilot, lovable, bolt, v0, windsurf, codeium, aider, devin, cline, supermaven, vibe coding |
| AI 개발도구 일반 | ai coding, ai ide, ai editor, coding assistant, code generation, code completion, ai pair programmer |
| AI assistant / agent | ai assistant, coding agent, mcp server, mcp tool, agentic development |
| AI-Driven Development | ai code review, ai pull request, ai dev workflow, aidd |

### 🌐 TIER2 — AI 전반

| 분류 | 키워드 |
|------|--------|
| AI 생태계 / 회사 | openai, anthropic, google ai, mistral, meta ai |
| 모델 | gpt, claude, gemini, llama, deepseek, qwen |
| 기술 | llm, generative ai, rag, fine-tuning, prompt engineering, inference |
| 비즈니스 | ai startup, ai product, ai platform, ai automation, ai productivity |

---

## 📡 소스별 수집 방식

### 🟠 Hacker News
- **API**: Firebase REST API (공식, 무료, 인증 불필요)
- **수집 대상**: 상위 200개 스토리 중 키워드 매칭 + 점수 20점 이상
- **정렬**: 점수 높은 순
- **쿼터**: 최대 3개 (TIER1 우선)
- **제공 정보**: 제목, 원문 링크, HN 토론 링크, 점수, 댓글 수

### 🔴 Product Hunt
- **API**: GraphQL API (토큰 있을 때) / RSS (토큰 없을 때 자동 전환)
- **수집 대상**: 오늘 투표 상위 30개 중 키워드 매칭
- **쿼터**: 최대 3개 (TIER1 우선)
- **제공 정보**: 툴 이름, 한 줄 소개, 투표 수, 댓글 수, 링크
- **특이사항**: 신규 툴 런칭 감지에 특화. 토큰 없어도 RSS로 동작

### ⚫ GitHub Trending
- **API**: gitterapp 비공식 API → 실패 시 github.com/trending 스크래핑으로 자동 전환
- **수집 대상**: 오늘 트렌딩 전체 레포 중 키워드 매칭
- **쿼터**: 최대 3개 (TIER1 우선)
- **제공 정보**: 레포명, 설명, 누적 스타 수, 오늘 획득 스타 수, 링크
- **특이사항**: 키워드 미매칭 시 트렌딩 상위 레포를 fallback으로 1개 포함

### 🟢 GeekNews (긱뉴스)
- **API**: Atom RSS (공식, 무료)
- **수집 대상**: 최신 50개 글 중 키워드 매칭
- **쿼터**: 최대 2개 (TIER1 우선)
- **특징**: 한국 개발자들이 직접 큐레이션하는 HN 스타일 커뮤니티. 해외 AI 툴 소식이 한국어로 가장 먼저 정리됨

### 🟡 Velog 트렌딩
- **API**: RSS (공식, 무료)
- **수집 대상**: 트렌딩 상위 40개 포스트 중 키워드 매칭
- **쿼터**: 최대 2개 (TIER1 우선)
- **특징**: 국내 개발자 실사용 후기, 튜토리얼, 비교 글 위주

### 🟣 요즘IT
- **API**: RSS (공식, 무료)
- **수집 대상**: 최신 30개 아티클 중 키워드 매칭
- **쿼터**: 최대 2개 (TIER1 우선)
- **특징**: 국내 IT 미디어. 툴 소개·비교·트렌드 분석 아티클

---

## 🔄 쿼터 보장 로직

키워드에 아무것도 안 걸려도 각 소스에서 반드시 1개는 나오도록 fallback이 작동합니다.

```
1순위: TIER1 키워드 매칭 글
2순위: TIER2 키워드 매칭 글
3순위: 매칭 없으면 해당 소스 인기글 1개 (점수/스타 순)
```

→ 항상 6개 소스가 골고루 등장합니다.

---

## 🤖 번역 / 요약

- **엔진**: Google Gemini 2.0 Flash
- **대상**: 해외 3개 소스 (HN, Product Hunt, GitHub) — 국내 소스는 그대로 출력
- **출력**: 한국어 제목 + 20자 이내 핵심 요약
- **규칙**: 툴 이름·고유명사는 영문 유지, 원문 제목도 함께 표시

---

## 📊 Slack 메시지 구성

```
🤖 AI 트렌드  🌅 오전 브리핑
📅 2026년 03월 10일  09:00 KST  |  총 13개  🔧 개발도구 9개  🌐 AI전반 4개

🟠 [Hacker News]  `🔧 개발도구`
Cursor, Claude Sonnet 통합으로 완성도 40% 향상
› 주요 업데이트
_Cursor integrates Claude Sonnet for 40% better completions_
⬆️ 847점  💬 234댓글
🔗 원문 보기  ›  💬 토론 보기
```

각 항목에 포함되는 정보:
- 출처 + 분류 배지 (`🔧 개발도구` / `🌐 AI 전반`)
- 한국어 번역 제목 + 한 줄 요약
- 영문 원제 (해외 소스)
- 점수 / 스타 / 투표 수
- 원문 링크 + 토론 링크 (별도 존재하는 경우)

---

## 💰 비용

| 항목 | 비용 |
|------|------|
| GitHub Actions | 무료 (월 2,000분 제공 / 이 봇 월 ~60분 사용) |
| 모든 소스 API / RSS | 무료 |
| Gemini 2.0 Flash | 무료 (하루 1,500 요청 제공 / 이 봇 하루 2회 사용) |
| **합계** | **$0 / 월** |
