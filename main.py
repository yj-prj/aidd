"""
AI 개발도구 트렌드 → Slack 알림 봇 v4
소스 (해외 3): Hacker News, Product Hunt, GitHub Trending
소스 (국내 3): GeekNews(긱뉴스), Velog 트렌딩, 요즘IT
번역/요약: Google Gemini 2.0 Flash (완전 무료)
실행: GitHub Actions — 매일 오전 9시 / 오후 6시 KST

[키워드 2단계]
  TIER_1: AI 개발도구 / 바이브코딩 / AI assistant / AIDD
          → 소스당 최대 3개까지 우선 수집
  TIER_2: AI 전반 (트렌드, 생태계)
          → TIER_1 못 채운 경우 보충

[쿼터 보장]
  - 각 소스에서 TIER_1 우선, 부족하면 TIER_2로 채움
  - 그래도 없으면 해당 소스 상위 인기글 1개 fallback
  - 최종 Slack 메시지: 소스별 1~3개, 총 6~12개
"""

import os
import json
import requests
import xml.etree.ElementTree as ET
from collections import defaultdict
from datetime import datetime, timezone, timedelta

# ─────────────────────────────────────────
# 환경 설정
# ─────────────────────────────────────────
GEMINI_API_KEY     = os.environ.get("GEMINI_API_KEY", "")
SLACK_WEBHOOK_URL  = os.environ.get("SLACK_WEBHOOK_URL", "")
PRODUCT_HUNT_TOKEN = os.environ.get("PRODUCT_HUNT_TOKEN", "")
RUN_PERIOD         = os.environ.get("RUN_PERIOD", "morning")

KST        = timezone(timedelta(hours=9))
HEADERS    = {"User-Agent": "AI-Trend-SlackBot/4.0"}
GEMINI_URL = (
    "https://generativelanguage.googleapis.com/v1beta/models"
    "/gemini-2.0-flash:generateContent"
)

# ─────────────────────────────────────────
# TIER 1 — AI 개발도구 / 바이브코딩 / AI assistant / AIDD
#           이 키워드에 걸리면 우선 수집
# ─────────────────────────────────────────
TIER1_KEYWORDS = [
    # 바이브코딩 / AI 코드 에디터
    "copilot", "cursor", "lovable", "bolt", "v0 ",
    "windsurf", "codeium", "tabnine", "aider", "devin",
    "cline", "supermaven", "void editor", "zed ai",
    "vibe coding", "vibe-coding", "vibecoding",
    # AI 개발도구 일반
    "ai coding", "ai-coding", "ai code", "ai ide", "ai editor",
    "coding assistant", "ai pair programmer", "ai developer tool",
    "code generation", "code completion",
    # AI assistant / agent
    "ai assistant", "coding agent", "software agent",
    "autonomous coding", "agentic", "mcp server", "mcp tool",
    # AI-Driven Development
    "ai-driven development", "ai driven dev", "aidd",
    "ai workflow", "ai dev workflow", "ai pull request", "ai code review",
    # 한국어
    "바이브코딩", "ai 코딩", "ai 개발도구", "코딩 어시스턴트",
    "ai 코드 에디터", "ai 코드 리뷰", "깃헙 코파일럿", "코딩 에이전트",
]

# ─────────────────────────────────────────
# TIER 2 — AI 전반 트렌드
#           TIER1 부족할 때 보충용
# ─────────────────────────────────────────
TIER2_KEYWORDS = [
    # AI 전반
    "artificial intelligence", "machine learning", "deep learning",
    "large language model", "llm", "generative ai", "gen ai",
    "openai", "anthropic", "google ai", "mistral", "meta ai",
    "gpt", "claude", "gemini", "llama", "qwen", "deepseek",
    # AI 트렌드·생태계
    "ai startup", "ai product", "ai tool", "ai platform",
    "ai automation", "ai productivity", "ai integration",
    "prompt engineering", "rag", "fine-tuning", "inference",
    # 한국어
    "인공지능", "ai 도구", "ai 서비스", "ai 플랫폼",
    "생성 ai", "llm", "ai 스타트업",
]


