# 🤖 AI 개발도구 트렌드 Slack 봇 v2

전 세계 + 국내 개발자 커뮤니티에서 AI 바이브코딩 툴 트렌드를 수집해  
**매일 오전 9시 / 오후 6시 KST** 에 Slack으로 자동 발송합니다.

---

## 📡 수집 소스 7곳

### 해외 (영문 → 한국어 자동 번역)

| 소스 | 신뢰도 | 특징 |
|------|--------|------|
| 🟠 **Hacker News** | ⭐⭐⭐⭐⭐ | Y Combinator 운영. 개발자 업보팅 기반. 새 툴 등장하면 가장 먼저 토론 시작 |
| 🔴 **Product Hunt** | ⭐⭐⭐⭐⭐ | AI/개발도구 신규 런칭 1번지. Lovable·Bolt·v0 모두 여기서 처음 화제 |
| ⚫ **GitHub Trending** | ⭐⭐⭐⭐⭐ | 실제 개발자들이 Star 준 레포. 스타 수 = 실사용 증거 |
| 🔵 **Reddit** | ⭐⭐⭐⭐ | r/LocalLLaMA, r/ChatGPTCoding 등 실사용 후기·비교 토론 풍부 |

### 국내

| 소스 | 특징 |
|------|------|
| 🟢 **GeekNews (긱뉴스)** | 한국판 Hacker News. 국내 개발자 큐레이션 |
| 🟡 **Velog 트렌딩** | 한국 개발자 블로그 실사용 리뷰·튜토리얼 |
| 🟣 **요즘IT** | 국내 IT 미디어. 툴 소개·비교 아티클 |

---

## ⚙️ 세팅 방법 (약 10분)

### 1단계 — GitHub 레포 만들기

```bash
# 이 폴더 전체를 GitHub에 올리기
git init
git add .
git commit -m "init: AI trend slack bot"
git remote add origin https://github.com/YOUR_ID/ai-trend-bot.git
git push -u origin main
```

### 2단계 — Slack Webhook URL 발급

1. https://api.slack.com/apps → **Create New App** → **From scratch**
2. 앱 이름: `AI Trend Bot`, 워크스페이스 선택
3. 좌측 메뉴 **Incoming Webhooks** → **Activate** ON
4. **Add New Webhook to Workspace** → 알림 받을 채널 선택
5. Webhook URL 복사 (`https://hooks.slack.com/services/T.../B.../...`)

### 3단계 — Anthropic API 키 발급

1. https://console.anthropic.com → **API Keys** → **Create Key**
2. 키 복사 (`sk-ant-api03-...`)
3. 💰 예상 비용: Claude Haiku 기준 **월 $1~3** (하루 2회 × 30일)

### 4단계 — GitHub Secrets 등록

레포 → **Settings** → **Secrets and variables** → **Actions** → **New repository secret**

| Secret 이름 | 값 | 필수 |
|-------------|-----|------|
| `ANTHROPIC_API_KEY` | Anthropic API 키 | ✅ 필수 |
| `SLACK_WEBHOOK_URL` | Slack Webhook URL | ✅ 필수 |
| `PRODUCT_HUNT_TOKEN` | Product Hunt API 토큰 | ⬜ 선택 (없으면 RSS 사용) |

### 5단계 — 완료! 🎉

다음날부터 오전 9시 / 오후 6시에 자동 발송됩니다.

**즉시 테스트하려면:**  
GitHub → **Actions** 탭 → **AI Dev Tool Trend Bot** → **Run workflow** → 실행

---

## 📱 Slack 메시지 예시

```
🤖 AI 개발도구 트렌드  🌅 오전 브리핑
📅 2025년 03월 10일  09:00 KST  |  총 22개 항목 수집
──────────────────────────────────────────────────
🟠 [Hacker News]
Cursor, Claude Sonnet 통합으로 코드 완성 정확도 40% 향상
› 주요 업데이트
_Cursor integrates Claude Sonnet for 40% better completions_
⬆️ 847점  💬 234댓글
🔗 원문 보기  ›  💬 토론 보기
──────────────────────────────────────────────────
🔴 [Product Hunt]
Bolt.new 2.0 — 대화만으로 풀스택 앱 생성
› 노코드 AI 빌더
_Bolt.new 2.0 — Build full-stack apps with just conversation_
⬆️ 1,204표  💬 89댓글
🔗 원문 보기
──────────────────────────────────────────────────
🟢 [GeekNews (긱뉴스)]
GitHub Copilot이 Claude를 기본 모델로 채택한 이유
🇰🇷 한국판 Hacker News
🔗 원문 보기
```

---

## 🔧 커스터마이징

### 알림 시간 변경 (`.github/workflows/daily-bot.yml`)

```yaml
schedule:
  - cron: "0 23 * * *"  # 오전 8시 KST
  - cron: "0 9 * * *"   # 오후 6시 KST
```

| 원하는 KST 시각 | cron (UTC) |
|----------------|------------|
| 오전 7시 | `0 22 * * *` (전날) |
| 오전 9시 | `0 0 * * *` |
| 오후 12시 | `0 3 * * *` |
| 오후 6시 | `0 9 * * *` |

### 키워드 추가 (`main.py`)

```python
AI_DEV_KEYWORDS = [
    "copilot", "cursor", "lovable",
    "여기에 새 툴 이름 추가",  # ← 추가
    ...
]
```

### Reddit 서브레딧 변경

```python
# fetch_reddit() 함수 내 subreddits 리스트 수정
subreddits = [
    "webdev", "learnprogramming", "devops",  # 원하는 서브레딧으로 교체
]
```

---

## 💰 비용 구조 (거의 무료)

| 항목 | 비용 |
|------|------|
| GitHub Actions | 완전 무료 (월 2,000분 제공, 이 봇은 ~120분 사용) |
| Hacker News API | 완전 무료 |
| Reddit JSON API | 완전 무료 |
| GitHub Trending | 무료 (스크래핑) |
| Product Hunt RSS | 무료 (GraphQL은 토큰 필요) |
| GeekNews RSS | 완전 무료 |
| Velog RSS | 완전 무료 |
| 요즘IT RSS | 완전 무료 |
| **Claude Haiku API** | **월 $1~3** ← 유일한 비용 |

**총 월 비용: $1~3** 🎉
