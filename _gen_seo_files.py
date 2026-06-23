"""Generate initial sitemap.xml and rss.xml from CSV data."""
import csv, io, os, datetime

ARTICLES_DIR = "articles"

rows = []
try:
    import requests
    resp = requests.get("https://docs.google.com/spreadsheets/d/1PNIvLQsoyh6ssc5wEvtmB4K8eT9tyNmngeyRpa1rFbY/export?format=csv", timeout=30)
    rows = list(csv.reader(io.StringIO(resp.content.decode("utf-8"))))
except:
    local = "blog_content.csv"
    if os.path.exists(local):
        with open(local, encoding="utf-8") as f:
            rows = list(csv.reader(f))

base = "https://domanid.com"

# Build article list
articles = []
for i, row in enumerate(rows):
    if i == 0 or len(row) < 8:
        continue
    articles.append({"slug": row[1], "title": row[0], "excerpt": row[5], "date": row[3]})

articles.reverse()  # latest first

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
    urls.append(f'  <url>\n    <loc>{base}/articles/{art["slug"]}.html</loc>\n    <priority>0.6</priority>\n  </url>')

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
    safe_title = art["title"].replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    items.append(f"""    <item>
        <title>{safe_title}</title>
        <link>{base}/articles/{art["slug"]}.html</link>
        <description><![CDATA[{art["excerpt"]}]]></description>
        <guid>{base}/articles/{art["slug"]}.html</guid>
        <pubDate>{pubdate}</pubDate>
    </item>""")

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
