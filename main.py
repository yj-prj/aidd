"""
AI 개발도구 트렌드 → Slack 알림 봇 v2
소스: Hacker News, Product Hunt, GitHub Trending, Reddit,
      GeekNews(긱뉴스), Velog 트렌딩, 요즘IT
번역: Claude Haiku (Anthropic)
실행: GitHub Actions — 매일 오전 9시 / 오후 6시 KST
"""

import os
import json
import requests
import xml.etree.ElementTree as ET
from datetime import datetime, timezone, timedelta
from anthropic import Anthropic

# ─────────────────────────────────────────
# 환경 설정
# ─────────────────────────────────────────
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
SLACK_WEBHOOK_URL = os.environ.get("SLACK_WEBHOOK_URL", "")
PRODUCT_HUNT_TOKEN = os.environ.get("PRODUCT_HUNT_TOKEN", "")
RUN_PERIOD = os.environ.get("RUN_PERIOD", "morning")  # "morning" | "evening"

KST = timezone(timedelta(hours=9))
HEADERS = {"User-Agent": "AI-Trend-SlackBot/2.0"}
client = Anthropic(api_key=ANTHROPIC_API_KEY)

# AI 개발도구 관련 키워드
AI_DEV_KEYWORDS = [
    # 바이브코딩 / AI 코드 에디터
    "copilot", "cursor", "lovable", "bolt", "v0", "replit",
    "windsurf", "codeium", "tabnine", "continue", "aider",
    "vibe coding", "vibe-coding", "vibecoding",
    "devin", "cline", "void", "zed", "supermaven",
    # AI 코딩 일반
    "ai coding", "ai-coding", "code generation", "coding assistant",
    "ai ide", "ai editor", "ai agent",
    # 주요 모델·회사
    "claude", "gpt-4", "gpt-5", "gemini", "llama", "mistral",
    "qwen", "deepseek", "openai", "anthropic",
    # 기술 키워드
    "llm", "mcp", "agentic", "rag", "fine-tuning",
    # 한국어 키워드
    "바이브코딩", "ai 도구", "ai개발", "코딩 도우미",
    "코드 생성", "깃헙 코파일럿", "코딩 에이전트",
]


def is_relevant(text: str) -> bool:
    t = text.lower()
    return any(kw in t for kw in AI_DEV_KEYWORDS)


# ══════════════════════════════════════════
# 소스 1 ─ Hacker News
# ══════════════════════════════════════════
def fetch_hacker_news() -> list[dict]:
    print("🟠 Hacker News...")
    out = []
    try:
        ids = requests.get(
            "https://hacker-news.firebaseio.com/v0/topstories.json", timeout=10
        ).json()[:150]

        for sid in ids:
            try:
                s = requests.get(
                    f"https://hacker-news.firebaseio.com/v0/item/{sid}.json", timeout=5
                ).json()
                if s and is_relevant(s.get("title", "")) and s.get("score", 0) >= 50:
                    out.append({
                        "source": "Hacker News",
                        "title": s["title"],
                        "url": s.get("url") or f"https://news.ycombinator.com/item?id={sid}",
                        "score": s.get("score", 0),
                        "comments_url": f"https://news.ycombinator.com/item?id={sid}",
                        "meta": f"⬆️ {s.get('score',0)}점  💬 {s.get('descendants',0)}댓글",
                    })
            except Exception:
                continue
    except Exception as e:
        print(f"  ⚠️ {e}")

    out.sort(key=lambda x: x["score"], reverse=True)
    print(f"  → {len(out[:5])}개")
    return out[:5]


