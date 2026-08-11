"""Generate sitemap.xml and rss.xml from published site content."""

import datetime
import html
import json
import os

from article_inventory import (
    load_articles,
    validate_articles,
)


base = "https://domanid.com"


# Published HTML files are the source of truth.
articles = load_articles()

article_errors = validate_articles(
    articles
)

if article_errors:
    print(
        "[FAIL] Article inventory validation failed."
    )

    for error in article_errors:
        print(
            f"  - {error}"
        )

    raise SystemExit(1)

print(
    f"[INFO] Published articles: {len(articles)}"
)

# Sitemap
static = [
    ("", 1.0, "weekly"),
    ("about.html", 0.8, "monthly"),
    ("contact.html", 0.7, "monthly"),
    ("terms.html", 0.3, "yearly"),
    ("privacy.html", 0.3, "yearly"),
    ("articles/index.html", 0.9, "daily"),
]

urls = []
for path, pri, freq in static:
    u = f"  <url>\n    <loc>{base}/{path}</loc>\n    <priority>{pri}</priority>"
    if freq:
        u += f"\n    <changefreq>{freq}</changefreq>"
    u += "\n  </url>"
    urls.append(u)

for art in articles:
    urls.append(
        f'  <url>\n'
        f'    <loc>{art["canonical"]}</loc>\n'
        f'    <priority>0.6</priority>\n'
        f'  </url>'
    )


# Add active domain pages from normalized domain inventory
domains_data_file = os.path.join("data", "domains.json")

if os.path.exists(domains_data_file):
    try:
        with open(domains_data_file, encoding="utf-8") as f:
            domains_payload = json.load(f)

        for domain in domains_payload.get("domains", []):
            if str(domain.get("status", "")).lower() != "active":
                continue

            slug = str(domain.get("slug", "")).strip()

            if not slug:
                continue

            urls.append(
                f"  <url>\n"
                f"    <loc>{base}/domains/{slug}/</loc>\n"
                f"    <priority>0.8</priority>\n"
                f"    <changefreq>weekly</changefreq>\n"
                f"  </url>"
            )

    except Exception as exc:
        print(f"Warning: could not add domain pages to sitemap: {exc}")

with open("sitemap.xml", "w", encoding="utf-8") as f:
    f.write('<?xml version="1.0" encoding="UTF-8"?>\n')
    f.write('<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n')
    f.write("\n".join(urls))
    f.write("\n</urlset>\n")
print(f"Generated sitemap.xml with {len(urls)} URLs")

# RSS
items = []
for art in articles:
    pubdate = art["date"]
    try:
        dt = datetime.datetime.strptime(art["date"], "%Y-%m-%d")
        pubdate = dt.strftime("%a, %d %b %Y %H:%M:%S +0000")
    except:
        pass
    safe_title = html.escape(
        art["title"]
    )

    safe_description = (
        art["excerpt"]
        .replace("]]>", "]]&gt;")
    )

    items.append(
        f"""    <item>
        <title>{safe_title}</title>
        <link>{art["canonical"]}</link>
        <description><![CDATA[{safe_description}]]></description>
        <guid>{art["canonical"]}</guid>
        <pubDate>{pubdate}</pubDate>
    </item>"""
    )

rss = f"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom">
  <channel>
    <title>DomanID Blog - Domain Investing Insights</title>
    <link>{base}/articles/index.html</link>
    <description>Expert insights on domain investing, premium domain strategies, SEO, and digital asset management.</description>
    <language>en</language>
    <atom:link href="{base}/rss.xml" rel="self" type="application/rss+xml"/>
{chr(10).join(items)}
  </channel>
</rss>"""

with open("rss.xml", "w", encoding="utf-8") as f:
    f.write(rss)
print(f"Generated rss.xml with {len(items)} articles")
