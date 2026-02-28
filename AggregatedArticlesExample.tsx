"use client";

import { useEffect, useState } from "react";

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

interface ApiResponse {
  total: number;
  limit: number;
  offset: number;
  articles: AggregatedArticle[];
}

export default function AggregatedArticlesExample() {
  const [data, setData] = useState<ApiResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [filters, setFilters] = useState({ today: false, limit: 10 });

  useEffect(() => {
    const params = new URLSearchParams();
    params.set("limit", String(filters.limit));
    if (filters.today) params.set("today", "1");

    fetch(`/api/aggregated?${params.toString()}`)
      .then((res) => {
        if (!res.ok) throw new Error("فشل جلب المقالات");
        return res.json();
      })
      .then(setData)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, [filters.today, filters.limit]);

  if (loading) return <p className="p-4">جاري التحميل...</p>;
  if (error) return <p className="p-4 text-red-600">خطأ: {error}</p>;
  if (!data) return null;

  const { articles, total } = data;

  return (
    <div className="max-w-4xl mx-auto p-4">
      <div className="flex gap-4 mb-6 items-center flex-wrap">
        <label className="flex items-center gap-2">
          <input
            type="checkbox"
            checked={filters.today}
            onChange={(e) => setFilters((f) => ({ ...f, today: e.target.checked }))}
          />
          مقالات اليوم فقط
        </label>
        <select
          value={filters.limit}
          onChange={(e) => setFilters((f) => ({ ...f, limit: Number(e.target.value) }))}
        >
          <option value={5}>5</option>
          <option value={10}>10</option>
          <option value={20}>20</option>
        </select>
      </div>
      <p className="text-sm text-gray-500 mb-4">عدد النتائج: {total}</p>
      <ul className="space-y-6">
        {articles.map((article) => (
          <li key={article.id} className="border rounded-lg overflow-hidden shadow-sm">
            {article.image_url && (
              <img
                src={article.image_url}
                alt=""
                className="w-full h-48 object-cover"
              />
            )}
            <div className="p-4">
              <span className="text-xs text-gray-500">{article.source_name} · {article.category}</span>
              <h2 className="text-lg font-semibold mt-1">{article.rewritten_title || article.original_title}</h2>
              <p className="text-sm text-gray-600 mt-2 line-clamp-3">
                {article.rewritten_description || article.original_description}
              </p>
              <a
                href={article.url}
                target="_blank"
                rel="noopener noreferrer"
                className="text-sm text-blue-600 mt-2 inline-block"
              >
                اقرأ من المصدر →
              </a>
            </div>
          </li>
        ))}
      </ul>
    </div>
  );
}