# ══════════════════════════════════════════
# 소스 2 ─ Product Hunt
# ══════════════════════════════════════════
def fetch_product_hunt() -> list[dict]:
    print("🔴 Product Hunt...")
    out = []

    # GraphQL (토큰 있을 때)
    if PRODUCT_HUNT_TOKEN:
        try:
            q = """{ posts(first:20, order:VOTES, topic:"developer-tools") {
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
                if is_relevant(p["name"] + " " + p["tagline"]):
                    out.append({
                        "source": "Product Hunt",
                        "title": f"{p['name']} — {p['tagline']}",
                        "url": p["url"],
                        "score": p["votesCount"],
                        "comments_url": p["url"],
                        "meta": f"⬆️ {p['votesCount']}표  💬 {p['commentsCount']}댓글",
                    })
        except Exception as e:
            print(f"  ℹ️ GraphQL 실패 → RSS 사용: {e}")

    # RSS fallback
    if not out:
        try:
            resp = requests.get("https://www.producthunt.com/feed", headers=HEADERS, timeout=10)
            root = ET.fromstring(resp.content)
            for item in root.findall(".//item"):
                title = item.findtext("title", "")
                link = item.findtext("link", "")
                if is_relevant(title):
                    out.append({
                        "source": "Product Hunt",
                        "title": title,
                        "url": link,
                        "score": 0,
                        "comments_url": link,
                        "meta": "🆕 오늘의 신규 툴 출시",
                    })
        except Exception as e:
            print(f"  ⚠️ RSS 오류: {e}")

    print(f"  → {len(out[:5])}개")
    return out[:5]


# ══════════════════════════════════════════
# 소스 3 ─ GitHub Trending
# ══════════════════════════════════════════
def fetch_github_trending() -> list[dict]:
    print("⚫ GitHub Trending...")
    out = []

    # gitterapp 비공식 API
    try:
        resp = requests.get(
            "https://api.gitterapp.com/repos?since=daily", headers=HEADERS, timeout=10
        )
        if resp.status_code == 200:
            for r in resp.json():
                if is_relevant(r.get("name", "") + " " + r.get("description", "")):
                    out.append({
                        "source": "GitHub Trending",
                        "title": f"{r.get('author','')}/{r.get('name','')} — {r.get('description','')}",
                        "url": r.get("url", ""),
                        "score": r.get("stars", 0),
                        "comments_url": r.get("url", ""),
                        "meta": f"⭐ {r.get('stars',0)} 스타  🔥 오늘 +{r.get('currentPeriodStars',0)}",
                    })
    except Exception as e:
        print(f"  ℹ️ gitterapp 실패: {e}")

    # 스크래핑 fallback
    if not out:
        import re
        try:
            resp = requests.get("https://github.com/trending", headers=HEADERS, timeout=10)
            repos = re.findall(r'href="/([a-zA-Z0-9._-]+/[a-zA-Z0-9._-]+)"', resp.text)
            descs = re.findall(r'<p class="col-9[^"]*"[^>]*>\s*([^<]+)\s*</p>', resp.text)
            seen_r = set()
            for i, rp in enumerate(repos):
                if rp in seen_r or "/" not in rp:
                    continue
                seen_r.add(rp)
                desc = descs[len(seen_r)-1].strip() if len(seen_r)-1 < len(descs) else ""
                if is_relevant(rp + " " + desc):
                    out.append({
                        "source": "GitHub Trending",
                        "title": f"{rp} — {desc}",
                        "url": f"https://github.com/{rp}",
                        "score": 0,
                        "comments_url": f"https://github.com/{rp}",
                        "meta": "🔥 GitHub 오늘의 트렌딩",
                    })
                if len(out) >= 5:
                    break
        except Exception as e:
            print(f"  ⚠️ 스크래핑 오류: {e}")

    print(f"  → {len(out[:5])}개")
    return out[:5]


# ══════════════════════════════════════════
# 소스 4 ─ Reddit
# ══════════════════════════════════════════
def fetch_reddit() -> list[dict]:
    print("🔵 Reddit...")
    subreddits = [
        "programming", "MachineLearning", "LocalLLaMA",
        "ChatGPTCoding", "artificial", "singularity",
    ]
    out = []
    for sub in subreddits:
        try:
            data = requests.get(
                f"https://www.reddit.com/r/{sub}/hot.json?limit=25",
                headers=HEADERS, timeout=10,
            ).json()["data"]["children"]
            for post in data:
                d = post["data"]
                if is_relevant(d.get("title", "")) and d.get("score", 0) >= 100:
                    url = d.get("url", "")
                    pl = f"https://reddit.com{d['permalink']}"
                    out.append({
                        "source": f"Reddit r/{sub}",
                        "title": d["title"],
                        "url": url if url.startswith("http") else pl,
                        "score": d.get("score", 0),
                        "comments_url": pl,
                        "meta": f"⬆️ {d.get('score',0)}점  💬 {d.get('num_comments',0)}댓글  📌 r/{sub}",
                    })
        except Exception as e:
            print(f"  ⚠️ r/{sub}: {e}")

    seen, unique = set(), []
    for r in sorted(out, key=lambda x: x["score"], reverse=True):
        if r["title"] not in seen:
            seen.add(r["title"])
            unique.append(r)

    print(f"  → {len(unique[:6])}개")
    return unique[:6]


# ══════════════════════════════════════════
# 소스 5 ─ 한국 커뮤니티
# ══════════════════════════════════════════
def fetch_korean_communities() -> list[dict]:
    print("🇰🇷 한국 커뮤니티...")
    out = []

    # GeekNews (긱뉴스) — 한국 개발자 커뮤니티 HN격
    try:
        resp = requests.get("https://news.hada.io/new.atom", headers=HEADERS, timeout=10)
        root = ET.fromstring(resp.content)
        ns = {"a": "http://www.w3.org/2005/Atom"}
        for entry in root.findall("a:entry", ns)[:30]:
            title = entry.findtext("a:title", "", ns)
            link_el = entry.find("a:link", ns)
            link = link_el.get("href", "") if link_el is not None else ""
            summary = entry.findtext("a:summary", "", ns)
            if is_relevant(title + " " + summary):
                out.append({
                    "source": "GeekNews (긱뉴스)",
                    "title": title,
                    "url": link,
                    "score": 0,
                    "comments_url": link,
                    "meta": "🇰🇷 한국판 Hacker News",
                    "is_korean": True,
                })
    except Exception as e:
        print(f"  ⚠️ GeekNews: {e}")

    # Velog 트렌딩 — 한국 개발자 블로그
    try:
        resp = requests.get(
            "https://v2.velog.io/rss/@trending", headers=HEADERS, timeout=10
        )
        root = ET.fromstring(resp.content)
        for item in root.findall(".//item")[:20]:
            title = item.findtext("title", "")
            link = item.findtext("link", "")
            desc = item.findtext("description", "")
            if is_relevant(title + " " + desc):
                out.append({
                    "source": "Velog 트렌딩",
                    "title": title,
                    "url": link,
                    "score": 0,
                    "comments_url": link,
                    "meta": "✍️ Velog 트렌딩 포스트",
                    "is_korean": True,
                })
    except Exception as e:
        print(f"  ⚠️ Velog: {e}")

    # 요즘IT — 국내 IT 미디어
    try:
        resp = requests.get(
            "https://yozm.wishket.com/magazine/feed/", headers=HEADERS, timeout=10
        )
        root = ET.fromstring(resp.content)
        for item in root.findall(".//item")[:15]:
            title = item.findtext("title", "")
            link = item.findtext("link", "")
            desc = item.findtext("description", "")
            if is_relevant(title + " " + desc):
                out.append({
                    "source": "요즘IT",
                    "title": title,
                    "url": link,
                    "score": 0,
                    "comments_url": link,
                    "meta": "📰 국내 IT 미디어 아티클",
                    "is_korean": True,
                })
    except Exception as e:
        print(f"  ⚠️ 요즘IT: {e}")

    print(f"  → {len(out[:6])}개")
    return out[:6]


# ══════════════════════════════════════════
# Claude API — 번역 + 요약
# ══════════════════════════════════════════
def translate_and_summarize(items: list[dict]) -> list[dict]:
    if not items:
        return items
    print("\n🤖 Claude Haiku로 번역/요약 중...")

    to_translate = [
        {"id": i, "title": item["title"]}
        for i, item in enumerate(items)
        if not item.get("is_korean", False)
    ]

    # 한국어 항목은 번역 패스
    for i, item in enumerate(items):
        if item.get("is_korean"):
            item["title_ko"] = item["title"]
            item["summary"] = ""

    if not to_translate:
        return items

    prompt = f"""다음 AI 개발도구 뉴스 제목을 한국어로 번역하고 한 줄 요약을 작성하세요.