def tier(text: str) -> int:
    """1=TIER1 매칭, 2=TIER2 매칭, 0=관련 없음"""
    t = text.lower()
    if any(kw in t for kw in TIER1_KEYWORDS):
        return 1
    if any(kw in t for kw in TIER2_KEYWORDS):
        return 2
    return 0


def pick_quota(candidates: list[dict], quota: int = 3) -> list[dict]:
    """
    candidates: tier 필드가 붙은 아이템 리스트
    TIER1 우선으로 quota개 선택. 부족하면 TIER2로 채움.
    """
    t1 = [x for x in candidates if x.get("tier") == 1]
    t2 = [x for x in candidates if x.get("tier") == 2]
    t0 = [x for x in candidates if x.get("tier") == 0]  # fallback

    result = t1[:quota]
    if len(result) < quota:
        result += t2[: quota - len(result)]
    if len(result) < 1:
        result += t0[:1]  # 아무것도 없으면 인기글 1개라도

    return result[:quota]


# ══════════════════════════════════════════
# 해외 1 ─ Hacker News
# ══════════════════════════════════════════
def fetch_hacker_news() -> list[dict]:
    print("🟠 Hacker News...")
    candidates = []
    try:
        ids = requests.get(
            "https://hacker-news.firebaseio.com/v0/topstories.json", timeout=10
        ).json()[:200]

        for sid in ids:
            try:
                s = requests.get(
                    f"https://hacker-news.firebaseio.com/v0/item/{sid}.json", timeout=5
                ).json()
                if not s or s.get("score", 0) < 20:
                    continue
                t = tier(s.get("title", ""))
                candidates.append({
                    "source": "Hacker News",
                    "title": s["title"],
                    "url": s.get("url") or f"https://news.ycombinator.com/item?id={sid}",
                    "score": s.get("score", 0),
                    "comments_url": f"https://news.ycombinator.com/item?id={sid}",
                    "meta": f"⬆️ {s.get('score',0)}점  💬 {s.get('descendants',0)}댓글",
                    "tier": t,
                })
            except Exception:
                continue
    except Exception as e:
        print(f"  ⚠️ {e}")

    # 점수 순 정렬 후 쿼터 선택
    candidates.sort(key=lambda x: x["score"], reverse=True)
    out = pick_quota(candidates, quota=3)
    print(f"  → {len(out)}개 (TIER1: {sum(1 for x in out if x['tier']==1)}, TIER2: {sum(1 for x in out if x['tier']==2)})")
    return out


# ══════════════════════════════════════════
# 해외 2 ─ Product Hunt
# ══════════════════════════════════════════
def fetch_product_hunt() -> list[dict]:
    print("🔴 Product Hunt...")
    candidates = []

    if PRODUCT_HUNT_TOKEN:
        try:
            q = """{ posts(first:30, order:VOTES) {
                edges { node { name tagline url votesCount commentsCount } }
            }}"""
            resp = requests.post(
                "https://api.producthunt.com/v2/api/graphql",
                json={"query": q},
                headers={"Authorization": f"Bearer {PRODUCT_HUNT_TOKEN}",
                         "Content-Type": "application/json"},
                timeout=10,
            )
            for edge in resp.json()["data"]["posts"]["edges"]:
                p = edge["node"]
                combined = p["name"] + " " + p["tagline"]
                t = tier(combined)
                if t > 0:
                    candidates.append({
                        "source": "Product Hunt",
                        "title": f"{p['name']} — {p['tagline']}",
                        "url": p["url"],
                        "score": p["votesCount"],
                        "comments_url": p["url"],
                        "meta": f"⬆️ {p['votesCount']}표  💬 {p['commentsCount']}댓글",
                        "tier": t,
                    })
        except Exception as e:
            print(f"  ℹ️ GraphQL 실패 → RSS: {e}")

    # RSS fallback
    if not candidates:
        try:
            resp = requests.get("https://www.producthunt.com/feed", headers=HEADERS, timeout=10)
            root = ET.fromstring(resp.content)
            for item in root.findall(".//item"):
                title = item.findtext("title", "")
                link  = item.findtext("link", "")
                desc  = item.findtext("description", "")
                t = tier(title + " " + desc)
                if t > 0:
                    candidates.append({
                        "source": "Product Hunt",
                        "title": title, "url": link,
                        "score": 0, "comments_url": link,
                        "meta": "🆕 오늘의 신규 툴 출시",
                        "tier": t,
                    })
        except Exception as e:
            print(f"  ⚠️ RSS 오류: {e}")

    out = pick_quota(candidates, quota=3)
    print(f"  → {len(out)}개 (TIER1: {sum(1 for x in out if x['tier']==1)}, TIER2: {sum(1 for x in out if x['tier']==2)})")
    return out


