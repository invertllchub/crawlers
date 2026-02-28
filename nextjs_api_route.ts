/**
 * Next.js API Route — /app/api/aggregated/route.ts
 * 
 * Reads the published_articles.json file produced by the Python crawler
 * and serves it to your frontend components.
 * 
 * Place this file at: app/api/aggregated/route.ts
 */

import { NextRequest, NextResponse } from "next/server";
import { readFileSync, existsSync } from "fs";
import path from "path";

// Path to the crawler's output file
// Option 1: Set CRAWLER_STORAGE_PATH in .env.local (e.g. full path to published_articles.json)
// Option 2: Default path relative to Next.js root (adjust ".." and "archyards-crawler" to your setup)
const PUBLISHED_PATH =
  process.env.CRAWLER_STORAGE_PATH ||
  path.join(
    process.cwd(),
    "..",
    "archyards-crawler",
    "storage",
    "published_articles.json"
  );

export interface AggregatedArticle {
  id: string;
  source_name: string;
  source_logo: string;
  original_title: string;
  original_description: string;
  rewritten_title: string;
  rewritten_description: string;
  url: string;
  image_url: string;
  published_at: string;
  published_at_archyards: string;
  category: string;
  tags: string[];
  popularity_score: number;
  badge: "aggregated" | "paid";
  status: string;
}

function loadArticles(): AggregatedArticle[] {
  if (!existsSync(PUBLISHED_PATH)) {
    console.warn(`[archyards-crawler] published_articles.json not found at ${PUBLISHED_PATH}`);
    return [];
  }
  try {
    const raw = readFileSync(PUBLISHED_PATH, "utf-8");
    return JSON.parse(raw) as AggregatedArticle[];
  } catch (e) {
    console.error("[archyards-crawler] Failed to parse published_articles.json", e);
    return [];
  }
}

export async function GET(req: NextRequest) {
  const { searchParams } = req.nextUrl;

  let articles = loadArticles();

  // Filter params
  const category = searchParams.get("category");
  const badge = searchParams.get("badge");
  const source = searchParams.get("source");
  const today = searchParams.get("today");
  const limit = Math.min(parseInt(searchParams.get("limit") ?? "20"), 100);
  const offset = parseInt(searchParams.get("offset") ?? "0");

  if (category) articles = articles.filter((a) => a.category === category);
  if (badge) articles = articles.filter((a) => a.badge === badge);
  if (source) articles = articles.filter((a) => a.source_name.toLowerCase() === source.toLowerCase());
  if (today === "1") {
    const todayStr = new Date().toISOString().slice(0, 10);
    articles = articles.filter((a) => a.published_at_archyards?.startsWith(todayStr));
  }

  const total = articles.length;
  const page = articles.slice(offset, offset + limit);

  return NextResponse.json({ total, limit, offset, articles: page });
}
