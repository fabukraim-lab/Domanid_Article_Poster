"""Migrate remaining articles not in CSV by parsing existing HTML."""
import os
import re

ARTICLES_DIR = "articles"

def extract_meta(filepath):
    with open(filepath, "r", encoding="utf-8", errors="replace") as f:
        html = f.read()

    title = "Article"
    m = re.search(r'<title>(.*?)\s*-\s*DomanID</title>', html)
    if m: title = m.group(1)

    excerpt = ""
    m = re.search(r'<meta name="description" content="(.*?)">', html)
    if m: excerpt = m.group(1)

    date = "2026-01-01"
    m = re.search(r'<span class="article-meta">.*?\|.*?(\d{4}-\d{2}-\d{2})</span>', html)
    if m: date = m.group(1)

    author = "DomanID"
    m = re.search(r'By\s+(.*?)</p>', html)
    if m: author = m.group(1).strip()

    slug = os.path.splitext(os.path.basename(filepath))[0]

    content_text = ""
    m = re.search(r'<div class="article-body">\s*(.*?)\s*</div>', html, re.DOTALL)
    if m:
        content_text = re.sub(r'<[^>]+>', '', m.group(1))
        content_text = re.sub(r'\s+', ' ', content_text).strip()

    image = "https://images.pexels.com/photos/160107/pexels-photo-160107.jpeg"
    m = re.search(r'<img\s+src="(.*?)"', html)
    if m: image = m.group(1)

    return {"title": title, "slug": slug, "date": date, "author": author,
            "excerpt": excerpt, "image": image, "raw": html, "content_text": content_text}

def reading_time(text):
    return max(1, round(len(text.split()) / 200))