# ══════════════════════════════════════════
# 해외 3 ─ GitHub Trending
# ══════════════════════════════════════════
def fetch_github_trending() -> list[dict]:
    print("⚫ GitHub Trending...")
    candidates = []

    try:
        resp = requests.get(
            "https://api.gitterapp.com/repos?since=daily", headers=HEADERS, timeout=10
        )
        if resp.status_code == 200:
            for r in resp.json():
                combined = r.get("name", "") + " " + r.get("description", "")
                t = tier(combined)
                candidates.append({
                    "source": "GitHub Trending",
                    "title": f"{r.get('author','')}/{r.get('name','')} — {r.get('description','')}",
                    "url": r.get("url", ""),
                    "score": r.get("stars", 0),
                    "comments_url": r.get("url", ""),
                    "meta": f"⭐ {r.get('stars',0)}  🔥 오늘 +{r.get('currentPeriodStars',0)}",
                    "tier": t,
                })
    except Exception as e:
        print(f"  ℹ️ gitterapp 실패: {e}")

    # 스크래핑 fallback
    if not candidates:
        import re
        try:
            resp = requests.get("https://github.com/trending", headers=HEADERS, timeout=10)
            repos = re.findall(r'href="/([a-zA-Z0-9._-]+/[a-zA-Z0-9._-]+)"', resp.text)
            descs = re.findall(r'<p class="col-9[^"]*"[^>]*>\s*([^<]+)\s*</p>', resp.text)
            seen, idx = set(), 0
            for rp in repos:
                if rp in seen or rp.count("/") != 1:
                    continue
                seen.add(rp)
                desc = descs[idx].strip() if idx < len(descs) else ""
                idx += 1
                t = tier(rp + " " + desc)
                candidates.append({
                    "source": "GitHub Trending",
                    "title": f"{rp} — {desc}",
                    "url": f"https://github.com/{rp}",
                    "score": 0, "comments_url": f"https://github.com/{rp}",
                    "meta": "🔥 GitHub 오늘의 트렌딩",
                    "tier": t,
                })
                if len(candidates) >= 30:
                    break
        except Exception as e:
            print(f"  ⚠️ 스크래핑 오류: {e}")

    out = pick_quota(candidates, quota=3)
    print(f"  → {len(out)}개 (TIER1: {sum(1 for x in out if x['tier']==1)}, TIER2: {sum(1 for x in out if x['tier']==2)})")
    return out


# ══════════════════════════════════════════
# 국내 ─ GeekNews / Velog / 요즘IT
# ══════════════════════════════════════════
def _parse_korean_source(name: str, items_raw: list[tuple]) -> list[dict]:
    """
    items_raw: [(title, url, extra_text), ...]
    소스별로 tier 분류 후 쿼터 선택
    """
    candidates = []
    meta_map = {
        "GeekNews (긱뉴스)": "🇰🇷 한국판 Hacker News",
        "Velog 트렌딩":      "✍️ Velog 트렌딩 포스트",
        "요즘IT":            "📰 국내 IT 미디어",
    }
    for title, url, extra in items_raw:
        t = tier(title + " " + extra)
        candidates.append({
            "source": name,
            "title": title, "url": url,
            "score": 0, "comments_url": url,
            "meta": meta_map.get(name, ""),
            "tier": t,
            "is_korean": True,
        })
    return pick_quota(candidates, quota=2)


