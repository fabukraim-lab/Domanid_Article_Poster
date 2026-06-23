"""One-time migration: update all existing article HTML files with SEO improvements."""
import os
import re
import csv
import io

ARTICLES_DIR = "articles"
CSV_URL = "https://docs.google.com/spreadsheets/d/1PNIvLQsoyh6ssc5wEvtmB4K8eT9tyNmngeyRpa1rFbY/export?format=csv"
LOCAL_CSV_PATH = "blog_content.csv"

def fetch_csv():
    try:
        import requests
        resp = requests.get(CSV_URL, timeout=30)
        return list(csv.reader(io.StringIO(resp.content.decode('utf-8'))))
    except:
        try:
            with open(LOCAL_CSV_PATH, encoding="utf-8") as f:
                return list(csv.reader(f))
        except:
            return []

def reading_time(text):
    return max(1, round(len(text.split()) / 200))

def build_article_map(rows):
    m = {}
    for i, row in enumerate(rows):
        if i == 0 or len(row) < 8:
            continue
        m[row[1]] = {
            "title": row[0], "slug": row[1], "category": row[2],
            "date": row[3], "author": row[4], "excerpt": row[5],
            "content": row[6], "keywords": row[7],
            "image": row[8].strip() if len(row) >= 9 and row[8].strip() else "https://images.pexels.com/photos/160107/pexels-photo-160107.jpeg"
        }
    return m

def related_html(slug, all_articles, max_count=3):
    others = [a for a in all_articles if a["slug"] != slug]
    selected = others[:max_count]
    if not selected:
        return ""
    cards = ""
    for a in selected:
        cards += f"""
            <a href="{a['slug']}.html" class="glass-panel related-card" style="text-decoration:none; display:block;">
                <span class="article-meta">{a['category']}</span>
                <h4>{a['title']}</h4>
            </a>"""
    return f"""
        <div class="related-articles">
            <h3>Continue Reading</h3>
            <div class="related-grid">{cards}
            </div>
        </div>"""

