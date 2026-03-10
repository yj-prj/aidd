"""
AI 개발도구 트렌드 → Slack 알림 봇 v3
소스 (해외 3): Hacker News, Product Hunt, GitHub Trending
소스 (국내 3): GeekNews(긱뉴스), Velog 트렌딩, 요즘IT
번역/요약: Google Gemini 2.0 Flash (완전 무료)
실행: GitHub Actions — 매일 오전 9시 / 오후 6시 KST
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
RUN_PERIOD         = os.environ.get("RUN_PERIOD", "morning")  # morning | evening

KST     = timezone(timedelta(hours=9))
HEADERS = {"User-Agent": "AI-Trend-SlackBot/3.0"}
GEMINI_URL = (
    "https://generativelanguage.googleapis.com/v1beta/models"
    "/gemini-2.0-flash:generateContent"
)

# ─────────────────────────────────────────
# 키워드: AI assistant / 개발도구 위주
# (모델 출시·연구 뉴스는 제외)
# ─────────────────────────────────────────
AI_DEV_KEYWORDS = [
    # AI 코드 에디터 / 바이브코딩 도구
    "copilot", "cursor", "lovable", "bolt.new", "v0",
    "windsurf", "codeium", "tabnine", "aider", "devin",
    "cline", "replit agent", "supermaven", "void editor",
    "vibe coding", "vibe-coding", "vibecoding",
    # AI 개발 도구 일반
    "ai coding", "ai-coding", "ai code editor", "coding assistant",
    "ai ide", "ai editor", "ai developer tool",
    "code generation tool", "ai pair programmer",
    # AI assistant / agent
    "ai assistant", "coding agent", "software agent",
    "autonomous coding", "agentic development",
    "mcp server", "mcp tool",
    # 개발 워크플로우
    "developer productivity", "dev workflow",
    "ai code review", "ai pull request",
    # 한국어
    "바이브코딩", "ai 코딩", "ai 개발도구", "코딩 어시스턴트",
    "코드 에디터", "ai 코드 리뷰", "깃헙 코파일럿",
]


def is_relevant(text: str) -> bool:
    t = text.lower()
    return any(kw in t for kw in AI_DEV_KEYWORDS)


# ══════════════════════════════════════════
# 해외 1 ─ Hacker News
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
                if s and is_relevant(s.get("title", "")) and s.get("score", 0) >= 30:
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
    print(f"  → {len(out[:4])}개")
    return out[:4]


# ══════════════════════════════════════════
# 해외 2 ─ Product Hunt
# ══════════════════════════════════════════
def fetch_product_hunt() -> list[dict]:
    print("🔴 Product Hunt...")
    out = []

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
            print(f"  ℹ️ GraphQL 실패 → RSS: {e}")

    if not out:
        try:
            resp = requests.get("https://www.producthunt.com/feed", headers=HEADERS, timeout=10)
            root = ET.fromstring(resp.content)
            for item in root.findall(".//item"):
                title = item.findtext("title", "")
                link  = item.findtext("link", "")
                desc  = item.findtext("description", "")
                if is_relevant(title + " " + desc):
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

    print(f"  → {len(out[:4])}개")
    return out[:4]


# ══════════════════════════════════════════
# 해외 3 ─ GitHub Trending
# ══════════════════════════════════════════
def fetch_github_trending() -> list[dict]:
    print("⚫ GitHub Trending...")
    out = []

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
                        "meta": f"⭐ {r.get('stars',0)}  🔥 오늘 +{r.get('currentPeriodStars',0)}",
                    })
    except Exception as e:
        print(f"  ℹ️ gitterapp 실패: {e}")

    if not out:
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
                if is_relevant(rp + " " + desc):
                    out.append({
                        "source": "GitHub Trending",
                        "title": f"{rp} — {desc}",
                        "url": f"https://github.com/{rp}",
                        "score": 0,
                        "comments_url": f"https://github.com/{rp}",
                        "meta": "🔥 GitHub 오늘의 트렌딩",
                    })
                if len(out) >= 4:
                    break
        except Exception as e:
            print(f"  ⚠️ 스크래핑 오류: {e}")

    print(f"  → {len(out[:4])}개")
    return out[:4]


# ══════════════════════════════════════════
# 국내 3 ─ GeekNews / Velog / 요즘IT
# ══════════════════════════════════════════
def fetch_korean_communities() -> list[dict]:
    print("🇰🇷 한국 커뮤니티...")
    out = []

    # GeekNews
    try:
        resp = requests.get("https://news.hada.io/new.atom", headers=HEADERS, timeout=10)
        root = ET.fromstring(resp.content)
        ns   = {"a": "http://www.w3.org/2005/Atom"}
        for entry in root.findall("a:entry", ns)[:40]:
            title   = entry.findtext("a:title", "", ns)
            summary = entry.findtext("a:summary", "", ns)
            link_el = entry.find("a:link", ns)
            link    = link_el.get("href", "") if link_el is not None else ""
            if is_relevant(title + " " + summary):
                out.append({
                    "source": "GeekNews (긱뉴스)",
                    "title": title, "url": link,
                    "score": 0, "comments_url": link,
                    "meta": "🇰🇷 한국판 Hacker News",
                    "is_korean": True,
                })
    except Exception as e:
        print(f"  ⚠️ GeekNews: {e}")

    # Velog
    try:
        resp = requests.get("https://v2.velog.io/rss/@trending", headers=HEADERS, timeout=10)
        root = ET.fromstring(resp.content)
        for item in root.findall(".//item")[:30]:
            title = item.findtext("title", "")
            link  = item.findtext("link", "")
            desc  = item.findtext("description", "")
            if is_relevant(title + " " + desc):
                out.append({
                    "source": "Velog 트렌딩",
                    "title": title, "url": link,
                    "score": 0, "comments_url": link,
                    "meta": "✍️ Velog 트렌딩 포스트",
                    "is_korean": True,
                })
    except Exception as e:
        print(f"  ⚠️ Velog: {e}")

    # 요즘IT
    try:
        resp = requests.get("https://yozm.wishket.com/magazine/feed/", headers=HEADERS, timeout=10)
        root = ET.fromstring(resp.content)
        for item in root.findall(".//item")[:20]:
            title = item.findtext("title", "")
            link  = item.findtext("link", "")
            desc  = item.findtext("description", "")
            if is_relevant(title + " " + desc):
                out.append({
                    "source": "요즘IT",
                    "title": title, "url": link,
                    "score": 0, "comments_url": link,
                    "meta": "📰 국내 IT 미디어",
                    "is_korean": True,
                })
    except Exception as e:
        print(f"  ⚠️ 요즘IT: {e}")

    # 소스별 최대 3개
    per_source: dict = defaultdict(list)
    for item in out:
        per_source[item["source"]].append(item)
    trimmed = []
    for src_items in per_source.values():
        trimmed.extend(src_items[:3])

    print(f"  → {len(trimmed)}개")
    return trimmed


# ══════════════════════════════════════════
# Gemini 번역 + 요약
# ══════════════════════════════════════════
def translate_and_summarize(items: list[dict]) -> list[dict]:
    # 한국어 소스는 번역 스킵
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

    # API 키 누락 조기 감지
    if not GEMINI_API_KEY:
        print("  ❌ GEMINI_API_KEY 없음 → GitHub Secrets 확인 필요")
        for item in items:
            item.setdefault("title_ko", item["title"])
            item.setdefault("summary", "")
        return items

    prompt = f"""다음 AI 개발도구 뉴스 제목을 한국어로 번역하고 한 줄 요약을 작성하세요.

