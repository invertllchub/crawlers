# Archyards Crawler & Rewrite Engine

Automatically fetches the most popular articles from top architecture sites every day,
then rewrites their titles and descriptions in Archyards' editorial voice using Claude AI.

---

## 🏗 Architecture

```
archyards-crawler/
├── crawler/
│   └── fetcher.py          # RSS fetcher + popularity ranker
├── rewriter/
│   └── rewriter.py         # Claude AI rewrite engine
├── scheduler/
│   └── scheduler.py        # Daily pipeline orchestrator
├── dashboard/
│   └── index.html          # Web dashboard to monitor articles
├── storage/
│   ├── raw_articles.json       # Raw crawled articles
│   ├── rewritten_articles.json # After AI rewrite
│   └── published_articles.json # Final feed (consumed by Next.js)
├── api.py                  # Optional Flask API server
├── nextjs_api_route.ts     # Drop into your Next.js app/api/
└── requirements.txt
```

---

## ⚡ Quick Start

### 1. Install dependencies
```bash
cd archyards-crawler
pip install -r requirements.txt
```

### 2. Set your API key
```bash
export ANTHROPIC_API_KEY="sk-ant-..."
```

### 3. Run the pipeline immediately
```bash
python scheduler/scheduler.py --run-now
```

### 4. Schedule daily runs (7am every day)
```bash
python scheduler/scheduler.py
# or with custom time:
python scheduler/scheduler.py --time 06:30
```

---

## 🕷 Sources Crawled

| Site                   | Category     | RSS Feed               |
|------------------------|--------------|------------------------|
| Dezeen                 | Architecture | dezeen.com/feed        |
| ArchDaily              | Architecture | archdaily.com/feed     |
| Designboom             | Design       | designboom.com/feed    |
| Wallpaper*             | Design       | wallpaper.com/rss      |
| Architectural Digest   | Interior     | architecturaldigest.com|
| Archinect              | Architecture | archinect.com/feed     |
| Frame Magazine         | Interior     | frameweb.com/rss       |
| Metropolis             | Architecture | metropolismag.com/feed |

---

## 🤖 AI Rewrite Engine

The rewriter uses `claude-opus-4-6` to rewrite each article in **Archyards' editorial voice**:

- Confident, intelligent, slightly provocative
- Short punchy titles that spark curiosity
- Opening lines that editorially frame the story
- Factually accurate — never invents information
- Max 5 sentences for the description

**Example:**

> **Original (Dezeen):** "Foster + Partners completes tower in London's financial district"
>
> **Rewritten (Archyards):** "Glass and Steel Ambition: Foster + Partners' Latest Tower Reshapes the City's Skyline"

---

## 📊 Popularity Scoring

Articles are ranked by a composite score:

| Signal            | Weight  |
|-------------------|---------|
| Freshness (hours) | Up to 100 pts |
| Comment count     | ×2 per comment |
| Social shares     | ×0.5 per share |
| Random jitter     | 0-5 pts |

**Source diversity rule:** Max 2 articles per source per day to ensure variety.

---

## 🔌 Connecting to Next.js

### Option A — Direct file read (simplest)
Copy `nextjs_api_route.ts` to `app/api/aggregated/route.ts`.

The route reads `published_articles.json` directly from the filesystem.

```typescript
// In your component:
const res = await fetch('/api/aggregated?today=1&limit=5');
const { articles } = await res.json();
```

### Option B — Flask API server
```bash
python api.py  # starts on port 5001
```

Then in Next.js:
```typescript
const res = await fetch('http://localhost:5001/api/articles/today');
```

---

## 📅 Cron Setup (Production)

Add to crontab for guaranteed daily runs:
```bash
crontab -e

# Run Archyards crawler every day at 7am
0 7 * * * cd /path/to/archyards-crawler && /usr/bin/python3 scheduler/scheduler.py --run-now >> logs/cron.log 2>&1
```

---

## 🖥 Dashboard

Open `dashboard/index.html` in your browser while the Flask API is running.

Features:
- Live article preview with rewrite comparison
- Source breakdown stats
- Pipeline trigger button
- Log viewer

---

## ⚙️ Configuration

Edit `CONFIG` in `scheduler/scheduler.py`:

```python
CONFIG = {
    "articles_per_day": 5,      # 3–5 recommended
    "run_time": "07:00",        # Daily run time
    ...
}
```

---

## 📦 Article Data Structure

```json
{
  "id": "a1b2c3d4e5f6",
  "source_name": "Dezeen",
  "original_title": "Foster + Partners completes...",
  "rewritten_title": "Glass and Steel Ambition...",
  "rewritten_description": "Five editorial sentences...",
  "url": "https://dezeen.com/...",
  "image_url": "https://...",
  "published_at": "2025-02-25T07:00:00Z",
  "published_at_archyards": "2025-02-25T07:05:23Z",
  "category": "architecture",
  "tags": ["foster", "london", "skyscraper"],
  "popularity_score": 142.5,
  "badge": "aggregated",
  "status": "rewritten"
}
```