def migrate_article(filepath, meta, all_articles):
    with open(filepath, "r", encoding="utf-8", errors="replace") as f:
        html = f.read()

    slug = meta["slug"]
    title = meta["title"]
    excerpt = meta["excerpt"]
    keywords = meta["keywords"]
    image = meta["image"]
    category = meta["category"]
    date = meta["date"]
    author = meta.get("author", "DomanID")
    content = meta.get("content", "")
    rt = reading_time(content)

    date_iso = date
    try:
        parts = date.split("-")
        if len(parts) == 3:
            date_iso = f"{parts[0]}-{parts[1]}-{parts[2]}"
    except:
        pass

    # 1. Add canonical after viewport
    if 'rel="canonical"' not in html:
        html = html.replace(
            '<meta name="viewport"',
            f'<meta name="viewport"\n    <link rel="canonical" href="https://domanid.com/articles/{slug}.html">\n    <meta name="viewport"'
        )

    # 2. Add preconnect hints after <!-- Google Fonts -->
    preconnect = """    <!-- Preconnect for Performance -->
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link rel="preconnect" href="https://www.googletagmanager.com">
    <link rel="preconnect" href="https://pagead2.googlesyndication.com">
    """
    if "Preconnect for Performance" not in html:
        html = html.replace("<!-- Google Fonts -->", preconnect + "    <!-- Google Fonts -->")

    # 3. Add og:site_name and Twitter card after og:image
    if 'og:site_name' not in html:
        html = html.replace(
            '<meta property="og:image"',
            '<meta property="og:site_name" content="DomanID">\n    <meta name="twitter:card" content="summary_large_image">\n    <meta name="twitter:title" content="' + title + '">\n    <meta name="twitter:description" content="' + excerpt + '">\n    <meta property="og:image"'
        )

    # 4. Add JSON-LD Article schema after Open Graph (before <!-- Google Fonts -->)
    jsonld_article = """    <!-- JSON-LD Structured Data: Article -->
    <script type="application/ld+json">
    {
        "@context": "https://schema.org",
        "@type": "Article",
        "headline": "%s",
        "description": "%s",
        "image": "%s",
        "datePublished": "%s",
        "author": {"@type": "Person", "name": "%s"},
        "publisher": {
            "@type": "Organization",
            "name": "DomanID",
            "logo": {"@type": "ImageObject", "url": "https://domanid.com/og-image.png"}
        },
        "mainEntityOfPage": {"@type": "WebPage", "@id": "https://domanid.com/articles/%s.html"}
    }
    </script>

    <!-- JSON-LD Structured Data: Breadcrumbs -->
    <script type="application/ld+json">
    {
        "@context": "https://schema.org",
        "@type": "BreadcrumbList",
        "itemListElement": [
            {"@type": "ListItem", "position": 1, "name": "Home", "item": "https://domanid.com/"},
            {"@type": "ListItem", "position": 2, "name": "Blog", "item": "https://domanid.com/articles/index.html"},
            {"@type": "ListItem", "position": 3, "name": "%s"}
        ]
    }
    </script>
    """ % (title, excerpt, image, date_iso, author, slug, title)

    if "JSON-LD Structured Data: Article" not in html:
        # Insert after the last Open Graph tag (before preconnect or Google Fonts)
        html = html.replace(
            '<meta name="twitter:description"',
            jsonld_article.strip() + '\n    <meta name="twitter:description"'
        )

    # 5. Add new CSS for breadcrumbs, reading time, related articles
    new_css = """        .breadcrumbs {
            display: flex;
            justify-content: center;
            gap: 8px;
            font-size: 0.85rem;
            color: var(--text-muted);
            margin-bottom: 20px;
            flex-wrap: wrap;
        }
        .breadcrumbs a {
            color: var(--accent-1);
            text-decoration: none;
        }
        .breadcrumbs a:hover {
            text-decoration: underline;
        }
        .breadcrumbs .sep {
            color: rgba(255,255,255,0.2);
        }
        .reading-time {
            color: var(--text-muted);
            font-size: 0.85rem;
            margin-top: -10px;
            margin-bottom: 20px;
        }
        .related-articles {
            margin-top: 60px;
            padding-top: 40px;
            border-top: 1px solid var(--glass-border);
        }
        .related-articles h3 {
            font-family: 'Outfit', sans-serif;
            font-size: 1.6rem;
            margin-bottom: 24px;
            text-align: center;
        }
        .related-grid {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(260px, 1fr));
            gap: 20px;
        }
        .related-card {
            padding: 20px;
            transition: transform 0.3s ease, border-color 0.3s ease;
        }
        .related-card:hover {
            transform: translateY(-3px);
            border-color: rgba(255,255,255,0.15);
        }
        .related-card .article-meta {
            font-size: 0.8rem;
            margin-bottom: 6px;
        }
        .related-card h4 {
            font-family: 'Outfit', sans-serif;
            font-size: 1.1rem;
            font-weight: 700;
            line-height: 1.3;
        }
        .related-card h4 a {
            color: var(--text-pure);
            text-decoration: none;
        }
        .related-card h4 a:hover {
            color: var(--accent-1);
        }
"""

    if ".breadcrumbs" not in html:
        # Insert before the first media query
        html = html.replace(
            "@media (max-width: 768px)",
            new_css + "\n        @media (max-width: 768px)"
        )

    # 6. Add related-grid to media queries for responsive
    if "related-grid" not in html:
        html = html.replace(
            ".article-body {" + " ",
            ".related-grid { grid-template-columns: 1fr !important; }\n            .article-body {"
        )

    # 7. Add breadcrumb HTML before article-header
    breadcrumb_html = """            <nav class="breadcrumbs" aria-label="Breadcrumb">
                <a href="../index.html">Home</a>
                <span class="sep">&#8250;</span>
                <a href="index.html">Blog</a>
                <span class="sep">&#8250;</span>
                <span>%s</span>
            </nav>
""" % title

    if 'class="breadcrumbs"' not in html:
        html = html.replace(
            '<div class="article-header">',
            breadcrumb_html + '            <div class="article-header">'
        )

    # 8. Add reading time after author line
    reading_html = '                <p class="reading-time">%d min read</p>\n' % rt
    if 'reading-time' not in html:
        html = html.replace(
            '<p style="color:var(--text-muted)">By ' + author + '</p>',
            '<p style="color:var(--text-muted)">By ' + author + '</p>\n' + reading_html
        )

    # 9. Add related articles before the CTA section
    related = related_html(slug, all_articles)
    if related and "related-articles" not in html:
        html = html.replace(
            '<div style="margin-top: 50px; padding: 30px; background: rgba(0, 252, 254, 0.05);',
            related + '\n\n            <div style="margin-top: 50px; padding: 30px; background: rgba(37, 99, 235, 0.05);'
        )
        # Also fix old CTA background color
        html = html.replace(
            'background: rgba(0, 252, 254, 0.05);',
            'background: rgba(37, 99, 235, 0.05);'
        )

    # 10. Add loading="lazy" to article image
    html = html.replace(
        '<img src="' + image + '" alt="' + title + '" style="width: 100%; height: 100%; object-fit: cover;">',
        '<img src="' + image + '" alt="' + title + '" style="width: 100%; height: 100%; object-fit: cover;" loading="lazy">'
    )

    with open(filepath, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"Migrated: {filepath}")

def main():
    rows = fetch_csv()
    if not rows:
        print("No CSV data found.")
        return

    article_map = build_article_map(rows)
    all_slugs = sorted(article_map.keys())

    # Build all_articles list for related links
    all_articles = []
    for slug in all_slugs:
        m = article_map[slug]
        all_articles.append({
            "slug": m["slug"], "title": m["title"], "category": m["category"],
            "date": m["date"], "excerpt": m["excerpt"]
        })

    # Sort same as blog_generator: latest first for related articles
    all_articles.reverse()

    count = 0
    for slug in all_slugs:
        filepath = os.path.join(ARTICLES_DIR, f"{slug}.html")
        if os.path.exists(filepath):
            migrate_article(filepath, article_map[slug], all_articles)
            count += 1
        else:
            print(f"File not found: {filepath}")

    print(f"\nDone! Migrated {count} articles.")

if __name__ == "__main__":
    main()
