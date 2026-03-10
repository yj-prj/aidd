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
# Gemini 번역 + 요약
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
            print(f"  ❌ Gemini {resp.status_code}: {resp.text[:200]}")
            raise ValueError(f"HTTP {resp.status_code}")

        raw = resp.json()["candidates"][0]["content"]["parts"][0]["text"].strip()
        print(f"  📝 응답 미리보기: {raw[:100]}")

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
TIER_BADGE = {1: "🔧 개발도구", 2: "🌐 AI 전반"}


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
    t1_cnt = sum(1 for x in items if x.get("tier") == 1)
    t2_cnt = sum(1 for x in items if x.get("tier") == 2)

    blocks: list[dict] = [
        {"type": "header",
         "text": {"type": "plain_text", "text": f"🤖 AI 트렌드  {period_label}"}},
        {"type": "context",
         "elements": [{"type": "mrkdwn",
             "text": (
                 f"📅 {now.strftime('%Y년 %m월 %d일  %H:%M')} KST  |  "
                 f"총 {len(items)}개  🔧 개발도구 {t1_cnt}개  🌐 AI전반 {t2_cnt}개"
             )}]},
        {"type": "divider"},
    ]

    # 소스 순서대로 그룹핑해서 출력
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

    blocks.append({
        "type": "context",
        "elements": [{"type": "mrkdwn",
            "text": (
                "📡 *해외*: HN · ProductHunt · GitHub  "
                "*국내*: GeekNews · Velog · 요즘IT  "
                "|  🤖 Gemini 2.0 Flash\n"
                "🔧 개발도구/바이브코딩/AI assistant/AIDD  🌐 AI 전반 트렌드"
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
    print(f"🚀 AI 트렌드 봇 v4  [{period.upper()}]  {now.strftime('%Y-%m-%d %H:%M KST')}")
    print("=" * 55)

    items: list[dict] = []
    items.extend(fetch_hacker_news())        # 해외 1  최대 3개
    items.extend(fetch_product_hunt())       # 해외 2  최대 3개
    items.extend(fetch_github_trending())    # 해외 3  최대 3개
    items.extend(fetch_korean_communities()) # 국내    소스별 최대 2개

    t1 = sum(1 for x in items if x.get("tier") == 1)
    t2 = sum(1 for x in items if x.get("tier") == 2)
    print(f"\n📊 총 수집: {len(items)}개  (🔧 TIER1 개발도구: {t1}개  🌐 TIER2 AI전반: {t2}개)")

    if not items:
        print("❌ 수집 항목 없음. 종료.")
        return

    items = translate_and_summarize(items)
    send_to_slack(items, period)


if __name__ == "__main__":
    main()
