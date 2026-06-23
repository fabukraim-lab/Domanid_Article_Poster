import csv
import os
import requests
import re
import io
import traceback
import sys
import json
from datetime import datetime

# --- CONFIGURATION ---
BLOG_CSV_URL = "https://docs.google.com/spreadsheets/d/1PNIvLQsoyh6ssc5wEvtmB4K8eT9tyNmngeyRpa1rFbY/export?format=csv"
APPS_SCRIPT_URL = "https://script.google.com/macros/s/AKfycbwwn9irH9UZbvX6b25lctzMIPeorl2926QLUfnwO_SxrOy3CnMCG5gtEH-OpSmjhpS5kw/exec"
LOCAL_CSV_PATH = "blog_content.csv"

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "").strip() if os.environ.get("GEMINI_API_KEY") else None
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip() or None
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "").strip() or None

TEMPLATE_PATH = "article_template.html"
ARTICLES_DIR = "articles"
INDEX_PATH = os.path.join(ARTICLES_DIR, "index.html")

def fetch_csv_data(url):
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        print(f"Connecting to: {url}")
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        decoded_content = response.content.decode('utf-8')
        
        # Use StringIO to handle multi-line fields correctly
        f = io.StringIO(decoded_content)
        cr = csv.reader(f, delimiter=',')
        my_list = list(cr)
        print(f"Successfully fetched {len(my_list)} rows from CSV.")
        return my_list
    except Exception as e:
        print(f"Error fetching CSV: {e}")
        return None

def reading_time(text):
    words = len(text.split())
    mins = max(1, round(words / 200))
    return f"{mins} min read"

def to_iso_date(date_str):
    try:
        parts = date_str.split("-")
        if len(parts) == 3:
            return f"{parts[0]}-{parts[1]}-{parts[2]}"
        return date_str
    except:
        return date_str

def related_articles_html(current_slug, all_articles, max_count=3):
    others = [a for a in all_articles if a["slug"] != current_slug]
    selected = others[:max_count]
    if not selected:
        return ""
    cards = ""
    for art in selected:
        cards += f"""
            <a href="{art['slug']}.html" class="glass-panel related-card" style="text-decoration:none; display:block;">
                <span class="article-meta">{art['category']}</span>
                <h4>{art['title']}</h4>
            </a>"""
    return f"""
        <div class="related-articles">
            <h3>Continue Reading</h3>
            <div class="related-grid">{cards}
            </div>
        </div>"""

def generate_article(row, template, all_articles=None):
    # Mapping: Title, Slug, Category, Date, Author, Excerpt, FullContent, Keywords, Image, Status
    if len(row) < 8:
        print(f"Skipping row due to insufficient columns: {row}")
        return None
    
    title, slug, category, date, author, excerpt, content, keywords = row[:8]
    
    image = "https://images.pexels.com/photos/160107/pexels-photo-160107.jpeg" # Default
    if len(row) >= 9 and row[8].strip():
        image = row[8].strip()

    rt = reading_time(content)
    date_iso = to_iso_date(date)
    related = related_articles_html(slug, all_articles) if all_articles else ""

    page_content = template
    page_content = page_content.replace("{{TITLE}}", title)
    page_content = page_content.replace("{{SLUG}}", slug)
    page_content = page_content.replace("{{CATEGORY}}", category)
    page_content = page_content.replace("{{DATE}}", date)
    page_content = page_content.replace("{{DATE_ISO}}", date_iso)
    page_content = page_content.replace("{{AUTHOR}}", author)
    page_content = page_content.replace("{{EXCERPT}}", excerpt)
    page_content = page_content.replace("{{CONTENT}}", content)
    page_content = page_content.replace("{{KEYWORDS}}", keywords)
    page_content = page_content.replace("{{IMAGE}}", image)
    page_content = page_content.replace("{{READING_TIME}}", rt)
    page_content = page_content.replace("{{RELATED_ARTICLES}}", related)

    filename = f"{slug}.html"
    filepath = os.path.join(ARTICLES_DIR, filename)

    with open(filepath, "w", encoding="utf-8") as f:
        f.write(page_content)
    
    print(f"Generated: {filepath}")
    return {"title": title, "slug": slug, "date": date, "excerpt": excerpt, "category": category}