def fetch_korean_communities() -> list[dict]:
    print("🇰🇷 한국 커뮤니티...")
    out = []

    # GeekNews
    try:
        resp = requests.get("https://news.hada.io/new.atom", headers=HEADERS, timeout=10)
        root = ET.fromstring(resp.content)
        ns   = {"a": "http://www.w3.org/2005/Atom"}
        raw  = []
        for entry in root.findall("a:entry", ns)[:50]:
            title   = entry.findtext("a:title", "", ns)
            summary = entry.findtext("a:summary", "", ns)
            link_el = entry.find("a:link", ns)
            link    = link_el.get("href", "") if link_el is not None else ""
            raw.append((title, link, summary))
        out.extend(_parse_korean_source("GeekNews (긱뉴스)", raw))
    except Exception as e:
        print(f"  ⚠️ GeekNews: {e}")

    # Velog
    try:
        resp = requests.get("https://v2.velog.io/rss/@trending", headers=HEADERS, timeout=10)
        root = ET.fromstring(resp.content)
        raw  = []
        for item in root.findall(".//item")[:40]:
            title = item.findtext("title", "")
            link  = item.findtext("link", "")
            desc  = item.findtext("description", "")
            raw.append((title, link, desc))
        out.extend(_parse_korean_source("Velog 트렌딩", raw))
    except Exception as e:
        print(f"  ⚠️ Velog: {e}")

    # 요즘IT
    try:
        resp = requests.get("https://yozm.wishket.com/magazine/feed/", headers=HEADERS, timeout=10)
        root = ET.fromstring(resp.content)
        raw  = []
        for item in root.findall(".//item")[:30]:
            title = item.findtext("title", "")
            link  = item.findtext("link", "")
            desc  = item.findtext("description", "")
            raw.append((title, link, desc))
        out.extend(_parse_korean_source("요즘IT", raw))
    except Exception as e:
        print(f"  ⚠️ 요즘IT: {e}")

    t1 = sum(1 for x in out if x["tier"] == 1)
    t2 = sum(1 for x in out if x["tier"] == 2)
    print(f"  → {len(out)}개 (TIER1: {t1}, TIER2: {t2})")
    return out


# ══════════════════════════════════════════
# Gemini 호출 공통 함수
# ══════════════════════════════════════════
def call_gemini(prompt: str) -> str:
    resp = requests.post(
        GEMINI_URL,
        params={"key": GEMINI_API_KEY},
        json={"contents": [{"parts": [{"text": prompt}]}]},
        headers={"Content-Type": "application/json"},
        timeout=30,
    )
    if resp.status_code != 200:
        raise ValueError(f"HTTP {resp.status_code}: {resp.text[:200]}")
    return resp.json()["candidates"][0]["content"]["parts"][0]["text"].strip()


def clean_json(raw: str) -> str:
    """코드블록 제거 후 JSON 문자열 반환"""
    if "```" in raw:
        raw = "\n".join(l for l in raw.split("\n") if not l.strip().startswith("```"))
    return raw.strip()


