"""
Archyards Scheduler — scheduler.py
Runs the full crawl → rank → rewrite → publish pipeline daily.
Can be run standalone or via cron.
"""


# import schedule
# import time
# import sys, os
import json
import logging
import shutil
from datetime import datetime, timezone
from pathlib import Path
import os


# Add parent to path
from fetcher import crawl_all, save_articles
from rewriter import run_rewriter

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler("scheduler.log"),
        logging.StreamHandler()
    ]
)
log = logging.getLogger(__name__)

# ── CONFIG ───────────────────────────────────────────────────────────────────
CONFIG = {
    "articles_per_day":  5,      # 3-5 articles selected daily
    "min_articles":      3,
    "run_time":          "07:00", # Run every day at 7am
    "raw_path":          "storage/raw_articles.json",
    "rewritten_path":    "storage/rewritten_articles.json",
    "published_path":    "storage/published_articles.json",
    "archive_dir":       "storage/archive",
    "api_key":           os.environ.get("ANTHROPIC_API_KEY"),
}


def archive_previous():
    """Move yesterday's published file to archive."""
    pub = Path(CONFIG["published_path"])
    if not pub.exists():
        return
    archive_dir = Path(CONFIG["archive_dir"])
    archive_dir.mkdir(parents=True, exist_ok=True)
    date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    dest = archive_dir / f"published_{date_str}.json"
    shutil.copy(pub, dest)
    log.info(f"📦 Archived previous articles to {dest}")


def merge_with_published(new_articles: list[dict]) -> list[dict]:
    """
    Merge new articles with existing published ones.
    Keeps a rolling window of the last 30 days.
    """
    pub_path = Path(CONFIG["published_path"])
    existing = []
    if pub_path.exists():
        with open(pub_path, encoding="utf-8") as f:
            existing = json.load(f)

    # Deduplicate by ID
    existing_ids = {a["id"] for a in existing}
    truly_new = [a for a in new_articles if a["id"] not in existing_ids]

    merged = truly_new + existing
    # Keep last 150 articles (approx 30 days × 5)
    merged = merged[:150]
    return merged


def mark_as_published(articles: list[dict]) -> list[dict]:
    """Tag articles with publish timestamp and aggregated badge."""
    now = datetime.now(timezone.utc).isoformat()
    for a in articles:
        a["published_at_archyards"] = now
        a["badge"] = "aggregated"
        a["status"] = "published"
    return articles


def run_pipeline():
    """Full daily pipeline: crawl → rank → rewrite → publish."""
    log.info("=" * 60)
    log.info(f"🚀 Archyards Crawler Pipeline starting — {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    log.info("=" * 60)

    # 1. Archive previous
    archive_previous()

    # 2. Crawl & rank
    log.info("\n📡 STEP 1: Crawling sources…")
    n = CONFIG["articles_per_day"]
    articles = crawl_all(top_n=n)

    if len(articles) < CONFIG["min_articles"]:
        log.warning(f"⚠ Only found {len(articles)} articles (min={CONFIG['min_articles']}). Continuing anyway.")

    save_articles(articles, CONFIG["raw_path"])

    # 3. Rewrite
    log.info("\n✍  STEP 2: Rewriting with AI engine…")
    if not CONFIG["api_key"]:
        log.warning("⚠ ANTHROPIC_API_KEY not set. Skipping rewrite step.")
        rewritten = [dict(**a, status="pending") for a in [
            json.loads(json.dumps(a.__dict__ if hasattr(a, '__dict__') else a))
            for a in articles
        ]]
    else:
        rewritten = run_rewriter(
            input_path=CONFIG["raw_path"],
            output_path=CONFIG["rewritten_path"],
            api_key=CONFIG["api_key"],
        )

    # 4. Mark as published and merge
    log.info("\n📤 STEP 3: Publishing…")
    to_publish = [a for a in rewritten if a.get("status") in ("rewritten", "pending")]
    to_publish = mark_as_published(to_publish)

    merged = merge_with_published(to_publish)

    Path(CONFIG["published_path"]).parent.mkdir(parents=True, exist_ok=True)
    with open(CONFIG["published_path"], "w", encoding="utf-8") as f:
        json.dump(merged, f, indent=2, ensure_ascii=False)

    log.info(f"\n✅ Pipeline complete!")
    log.info(f"   • {len(to_publish)} new articles published today")
    log.info(f"   • {len(merged)} total articles in feed")

    # 5. Print summary
    log.info("\n📋 TODAY'S ARTICLES:")
    for i, a in enumerate(to_publish, 1):
        title = a.get("rewritten_title") or a.get("original_title", "?")
        source = a.get("source_name", "?")
        log.info(f"  {i}. [{source}] {title[:70]}")

    return to_publish

# ENTRY POINT FOR DEPLOYMENT / CRON
if __name__ == "__main__":
    run_pipeline()







# ── ENTRY POINT ──────────────────────────────────────────────────────────────
# if __name__ == "__main__":
#     import argparse
#     parser = argparse.ArgumentParser(description="Archyards Article Crawler")
#     parser.add_argument(
#         "--run-now",
#         action="store_true",
#         help="Run pipeline immediately instead of waiting for schedule"
#     )
#     parser.add_argument(
#         "--time",
#         default=CONFIG["run_time"],
#         help=f"Daily run time in HH:MM format (default: {CONFIG['run_time']})"
#     )
#     parser.add_argument(
#         "--articles",
#         type=int,
#         default=CONFIG["articles_per_day"],
#         help="Number of articles per day (3-5 recommended)"
#     )
#     args = parser.parse_args()

#     CONFIG["articles_per_day"] = max(3, min(5, args.articles))
#     CONFIG["run_time"] = args.time

#     if args.run_now:
#         log.info("▶ Running pipeline immediately…")
#         run_pipeline()
#     else:
#         log.info(f"⏰ Scheduler started. Pipeline will run daily at {CONFIG['run_time']}")
#         schedule.every().day.at(CONFIG["run_time"]).do(run_pipeline)
#         log.info("   Press Ctrl+C to stop.\n")
#         while True:
#             schedule.run_pending()
#             time.sleep(30)
