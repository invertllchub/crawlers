"""
Archyards Crawler — fetcher.py
Fetches RSS/Atom feeds from top architecture sites, scrapes article metadata,
and ranks articles by estimated popularity (views/comments/shares).
"""

import feedparser
import requests
from bs4 import BeautifulSoup
import json
import time
import logging
from datetime import datetime, timezone
from pathlib import Path
from dataclasses import dataclass, asdict
from typing import Optional
import random

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler("crawler.log"),
        logging.StreamHandler()
    ]
)
log = logging.getLogger(__name__)

# ── SOURCES ──────────────────────────────────────────────────────────────────
SOURCES = [
    {
        "name": "Dezeen",
        "rss": "https://www.dezeen.com/feed/",
        "base_url": "https://www.dezeen.com",
        "popularity_selector": None,   # will use comment count fallback
        "category": "architecture",
        "logo": "https://www.dezeen.com/favicon.ico",
    },
    {
        "name": "ArchDaily",
        "rss": "https://www.archdaily.com/feed",
        "base_url": "https://www.archdaily.com",
        "popularity_selector": ".ad-comments-count",
        "category": "architecture",
        "logo": "https://www.archdaily.com/favicon.ico",
    },
    {
        "name": "Designboom",
        "rss": "https://www.designboom.com/feed/",
        "base_url": "https://www.designboom.com",
        "popularity_selector": None,
        "category": "design",
        "logo": "https://www.designboom.com/favicon.ico",
    },
    {
        "name": "Wallpaper",
        "rss": "https://www.wallpaper.com/rss",
        "base_url": "https://www.wallpaper.com",
        "popularity_selector": None,
        "category": "design",
        "logo": "https://www.wallpaper.com/favicon.ico",
    },
    {
        "name": "Architectural Digest",
        "rss": "https://www.architecturaldigest.com/feed/rss",
        "base_url": "https://www.architecturaldigest.com",
        "popularity_selector": None,
        "category": "interior",
        "logo": "https://www.architecturaldigest.com/favicon.ico",
    },
    {
        "name": "Archinect",
        "rss": "https://archinect.com/feed/news",
        "base_url": "https://archinect.com",
        "popularity_selector": ".comment-count",
        "category": "architecture",
        "logo": "https://archinect.com/favicon.ico",
    },
    {
        "name": "Frame Magazine",
        "rss": "https://www.frameweb.com/rss",
        "base_url": "https://www.frameweb.com",
        "popularity_selector": None,
        "category": "interior",
        "logo": "https://www.frameweb.com/favicon.ico",
    },
    {
        "name": "Metropolis",
        "rss": "https://metropolismag.com/feed/",
        "base_url": "https://metropolismag.com",
        "popularity_selector": None,
        "category": "architecture",
        "logo": "https://metropolismag.com/favicon.ico",
    },
]

# ── DATA MODEL ───────────────────────────────────────────────────────────────
@dataclass
class Article:
    id: str
    source_name: str
    source_logo: str
    original_title: str
    original_description: str
    url: str
    image_url: str
    published_at: str
    category: str
    tags: list
    popularity_score: float
    comment_count: int
    # Filled later by rewriter
    rewritten_title: str = ""
    rewritten_description: str = ""
    status: str = "pending"   # pending | rewritten | published


# ── HELPERS ──────────────────────────────────────────────────────────────────
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (compatible; ArchyardsBot/1.0; "
        "+https://archyards.com/bot)"
    ),
    "Accept-Language": "en-US,en;q=0.9",
}

def safe_get(url: str, timeout: int = 10) -> Optional[requests.Response]:
    try:
        resp = requests.get(url, headers=HEADERS, timeout=timeout)
        resp.raise_for_status()
        return resp
    except Exception as e:
        log.warning(f"Failed to fetch {url}: {e}")
        return None


def extract_image(entry, soup: Optional[BeautifulSoup]) -> str:
    """Try multiple strategies to find the best image."""
    # 1. Media content in RSS
    if hasattr(entry, "media_content") and entry.media_content:
        for m in entry.media_content:
            if m.get("url", "").startswith("http"):
                return m["url"]

    # 2. Enclosure
    if hasattr(entry, "enclosures") and entry.enclosures:
        for enc in entry.enclosures:
            if "image" in enc.get("type", ""):
                return enc.get("href", "")

    # 3. OG image from page
    if soup:
        og = soup.find("meta", property="og:image")
        if og and og.get("content"):
            return og["content"]
        tw = soup.find("meta", {"name": "twitter:image"})
        if tw and tw.get("content"):
            return tw["content"]

    # 4. First <img> in summary
    if hasattr(entry, "summary"):
        bs = BeautifulSoup(entry.summary, "html.parser")
        img = bs.find("img")
        if img and img.get("src", "").startswith("http"):
            return img["src"]

    return ""


def extract_description(entry, soup: Optional[BeautifulSoup]) -> str:
    """Get clean plain-text description."""
    raw = ""

    # Try summary from RSS
    if hasattr(entry, "summary") and entry.summary:
        raw = entry.summary

    # If too short, try scraping article body
    if len(raw) < 100 and soup:
        for sel in ["article p", ".entry-content p", ".article-body p", "p"]:
            paras = soup.select(sel)
            if paras:
                raw = " ".join(p.get_text(" ", strip=True) for p in paras[:5])
                break

    # Strip HTML
    clean = BeautifulSoup(raw, "html.parser").get_text(" ", strip=True)
    return clean[:1500]  # cap at 1500 chars