# ══════════════════════════════════════════
# Step 1. Gemini 필터링 — 쓸만한 소식인지 체크
# ══════════════════════════════════════════
def gemini_filter(items: list[dict]) -> list[dict]:
    """
    수집된 뉴스를 Gemini에게 넘겨 AI 개발도구 관점에서
    '실제로 읽을 가치가 있는 소식'인지 판단.
    keep=true인 것만 통과시킴.
    """
    if not GEMINI_API_KEY:
        return items

    print(f"\n🔍 Gemini 필터링 중... ({len(items)}개)")

    news_list = [{"id": i, "title": item["title"], "source": item["source"]}
                 for i, item in enumerate(items)]

    prompt = f"""당신은 AI 개발도구 전문 큐레이터입니다.
아래 뉴스 목록을 검토하고, 다음 기준으로 읽을 가치가 있는 소식인지 판단하세요.

통과 기준 (하나라도 해당되면 keep=true):
- AI IDE / 코드 에디터 관련 (Cursor, Copilot, Windsurf, Lovable 등)
- Vibe coding / AI-Driven Development 트렌드
- AI coding assistant / coding agent 관련
- MCP (Model Context Protocol) 관련
- 새로운 AI 개발도구 출시 또는 주요 업데이트
- 개발자 워크플로우를 바꾸는 AI 툴·기능

제외 기준 (모두 해당되면 keep=false):
- 단순 모델 벤치마크·성능 비교
- AI 규제·정책·윤리 이슈
- AI 투자·인수합병 소식 (툴과 직접 관련 없는 것)
- 학술 논문·연구 발표

JSON 배열만 출력 (설명 없이):
[{{"id": 0, "keep": true, "reason": "한 줄 이유"}}]

뉴스 목록:
{json.dumps(news_list, ensure_ascii=False)}"""

    try:
        raw = call_gemini(prompt)
        print(f"  📝 필터 응답 미리보기: {raw[:100]}")
        results = {{r["id"]: r for r in json.loads(clean_json(raw))}}

        filtered = []
        dropped  = []
        for i, item in enumerate(items):
            r = results.get(i, {})
            if r.get("keep", True):  # 판단 못하면 기본 통과
                item["filter_reason"] = r.get("reason", "")
                filtered.append(item)
            else:
                dropped.append(item["title"][:50])

        print(f"  ✅ 통과: {len(filtered)}개  제외: {len(dropped)}개")
        if dropped:
            print(f"  🗑️ 제외된 항목: {dropped}")
        return filtered

    except Exception as e:
        print(f"  ⚠️ 필터링 오류: {e} → 전체 통과")
        return items


# ══════════════════════════════════════════
# Step 2. Gemini 번역 + 요약
# ══════════════════════════════════════════
def translate_and_summarize(items: list[dict]) -> list[dict]:
    for item in items:
        if item.get("is_korean"):
            item["title_ko"] = item["title"]
            item["summary"]  = ""

    to_translate = [
        {"id": i, "title": item["title"]}
        for i, item in enumerate(items)
        if not item.get("is_korean", False)
    ]

    if not to_translate:
        print("  ℹ️ 번역 대상 없음")
        return items

    print(f"\n🤖 Gemini 번역/요약 중... ({len(to_translate)}개)")

    if not GEMINI_API_KEY:
        print("  ❌ GEMINI_API_KEY 없음 → GitHub Secrets 확인 필요")
        for item in items:
            item.setdefault("title_ko", item["title"])
            item.setdefault("summary", "")
        return items

    prompt = f"""다음 AI 관련 뉴스 제목을 한국어로 번역하고 한 줄 요약을 작성하세요.

규칙:
- title_ko: 자연스러운 한국어 (툴 이름·고유명사는 영문 유지)
- summary: 20자 이내, 핵심만 (어떤 툴/내용인지, 왜 화제인지)
- JSON 배열만 출력 (```없이, 설명 없이)

출력 형식:
[{{"id": 0, "title_ko": "번역 제목", "summary": "핵심 요약"}}]

뉴스 목록:
{json.dumps(to_translate, ensure_ascii=False)}"""

    try:
        raw = call_gemini(prompt)
        print(f"  📝 번역 응답 미리보기: {raw[:100]}")
        translations = {{t["id"]: t for t in json.loads(clean_json(raw))}}
        print(f"  ✅ 번역 완료: {len(translations)}개")

        for i, item in enumerate(items):
            if not item.get("is_korean"):
                t = translations.get(i, {})
                item["title_ko"] = t.get("title_ko", item["title"])
                item["summary"]  = t.get("summary", "")

    except Exception as e:
        print(f"  ⚠️ 번역 오류: {e}")
        for item in items:
            item.setdefault("title_ko", item["title"])
            item.setdefault("summary", "")

    return items


