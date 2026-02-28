# ربط Archyards Crawler بفرونت إند Next.js

## الخطوة 1: نسخ الـ API Route داخل مشروع Next.js

1. في مشروع Next.js (مجلد الجذر)، أنشئ المسار:
   ```
   app/api/aggregated/route.ts
   ```
2. انسخ محتوى الملف `nextjs_api_route.ts` إلى `app/api/aggregated/route.ts`.

---

## الخطوة 2: تعديل مسار الملف (published_articles.json)

الـ API Route يقرأ من:
```
../archyards-crawler/storage/published_articles.json
```

- إذا مشروع Next.js عندك **جنب** مجلد الـ crawler (مثلاً: `Desktop/files` فيه الـ crawler و `Desktop/archyards-app` فيه Next.js)، غيّر في `route.ts` المتغير `PUBLISHED_PATH` ليشير للمسار الصحيح.
- مثال إذا الـ crawler في `Desktop/files` و Next.js في `Desktop/archyards-app`:
  ```ts
  const PUBLISHED_PATH = path.join(process.cwd(), "..", "files", "storage", "published_articles.json");
  ```
- أو استخدم متغير بيئة (أنسب للإنتاج):
  ```ts
  const PUBLISHED_PATH = process.env.CRAWLER_STORAGE_PATH || path.join(process.cwd(), "..", "archyards-crawler", "storage", "published_articles.json");
  ```
  ثم في `.env.local`:
  ```
  CRAWLER_STORAGE_PATH=C:\Users\MOHAMED THARWAT\Desktop\files\storage\published_articles.json
  ```

---

## الخطوة 3: تشغيل الـ Crawler مرة واحدة (حتى يوجد الملف)

من مجلد الـ crawler:
```bash
pip install -r requirements.txt
set ANTHROPIC_API_KEY=sk-ant-...
python scheduler/scheduler.py --run-now
```

سيتم إنشاء `storage/published_articles.json`. بعدها الـ API Route يقدر يقرأ منه.

---

## الخطوة 4: استدعاء الـ API من الفرونت إند

الـ API يدعم Query Parameters:

| Parameter | الوصف |
|-----------|--------|
| `category` | تصفية حسب الفئة (مثل architecture, design) |
| `badge` | aggregated أو paid |
| `source` | اسم المصدر (مثل Dezeen) |
| `today=1` | مقالات اليوم فقط |
| `limit` | عدد النتائج (افتراضي 20، أقصى 100) |
| `offset` | للـ pagination |

**أمثلة استدعاء من أي صفحة أو Server Component:**

```ts
// آخر 10 مقالات
const res = await fetch('/api/aggregated?limit=10');
const { articles, total } = await res.json();

// مقالات اليوم فقط
const resToday = await fetch('/api/aggregated?today=1&limit=5');

// تصفية حسب الفئة
const resCat = await fetch('/api/aggregated?category=architecture&limit=20');
```

استخدم الملف `AggregatedArticlesExample.tsx` كمثال جاهز لصفحة تعرض المقالات.

---

## ملخص المسار

```
[Crawler يشتغل] → published_articles.json
                        ↓
[Next.js API]   → GET /api/aggregated?limit=10
                        ↓
[صفحة Next.js]  → fetch('/api/aggregated') → عرض المقالات
```