def estimate_popularity(entry, soup: Optional[BeautifulSoup], source: dict) -> tuple[float, int]:
    """
    Score articles by freshness + comment count + engagement signals.
    Returns (score, comment_count).
    """
    score = 0.0
    comments = 0

    # Freshness bonus (newer = higher)
    try:
        pub = entry.get("published_parsed") or entry.get("updated_parsed")
        if pub:
            age_hours = (time.time() - time.mktime(pub)) / 3600
            score += max(0, 100 - age_hours)   # up to 100 pts for fresh content
    except Exception:
        pass

    # Comment count from page
    if soup and source.get("popularity_selector"):
        el = soup.select_one(source["popularity_selector"])
        if el:
            try:
                comments = int("".join(filter(str.isdigit, el.get_text())))
                score += comments * 2
            except ValueError:
                pass

    # OG/meta share signals
    if soup:
        # Some sites embed share counts in data attributes
        for attr in ["data-shares", "data-reactions", "data-likes"]:
            el = soup.find(attrs={attr: True})
            if el:
                try:
                    score += int(el[attr]) * 0.5
                except (ValueError, TypeError):
                    pass

    # Small random jitter to break ties
    score += random.uniform(0, 5)

    return round(score, 2), comments


def parse_tags(entry) -> list:
    tags = []
    if hasattr(entry, "tags"):
        tags = [t.term for t in entry.tags if hasattr(t, "term")]
    return tags[:8]


def article_id(source_name: str, url: str) -> str:
    import hashlib
    return hashlib.md5(f"{source_name}:{url}".encode()).hexdigest()[:12]


# ── MAIN CRAWLER ─────────────────────────────────────────────────────────────
def crawl_source(source: dict) -> list[Article]:
    log.info(f"Crawling {source['name']} — {source['rss']}")
    articles = []

    feed = feedparser.parse(
        source["rss"],
        request_headers=HEADERS,
        agent=HEADERS["User-Agent"]
    )

    if feed.bozo and not feed.entries:
        log.warning(f"  ⚠ Feed parse error for {source['name']}: {feed.bozo_exception}")
        return []

    log.info(f"  Found {len(feed.entries)} entries")

    for entry in feed.entries[:20]:  # check top 20 per source
        url = entry.get("link", "")
        if not url:
            continue

        # Small polite delay
        time.sleep(random.uniform(0.5, 1.5))

        # Fetch the actual article page for richer data
        resp = safe_get(url)
        soup = BeautifulSoup(resp.text, "html.parser") if resp else None

        title = entry.get("title", "Untitled")
        description = extract_description(entry, soup)
        image_url = extract_image(entry, soup)
        popularity_score, comment_count = estimate_popularity(entry, soup, source)
        tags = parse_tags(entry)

        pub_raw = entry.get("published") or entry.get("updated") or ""
        try:
            from email.utils import parsedate_to_datetime
            pub_dt = parsedate_to_datetime(pub_raw).isoformat()
        except Exception:
            pub_dt = datetime.now(timezone.utc).isoformat()

        art = Article(
            id=article_id(source["name"], url),
            source_name=source["name"],
            source_logo=source["logo"],
            original_title=title,
            original_description=description,
            url=url,
            image_url=image_url,
            published_at=pub_dt,
            category=source["category"],
            tags=tags,
            popularity_score=popularity_score,
            comment_count=comment_count,
        )
        articles.append(art)
        log.info(f"  ✓ {title[:60]}… [score={popularity_score}]")

    return articles


def crawl_all(top_n: int = 5) -> list[Article]:
    """Crawl all sources and return top N articles by popularity."""
    all_articles: list[Article] = []

    for source in SOURCES:
        try:
            articles = crawl_source(source)
            all_articles.extend(articles)
        except Exception as e:
            log.error(f"Error crawling {source['name']}: {e}")

    # Deduplicate by ID
    seen = set()
    unique = []
    for a in all_articles:
        if a.id not in seen:
            seen.add(a.id)
            unique.append(a)

    # Sort by popularity score desc
    unique.sort(key=lambda a: a.popularity_score, reverse=True)

    # Ensure variety: pick top N but no more than 2 from same source
    selected = []
    source_count: dict[str, int] = {}
    for art in unique:
        if len(selected) >= top_n:
            break
        count = source_count.get(art.source_name, 0)
        if count < 2:
            selected.append(art)
            source_count[art.source_name] = count + 1

    log.info(f"\n🏆 Top {len(selected)} articles selected from {len(unique)} total")
    for i, a in enumerate(selected, 1):
        log.info(f"  {i}. [{a.source_name}] {a.original_title[:70]} (score={a.popularity_score})")

    return selected


def save_articles(articles: list[Article], path: str = "storage/raw_articles.json"):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    data = [asdict(a) for a in articles]
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    log.info(f"💾 Saved {len(data)} articles to {path}")


if __name__ == "__main__":
    articles = crawl_all(top_n=5)
    save_articles(articles)