def main():
    articles = [f for f in os.listdir(ARTICLES_DIR)
                if f.endswith(".html") and f != "index.html"]
    articles.sort()

    # First pass: extract all metadata for related articles
    all_meta = {}
    for art in articles:
        fp = os.path.join(ARTICLES_DIR, art)
        meta = extract_meta(fp)
        all_meta[art] = meta

    # Build related articles list
    all_list = [{"slug": m["slug"], "title": m["title"], "category": "Domain Investing"}
                for m in all_meta.values()]
    all_list.reverse()  # latest first

    def related_html(slug, articles_list, max_count=3):
        others = [a for a in articles_list if a["slug"] != slug]
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

    count = 0
    for art in articles:
        fp = os.path.join(ARTICLES_DIR, art)
        meta = all_meta[art]
        html = meta["raw"]
        slug = meta["slug"]
        title = meta["title"]
        excerpt = meta["excerpt"]
        image = meta["image"]
        date = meta["date"]
        author = meta["author"]
        rt = reading_time(meta["content_text"])

        date_iso = date
        try:
            parts = date.split("-")
            if len(parts) == 3:
                date_iso = f"{parts[0]}-{parts[1]}-{parts[2]}"
        except:
            pass

        changes = 0

        # Canonical
        if 'rel="canonical"' not in html:
            html = html.replace(
                '<meta name="viewport"',
                f'<meta name="viewport"\n    <link rel="canonical" href="https://domanid.com/articles/{slug}.html">\n    <meta name="viewport"'
            )
            changes += 1

        # Preconnect
        if "Preconnect for Performance" not in html:
            preconnect = """    <!-- Preconnect for Performance -->
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link rel="preconnect" href="https://www.googletagmanager.com">
    <link rel="preconnect" href="https://pagead2.googlesyndication.com">
    """
            html = html.replace("<!-- Google Fonts -->", preconnect + "    <!-- Google Fonts -->")
            changes += 1

        # Open Graph additions
        if 'og:site_name' not in html:
            html = html.replace(
                '<meta property="og:image"',
                '<meta property="og:site_name" content="DomanID">\n    <meta name="twitter:card" content="summary_large_image">\n    <meta property="og:image"'
            )
            changes += 1

        # JSON-LD
        if "JSON-LD Structured Data: Article" not in html:
            jsonld = f"""    <!-- JSON-LD Structured Data: Article -->
    <script type="application/ld+json">
    {{
        "@context": "https://schema.org",
        "@type": "Article",
        "headline": "{title}",
        "description": "{excerpt}",
        "image": "{image}",
        "datePublished": "{date_iso}",
        "author": {{"@type": "Person", "name": "{author}"}},
        "publisher": {{
            "@type": "Organization",
            "name": "DomanID",
            "logo": {{"@type": "ImageObject", "url": "https://domanid.com/og-image.png"}}
        }},
        "mainEntityOfPage": {{"@type": "WebPage", "@id": "https://domanid.com/articles/{slug}.html"}}
    }}
    </script>

    <!-- JSON-LD Structured Data: Breadcrumbs -->
    <script type="application/ld+json">
    {{
        "@context": "https://schema.org",
        "@type": "BreadcrumbList",
        "itemListElement": [
            {{"@type": "ListItem", "position": 1, "name": "Home", "item": "https://domanid.com/"}},
            {{"@type": "ListItem", "position": 2, "name": "Blog", "item": "https://domanid.com/articles/index.html"}},
            {{"@type": "ListItem", "position": 3, "name": "{title}"}}
        ]
    }}
    </script>
    """
            # Insert after the last OG tag
            html = html.replace(
                '<meta property="og:site_name"',
                jsonld.strip() + '\n    <meta property="og:site_name"'
            )
            changes += 1

        # CSS for breadcrumbs etc.
        if ".breadcrumbs" not in html:
            new_css = """        .breadcrumbs {
            display: flex; justify-content: center; gap: 8px;
            font-size: 0.85rem; color: var(--text-muted);
            margin-bottom: 20px; flex-wrap: wrap;
        }
        .breadcrumbs a { color: var(--accent-1); text-decoration: none; }
        .breadcrumbs a:hover { text-decoration: underline; }
        .breadcrumbs .sep { color: rgba(255,255,255,0.2); }
        .reading-time { color: var(--text-muted); font-size: 0.85rem; margin-top: -10px; margin-bottom: 20px; }
        .related-articles { margin-top: 60px; padding-top: 40px; border-top: 1px solid var(--glass-border); }
        .related-articles h3 { font-family: 'Outfit', sans-serif; font-size: 1.6rem; margin-bottom: 24px; text-align: center; }
        .related-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(260px, 1fr)); gap: 20px; }
        .related-card { padding: 20px; transition: transform 0.3s ease, border-color 0.3s ease; }
        .related-card:hover { transform: translateY(-3px); border-color: rgba(255,255,255,0.15); }
        .related-card .article-meta { font-size: 0.8rem; margin-bottom: 6px; }
        .related-card h4 { font-family: 'Outfit', sans-serif; font-size: 1.1rem; font-weight: 700; line-height: 1.3; }
        .related-card h4 a { color: var(--text-pure); text-decoration: none; }
        .related-card h4 a:hover { color: var(--accent-1); }
"""
            html = html.replace(
                "@media (max-width: 768px)",
                new_css + "\n        @media (max-width: 768px)"
            )
            changes += 1

        # Breadcrumb HTML
        if 'class="breadcrumbs"' not in html:
            breadcrumb = f"""            <nav class="breadcrumbs" aria-label="Breadcrumb">
                <a href="../index.html">Home</a>
                <span class="sep">&#8250;</span>
                <a href="index.html">Blog</a>
                <span class="sep">&#8250;</span>
                <span>{title}</span>
            </nav>
"""
            html = html.replace(
                '<div class="article-header">',
                breadcrumb + '            <div class="article-header">'
            )
            changes += 1

        # Reading time
        if 'reading-time' not in html:
            reading_html = f'                <p class="reading-time">{rt} min read</p>\n'
            html = html.replace(
                f'<p style="color:var(--text-muted)">By {author}</p>',
                f'<p style="color:var(--text-muted)">By {author}</p>\n' + reading_html
            )
            changes += 1

        # Related articles & CTA fix
        if "related-articles" not in html:
            related = related_html(slug, all_list)
            if related:
                html = html.replace(
                    'background: rgba(0, 252, 254, 0.05)',
                    'background: rgba(37, 99, 235, 0.05)'
                )
                html = html.replace(
                    '<div style="margin-top: 50px; padding: 30px; background: rgba(37, 99, 235, 0.05);',
                    related + '\n\n            <div style="margin-top: 50px; padding: 30px; background: rgba(37, 99, 235, 0.05);'
                )
                changes += 1

        # Lazy loading
        if 'loading="lazy"' not in html:
            html = html.replace(
                '<img src="' + image + '"',
                '<img src="' + image + '" loading="lazy"'
            )
            changes += 1

        if changes > 0:
            with open(fp, "w", encoding="utf-8") as f:
                f.write(html)
            print(f"Migrated: {art} ({changes} changes)")
            count += 1
        else:
            print(f"Skipped: {art} (no changes needed)")

    print(f"\nDone! Updated {count} remaining articles.")

if __name__ == "__main__":
    main()