def send_telegram_message(text):
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        return
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        payload = {"chat_id": TELEGRAM_CHAT_ID, "text": text, "parse_mode": "HTML"}
        resp = requests.post(url, json=payload, timeout=15)
        if resp.status_code == 200:
            print("Telegram notification sent.")
        else:
            print(f"Telegram send failed: {resp.text}")
    except Exception as e:
        print(f"Telegram error: {e}")

SITEMAP_PATH = "sitemap.xml"

def generate_sitemap(articles):
    base_url = "https://domanid.com"
    static_pages = [
        ("", 1.0, "weekly"),
        ("about.html", 0.8, "monthly"),
        ("contact.html", 0.7, "monthly"),
        ("terms.html", 0.3, "yearly"),
        ("privacy.html", 0.3, "yearly"),
        ("articles/index.html", 0.9, "daily"),
    ]
    lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">',
    ]
    for path, priority, changefreq in static_pages:
        lines.append(f"  <url>")
        lines.append(f"    <loc>{base_url}/{path}</loc>")
        lines.append(f"    <priority>{priority}</priority>")
        if changefreq:
            lines.append(f"    <changefreq>{changefreq}</changefreq>")
        lines.append(f"  </url>")
    for art in articles:
        lines.append(f"  <url>")
        lines.append(f"    <loc>{base_url}/articles/{art['slug']}.html</loc>")
        lines.append(f"    <priority>0.6</priority>")
        lines.append(f"  </url>")
    lines.append("</urlset>")
    with open(SITEMAP_PATH, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    print(f"Generated {SITEMAP_PATH}")

def update_index(articles):
    if not os.path.exists(INDEX_PATH):
        print("articles/index.html not found.")
        return

    with open(INDEX_PATH, "r", encoding="utf-8", errors="replace") as f:
        content = f.read()

    grid_html = ""
    for art in articles:
        grid_html += f"""
        <article class="glass-panel">
            <div class="article-content">
                <span class="article-meta">{art['category']} | {art['date']}</span>
                <h2 class="article-title"><a href="{art['slug']}.html">{art['title']}</a></h2>
                <p class="article-excerpt">{art['excerpt']}</p>
            </div>
        </article>"""

    pattern = re.compile(r"<!-- START_ARTICLES -->.*?<!-- END_ARTICLES -->", re.DOTALL)
    new_content = pattern.sub(f"<!-- START_ARTICLES -->\n{grid_html}\n<!-- END_ARTICLES -->", content)

    with open(INDEX_PATH, "w", encoding="utf-8") as f:
        f.write(new_content)
    print("Updated articles/index.html")

GENERATE_RSS = True

def generate_rss(articles):
    if not GENERATE_RSS:
        return
    items = ""
    for art in articles:
        items += f"""    <item>
        <title>{art['title']}</title>
        <link>https://domanid.com/articles/{art['slug']}.html</link>
        <description><![CDATA[{art['excerpt']}]]></description>
        <guid>https://domanid.com/articles/{art['slug']}.html</guid>
    </item>
"""
    rss = f"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom" xmlns:content="http://purl.org/rss/1.0/modules/content/">
  <channel>
    <title>DomanID Blog - Domain Investing Insights</title>
    <link>https://domanid.com/articles/index.html</link>
    <description>Expert insights on domain investing, premium domain strategies, SEO, and digital asset management.</description>
    <language>en</language>
    <atom:link href="https://domanid.com/rss.xml" rel="self" type="application/rss+xml"/>
{items}  </channel>
</rss>"""
    with open("rss.xml", "w", encoding="utf-8") as f:
        f.write(rss)
    print("Generated rss.xml")

def inject_related_into_article(slug, all_articles):
    filepath = os.path.join(ARTICLES_DIR, f"{slug}.html")
    if not os.path.exists(filepath):
        return
    with open(filepath, "r", encoding="utf-8", errors="replace") as f:
        content = f.read()
    related = related_articles_html(slug, all_articles)
    content = content.replace("{{RELATED_ARTICLES}}", related)
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(content)

def main():
    try:
        if not os.path.exists(ARTICLES_DIR):
            os.makedirs(ARTICLES_DIR)

        if not os.path.exists(TEMPLATE_PATH):
            print(f"Error: {TEMPLATE_PATH} not found.")
            return

        with open(TEMPLATE_PATH, "r", encoding="utf-8", errors="replace") as f:
            template = f.read()

        print("Fetching blog data...")
        csv_data = None
        if BLOG_CSV_URL:
            csv_data = fetch_csv_data(BLOG_CSV_URL)
        
        if not csv_data:
            if os.path.exists(LOCAL_CSV_PATH):
                with open(LOCAL_CSV_PATH, "r", encoding="utf-8", errors="replace") as f:
                    cr = csv.reader(f)
                    csv_data = list(cr)
            else:
                print("Error: No blog source found.")
                return

        csv_rows = list(csv_data)
        articles_data = []
        found_any = False
        sheet_row = -1

        # 0. Build full posted articles list FIRST (for related articles context)
        all_posted_articles = []
        for i, row in enumerate(csv_rows):
            if i == 0: continue
            status = ""
            if len(row) >= 10:
                status = row[9].strip().lower()
            if status == "posted" and len(row) >= 8:
                expected_filepath = os.path.join(ARTICLES_DIR, f"{row[1]}.html")
                if os.path.exists(expected_filepath):
                    all_posted_articles.append({
                        "title": row[0], "slug": row[1], "category": row[2],
                        "date": row[3], "excerpt": row[5]
                    })
        
        # 1. Post ONE pending article (with full context for related articles)
        for i, row in enumerate(csv_rows):
            if i == 0: continue
            status = "pending"
            if len(row) >= 10:
                status = row[9].strip().lower()
            
            if status == "pending":
                print(f"Found pending article: {row[0]}")
                art = generate_article(row, template, all_posted_articles)
                if art:
                    articles_data.append(art)
                    all_posted_articles.append(art)
                    
                    if APPS_SCRIPT_URL:
                        sheet_row = i + 1
                        try:
                            resp = requests.get(f"{APPS_SCRIPT_URL}?row={sheet_row}&status=posted", timeout=30)
                            print(f"Status update response: {resp.text}")
                        except Exception as e:
                            print(f"Error updating status: {e}")
                    found_any = True
                    break

        # 2. Rebuild index (latest first)
        print("Rebuilding articles/index.html...")
        if not found_any:
            # Rebuild with current posted list (no new article)
            all_posted_articles = []
            for i, row in enumerate(csv_rows):
                if i == 0: continue
                status = ""
                if len(row) >= 10:
                    status = row[9].strip().lower()
                if status == "posted" and len(row) >= 8:
                    expected_filepath = os.path.join(ARTICLES_DIR, f"{row[1]}.html")
                    if os.path.exists(expected_filepath):
                        all_posted_articles.append({
                            "title": row[0], "slug": row[1], "category": row[2],
                            "date": row[3], "excerpt": row[5]
                        })
        
        if all_posted_articles:
            all_posted_articles.reverse() # SORT: LATEST FIRST
            update_index(all_posted_articles)
            generate_sitemap(all_posted_articles)
            generate_rss(all_posted_articles)

        # 3. Re-inject related articles into the new article with full list
        if articles_data:
            new_art = articles_data[-1]
            inject_related_into_article(new_art["slug"], all_posted_articles)

        if articles_data:
            art = articles_data[-1]
            msg = (
                f"✅ <b>Article Published Successfully</b>\n\n"
                f"📄 <b>{art['title']}</b>\n"
                f"📅 {art['date']}  |  📂 {art['category']}\n"
                f"🔗 https://domanid.com/articles/{art['slug']}.html"
            )
            send_telegram_message(msg)
        else:
            send_telegram_message("✅ <b>Blog Check Complete</b>\nNo pending articles to publish.")

    except Exception as e:
        print("--- CRITICAL ERROR ---")
        traceback.print_exc()
        error_msg = f"❌ <b>Blog Publisher Failed</b>\n\n<code>{traceback.format_exc()[:2000]}</code>"
        send_telegram_message(error_msg)
        sys.exit(1)

if __name__ == "__main__":
    main()