# ══════════════════════════════════════════
# Step 3. Gemini 분석 — AI 개발도구 관점
# ══════════════════════════════════════════
def gemini_analyze(items: list[dict]) -> tuple:
    """
    통과된 뉴스 전체를 바탕으로 AI 개발도구 관점 인사이트 생성.
    반환: (분석 본문, 한 줄 트렌딩 요약)
    """
    if not GEMINI_API_KEY:
        return "", ""

    print("\n🧠 Gemini 분석 중...")

    titles = "\n".join(f"- [{item['source']}] {item['title']}" for item in items)

    prompt = f"""당신은 AI 개발도구 트렌드 분석가입니다.
아래는 오늘 전 세계 커뮤니티에서 수집·필터링된 AI 개발도구 관련 뉴스입니다.

다음 관점으로만 분석하세요 (다른 AI 이슈는 언급하지 말 것):
- Vibe coding / AIDD (AI-Driven Development) 흐름
- AI IDE / 코드 에디터 경쟁 구도
- AI coding agent / autonomous coding 동향
- MCP (Model Context Protocol) 생태계
- 주목할 신규 AI 개발도구

아래 형식으로 작성하세요:

📌 오늘의 핵심 트렌드
(2~3문장. 오늘 뉴스에서 가장 눈에 띄는 흐름)

🔥 주목할 움직임
(갑자기 화제가 된 툴·기능이 있다면 언급. 없으면 생략)

💡 개발자가 챙겨볼 것
(실제 개발 워크플로우에 영향을 줄 수 있는 내용 1~2가지)

🗞️ 오늘의 트렌딩 한 줄 요약
(위 전체를 압축한 딱 한 문장. "🗞️ 오늘의 트렌딩 한 줄 요약" 헤더 바로 아래에 작성)

뉴스 목록:
{titles}"""

    try:
        raw = call_gemini(prompt)
        print(f"  ✅ 분석 완료 ({len(raw)}자)")

        # 한 줄 요약 파싱
        one_liner = ""
        if "🗞️" in raw:
            after = raw.split("🗞️")[-1].strip()
            for line in after.splitlines():
                line = line.strip()
                if line and "한 줄 요약" not in line:
                    one_liner = line
                    break
            body = raw.split("🗞️")[0].strip()
        else:
            body = raw

        return body, one_liner

    except Exception as e:
        print(f"  ⚠️ 분석 오류: {e}")
        return "", ""


# ══════════════════════════════════════════
# Slack 전송
# ══════════════════════════════════════════
SOURCE_EMOJI = {
    "Hacker News":     "🟠",
    "Product Hunt":    "🔴",
    "GitHub Trending": "⚫",
    "GeekNews":        "🟢",
    "Velog":           "🟡",
    "요즘IT":           "🟣",
}
TIER_BADGE = {1: "🔧 개발도구", 2: "🌐 AI 전반"}


def emoji_for(source: str) -> str:
    for k, v in SOURCE_EMOJI.items():
        if k in source:
            return v
    return "⚪"


