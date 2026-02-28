"""
Archyards Rewriter — rewriter.py
Uses the Anthropic Claude API to rewrite article titles and first 5 lines
of description in Archyards' editorial voice.
"""

import anthropic
import json
import time
import logging
from pathlib import Path
from dataclasses import asdict

log = logging.getLogger(__name__)

# ── EDITORIAL VOICE GUIDE ────────────────────────────────────────────────────
SYSTEM_PROMPT = """You are the senior editor of Archyards, a prestigious architecture 
and design magazine with the editorial weight of Dezeen, the cultural insight of 
Wallpaper*, and the technical depth of ArchDaily.

Your job is to rewrite article titles and opening descriptions from other publications 
in Archyards' distinctive voice:

ARCHYARDS VOICE:
- Confident, intelligent, slightly provocative
- Never hyperbolic or clickbait — gravitas matters
- Short, punchy titles that spark curiosity
- Descriptions that open with a strong editorial observation, not a summary
- Mix of architectural precision and cultural commentary
- Present tense preferred
- No passive voice
- Maximum 5 sentences for the description

CRITICAL RULES:
- DO NOT copy original wording — rewrite fully in your own voice
- Preserve all factual accuracy (names, places, dates, buildings)
- Never invent facts not present in the original
- The result should feel like Archyards wrote it first, not borrowed it
- Return ONLY valid JSON, no extra text
"""

REWRITE_PROMPT = """Rewrite the following article for Archyards magazine.

SOURCE: {source_name}
ORIGINAL TITLE: {title}
ORIGINAL DESCRIPTION: {description}

Return a JSON object with exactly these two keys:
{{
  "rewritten_title": "Your rewritten title here",
  "rewritten_description": "Your rewritten 5-line description here. Each sentence on a new line."
}}

Remember: factually accurate, editorially fresh, Archyards voice."""


# ── REWRITER ─────────────────────────────────────────────────────────────────
class ArticleRewriter:
    def __init__(self, api_key: str = None):
        """
        api_key: Your Anthropic API key.
                 If None, reads from ANTHROPIC_API_KEY env var.
        """
        import os
        self.client = anthropic.Anthropic(
            api_key=api_key or os.environ.get("ANTHROPIC_API_KEY")
        )
        self.model = "claude-opus-4-6"

    def rewrite(self, article: dict) -> dict:
        """Rewrite a single article. Returns updated article dict."""
        log.info(f"✍  Rewriting: {article['original_title'][:60]}…")

        prompt = REWRITE_PROMPT.format(
            source_name=article["source_name"],
            title=article["original_title"],
            description=article["original_description"][:800],  # cap input
        )

        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=600,
                system=SYSTEM_PROMPT,
                messages=[{"role": "user", "content": prompt}]
            )

            raw = response.content[0].text.strip()

            # Parse JSON response
            # Strip markdown code fences if present
            if raw.startswith("```"):
                raw = raw.split("```")[1]
                if raw.startswith("json"):
                    raw = raw[4:]
            raw = raw.strip()

            result = json.loads(raw)

            article["rewritten_title"] = result.get("rewritten_title", article["original_title"])
            article["rewritten_description"] = result.get("rewritten_description", article["original_description"])
            article["status"] = "rewritten"

            log.info(f"  → New title: {article['rewritten_title']}")

        except json.JSONDecodeError as e:
            log.error(f"  ✗ JSON parse error: {e}\n  Raw: {raw[:200]}")
            article["status"] = "rewrite_failed"
        except anthropic.APIError as e:
            log.error(f"  ✗ API error: {e}")
            article["status"] = "rewrite_failed"

        return article

    def rewrite_batch(
        self,
        articles: list[dict],
        delay: float = 1.0
    ) -> list[dict]:
        """Rewrite all articles with a polite delay between calls."""
        results = []
        for i, article in enumerate(articles):
            if article.get("status") == "rewritten":
                log.info(f"  Skipping already rewritten: {article['original_title'][:50]}")
                results.append(article)
                continue

            rewritten = self.rewrite(article)
            results.append(rewritten)

            if i < len(articles) - 1:
                time.sleep(delay)

        return results


# ── PIPELINE ─────────────────────────────────────────────────────────────────
def run_rewriter(
    input_path: str = "storage/raw_articles.json",
    output_path: str = "storage/rewritten_articles.json",
    api_key: str = None,
):
    """Load raw articles, rewrite them, save results."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
    )

    # Load
    with open(input_path, encoding="utf-8") as f:
        articles = json.load(f)
    log.info(f"📥 Loaded {len(articles)} articles from {input_path}")

    # Rewrite
    rewriter = ArticleRewriter(api_key=api_key)
    rewritten = rewriter.rewrite_batch(articles)

    # Save
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(rewritten, f, indent=2, ensure_ascii=False)

    success = sum(1 for a in rewritten if a["status"] == "rewritten")
    log.info(f"💾 Saved {len(rewritten)} articles ({success} rewritten) to {output_path}")

    return rewritten


if __name__ == "__main__":
    import os
    run_rewriter(api_key=os.environ.get("ANTHROPIC_API_KEY"))
