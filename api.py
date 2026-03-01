"""
Archyards API — api.py
Lightweight Flask API that exposes published articles as JSON.
Your Next.js frontend can call this, or you can replace it with 
a Next.js API route that reads published_articles.json directly.
"""

from flask import Flask, jsonify, request
from pathlib import Path
import json
from datetime import datetime
import os

app = Flask(__name__)

PUBLISHED_PATH = Path("storage/published_articles.json")
ARCHIVE_DIR = Path("storage/archive")


def load_published() -> list[dict]:
    if not PUBLISHED_PATH.exists():
        return []
    with open(PUBLISHED_PATH, encoding="utf-8") as f:
        return json.load(f)


@app.route("/api/articles", methods=["GET"])
def get_articles():
    """
    GET /api/articles
    Query params:
      - limit: int (default 20)
      - offset: int (default 0)
      - category: string filter
      - badge: aggregated | paid
      - source: source name filter
    """
    articles = load_published()

    # Filter
    category = request.args.get("category")
    badge = request.args.get("badge")
    source = request.args.get("source")

    if category:
        articles = [a for a in articles if a.get("category") == category]
    if badge:
        articles = [a for a in articles if a.get("badge") == badge]
    if source:
        articles = [a for a in articles if a.get("source_name", "").lower() == source.lower()]

    # Paginate
    limit = min(int(request.args.get("limit", 20)), 100)
    offset = int(request.args.get("offset", 0))
    total = len(articles)
    page = articles[offset: offset + limit]

    return jsonify({
        "total": total,
        "limit": limit,
        "offset": offset,
        "articles": page,
    })


@app.route("/api/articles/today", methods=["GET"])
def get_today():
    """GET /api/articles/today — today's freshly crawled articles."""
    articles = load_published()
    today = datetime.utcnow().strftime("%Y-%m-%d")
    todays = [
        a for a in articles
        if a.get("published_at_archyards", "").startswith(today)
    ]
    return jsonify({"count": len(todays), "articles": todays})


@app.route("/api/articles/<article_id>", methods=["GET"])
def get_article(article_id: str):
    """GET /api/articles/:id — single article."""
    articles = load_published()
    match = next((a for a in articles if a["id"] == article_id), None)
    if not match:
        return jsonify({"error": "Not found"}), 404
    return jsonify(match)


@app.route("/api/sources", methods=["GET"])
def get_sources():
    """GET /api/sources — list all source names with article counts."""
    articles = load_published()
    from collections import Counter
    counts = Counter(a.get("source_name") for a in articles)
    return jsonify([{"source": k, "count": v} for k, v in counts.most_common()])


@app.route("/api/health", methods=["GET"])
def health():
    articles = load_published()
    return jsonify({
        "status": "ok",
        "total_articles": len(articles),
        "last_updated": articles[0].get("published_at_archyards") if articles else None,
    })


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