def send_to_slack(items: list[dict], analysis: str, one_liner: str, period: str):
    if not items:
        print("📭 전송할 항목 없음")
        return

    now          = datetime.now(KST)
    period_label = "🌅 오전 브리핑" if period == "morning" else "🌆 오후 브리핑"
    t1_cnt = sum(1 for x in items if x.get("tier") == 1)
    t2_cnt = sum(1 for x in items if x.get("tier") == 2)

    # ── 헤더
    blocks: list[dict] = [
        {"type": "header",
         "text": {"type": "plain_text", "text": f"🤖 AI 개발도구 트렌드  {period_label}"}},
        {"type": "context",
         "elements": [{"type": "mrkdwn",
             "text": (
                 f"📅 {now.strftime('%Y년 %m월 %d일  %H:%M')} KST  |  "
                 f"총 {len(items)}개  🔧 개발도구 {t1_cnt}개  🌐 AI전반 {t2_cnt}개"
             )}]},
        {"type": "divider"},
    ]

    # ── Gemini 분석 섹션 (맨 앞)
    if analysis:
        blocks.append({
            "type": "section",
            "text": {"type": "mrkdwn", "text": f"*🧠 오늘의 AI 개발도구 트렌드 분석*\n\n{analysis}"},
        })
        blocks.append({"type": "divider"})

    # ── 개별 뉴스 (소스 순서대로)
    source_order = [
        "Hacker News", "Product Hunt", "GitHub Trending",
        "GeekNews (긱뉴스)", "Velog 트렌딩", "요즘IT",
    ]
    grouped: dict = defaultdict(list)
    for item in items:
        grouped[item["source"]].append(item)

    for src in source_order:
        src_items = grouped.get(src, [])
        if not src_items:
            continue
        for item in src_items:
            em       = emoji_for(item["source"])
            title_ko = item.get("title_ko", item["title"])
            summary  = item.get("summary", "")
            url      = item["url"]
            c_url    = item.get("comments_url", url)
            is_ko    = item.get("is_korean", False)
            badge    = TIER_BADGE.get(item.get("tier", 0), "")

            links = f"<{url}|🔗 원문 보기>"
            if not is_ko and c_url != url:
                links += f"  ›  <{c_url}|💬 토론 보기>"

            lines = [f"{em} *[{item['source']}]*  `{badge}`"]
            lines.append(f"*{title_ko}*")
            if summary:
                lines.append(f"› _{summary}_")
            if not is_ko:
                lines.append(f"_{item['title']}_")
            lines.append(item["meta"])
            lines.append(links)

            blocks.append({
                "type": "section",
                "text": {"type": "mrkdwn", "text": "\n".join(lines)},
            })
            blocks.append({"type": "divider"})

    # ── 오늘의 트렌딩 한 줄 요약
    if one_liner:
        blocks.append({
            "type": "section",
            "text": {"type": "mrkdwn", "text": f"🗞️ *오늘의 트렌딩 한 줄 요약*\n{one_liner}"},
        })
        blocks.append({"type": "divider"})

    # ── 푸터
    blocks.append({
        "type": "context",
        "elements": [{"type": "mrkdwn",
            "text": (
                "📡 *해외*: HN · ProductHunt · GitHub  "
                "*국내*: GeekNews · Velog · 요즘IT  "
                "|  🤖 필터링·분석·번역: Gemini 2.0 Flash"
            )}],
    })

    resp = requests.post(SLACK_WEBHOOK_URL, json={"blocks": blocks}, timeout=10)
    if resp.status_code == 200:
        print(f"✅ Slack 전송 완료! ({len(items)}개 / {period_label})")
    else:
        print(f"❌ Slack 실패: {resp.status_code} — {resp.text}")


# ══════════════════════════════════════════
# 메인
# ══════════════════════════════════════════
def main():
    period = RUN_PERIOD
    now    = datetime.now(KST)
    print("=" * 55)
    print(f"🚀 AI 트렌드 봇 v5  [{period.upper()}]  {now.strftime('%Y-%m-%d %H:%M KST')}")
    print("=" * 55)

    # 1. 수집
    items: list[dict] = []
    items.extend(fetch_hacker_news())
    items.extend(fetch_product_hunt())
    items.extend(fetch_github_trending())
    items.extend(fetch_korean_communities())

    t1 = sum(1 for x in items if x.get("tier") == 1)
    t2 = sum(1 for x in items if x.get("tier") == 2)
    print(f"\n📊 수집: {len(items)}개  (🔧 TIER1: {t1}  🌐 TIER2: {t2})")

    if not items:
        print("❌ 수집 항목 없음. 종료.")
        return

    # 2. Gemini 필터링 — 쓸만한 소식인지 체크
    items = gemini_filter(items)

    if not items:
        print("❌ 필터링 후 항목 없음. 종료.")
        return

    # 3. Gemini 번역 + 요약
    items = translate_and_summarize(items)

    # 4. Gemini 분석 — AI 개발도구 관점 인사이트 + 한 줄 요약
    analysis, one_liner = gemini_analyze(items)

    # 5. Slack 발송 (분석 먼저, 뉴스 링크, 한 줄 요약 마지막)
    send_to_slack(items, analysis, one_liner, period)


if __name__ == "__main__":
    main()