규칙:
- title_ko: 자연스러운 한국어 (툴 이름·고유명사는 영문 유지)
- summary: 20자 이내, 핵심만 (어떤 툴인지 or 왜 화제인지)
- 반드시 JSON 배열만 출력 (```없이, 설명 없이)

출력 형식:
[{{"id": 0, "title_ko": "번역 제목", "summary": "핵심 요약"}}]

뉴스 목록:
{json.dumps(to_translate, ensure_ascii=False)}"""

    try:
        resp = requests.post(
            GEMINI_URL,
            params={"key": GEMINI_API_KEY},
            json={"contents": [{"parts": [{"text": prompt}]}]},
            headers={"Content-Type": "application/json"},
            timeout=30,
        )

        if resp.status_code != 200:
            print(f"  ❌ Gemini API 오류 {resp.status_code}: {resp.text[:300]}")
            raise ValueError(f"HTTP {resp.status_code}")

        raw = resp.json()["candidates"][0]["content"]["parts"][0]["text"].strip()
        print(f"  📝 응답 미리보기: {raw[:120]}")

        # 코드블록 제거
        if "```" in raw:
            raw = "\n".join(l for l in raw.split("\n") if not l.strip().startswith("```")).strip()

        translations = {t["id"]: t for t in json.loads(raw)}
        print(f"  ✅ 번역 완료: {len(translations)}개")

        for i, item in enumerate(items):
            if not item.get("is_korean"):
                t = translations.get(i, {})
                item["title_ko"] = t.get("title_ko", item["title"])
                item["summary"]  = t.get("summary", "")

    except json.JSONDecodeError as e:
        print(f"  ⚠️ JSON 파싱 실패: {e}")
        for item in items:
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
    "Hacker News":     "🟠",
    "Product Hunt":    "🔴",
    "GitHub Trending": "⚫",
    "GeekNews":        "🟢",
    "Velog":           "🟡",
    "요즘IT":           "🟣",
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

    now          = datetime.now(KST)
    period_label = "🌅 오전 브리핑" if period == "morning" else "🌆 오후 브리핑"

    blocks: list[dict] = [
        {"type": "header",
         "text": {"type": "plain_text", "text": f"🤖 AI 개발도구 트렌드  {period_label}"}},
        {"type": "context",
         "elements": [{"type": "mrkdwn",
             "text": f"📅 {now.strftime('%Y년 %m월 %d일  %H:%M')} KST  |  {len(items)}개 항목"}]},
        {"type": "divider"},
    ]

    for item in items:
        em       = emoji_for(item["source"])
        title_ko = item.get("title_ko", item["title"])
        summary  = item.get("summary", "")
        url      = item["url"]
        c_url    = item.get("comments_url", url)
        is_ko    = item.get("is_korean", False)

        links = f"<{url}|🔗 원문 보기>"
        if not is_ko and c_url != url:
            links += f"  ›  <{c_url}|💬 토론 보기>"

        lines = [f"{em} *[{item['source']}]*", f"*{title_ko}*"]
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
            "text": "📡 HN · ProductHunt · GitHub · GeekNews · Velog · 요즘IT  |  🤖 Gemini 2.0 Flash"}],
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
    print(f"🚀 AI 트렌드 봇 v3  [{period.upper()}]  {now.strftime('%Y-%m-%d %H:%M KST')}")
    print("=" * 55)

    items: list[dict] = []
    items.extend(fetch_hacker_news())        # 해외 1
    items.extend(fetch_product_hunt())       # 해외 2
    items.extend(fetch_github_trending())    # 해외 3
    items.extend(fetch_korean_communities()) # 국내 (GeekNews + Velog + 요즘IT)

    print(f"\n📊 총 수집: {len(items)}개")
    if not items:
        print("❌ 수집 항목 없음. 종료.")
        return

    items = translate_and_summarize(items)
    send_to_slack(items, period)


if __name__ == "__main__":
    main()