규칙:
- title_ko: 자연스러운 한국어 번역 (툴 이름·고유명사는 영문 유지)
- summary: 15자 이내, 왜 주목받는지 핵심만

JSON 배열로만 응답 (코드블록 없이):
[{{"id": 0, "title_ko": "번역 제목", "summary": "핵심 요약"}}]

뉴스 목록:
{json.dumps(to_translate, ensure_ascii=False)}"""

    try:
        msg = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=2000,
            messages=[{"role": "user", "content": prompt}],
        )
        raw = msg.content[0].text.strip()
        if raw.startswith("```"):
            raw = "\n".join(raw.split("\n")[1:-1])
        translations = {t["id"]: t for t in json.loads(raw)}
        for i, item in enumerate(items):
            if not item.get("is_korean") and i in translations:
                item["title_ko"] = translations[i].get("title_ko", item["title"])
                item["summary"] = translations[i].get("summary", "")
            elif not item.get("is_korean"):
                item.setdefault("title_ko", item["title"])
                item.setdefault("summary", "")
    except Exception as e:
        print(f"  ⚠️ 번역 오류: {e}")
        for item in items:
            item.setdefault("title_ko", item["title"])
            item.setdefault("summary", "")

    return items


# ══════════════════════════════════════════
# Slack 전송
# ══════════════════════════════════════════
SOURCE_EMOJI = {
    "Hacker News": "🟠",
    "Product Hunt": "🔴",
    "GitHub Trending": "⚫",
    "Reddit": "🔵",
    "GeekNews": "🟢",
    "Velog": "🟡",
    "요즘IT": "🟣",
}


def emoji_for(source: str) -> str:
    for k, v in SOURCE_EMOJI.items():
        if k in source:
            return v
    return "⚪"


def send_to_slack(items: list[dict], period: str):
    if not items:
        print("📭 전송할 항목 없음")
        return

    now = datetime.now(KST)
    period_label = "🌅 오전 브리핑" if period == "morning" else "🌆 오후 브리핑"
    date_str = now.strftime("%Y년 %m월 %d일  %H:%M")

    blocks: list[dict] = [
        {
            "type": "header",
            "text": {"type": "plain_text", "text": f"🤖 AI 개발도구 트렌드  {period_label}"},
        },
        {
            "type": "context",
            "elements": [{"type": "mrkdwn",
                          "text": f"📅 {date_str} KST  |  총 {len(items)}개 항목 수집"}],
        },
        {"type": "divider"},
    ]

    for item in items:
        em = emoji_for(item["source"])
        title_ko = item.get("title_ko", item["title"])
        summary = item.get("summary", "")
        url = item["url"]
        comments_url = item.get("comments_url", url)
        is_ko = item.get("is_korean", False)

        links = f"<{url}|🔗 원문 보기>"
        if not is_ko and comments_url != url:
            links += f"  ›  <{comments_url}|💬 토론 보기>"

        lines = [
            f"{em} *[{item['source']}]*",
            f"*{title_ko}*",
        ]
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

    blocks.append({
        "type": "context",
        "elements": [{"type": "mrkdwn",
                      "text": "📡 *소스*: HN · ProductHunt · GitHub · Reddit · GeekNews · Velog · 요즘IT  |  🤖 번역: Claude Haiku"}],
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
    now = datetime.now(KST)
    print("=" * 55)
    print(f"🚀 AI 트렌드 봇 v2  [{period.upper()}]  {now.strftime('%Y-%m-%d %H:%M KST')}")
    print("=" * 55)

    items: list[dict] = []
    items.extend(fetch_hacker_news())
    items.extend(fetch_product_hunt())
    items.extend(fetch_github_trending())
    items.extend(fetch_reddit())
    items.extend(fetch_korean_communities())

    print(f"\n📊 총 수집: {len(items)}개")
    if not items:
        print("❌ 수집 항목 없음. 종료.")
        return

    items = translate_and_summarize(items)
    send_to_slack(items, period)


if __name__ == "__main__":
    main()
