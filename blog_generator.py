import csv
import os
import requests
import re
import io
import traceback
import sys
import json
import sys

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

def generate_article(row, template):
    # Mapping: Title, Slug, Category, Date, Author, Excerpt, FullContent, Keywords, Image, Status
    if len(row) < 8:
        print(f"Skipping row due to insufficient columns: {row}")
        return None
    
    title, slug, category, date, author, excerpt, content, keywords = row[:8]
    
    image = "https://images.pexels.com/photos/160107/pexels-photo-160107.jpeg" # Default
    if len(row) >= 9 and row[8].strip():
        image = row[8].strip()

    page_content = template
    page_content = page_content.replace("{{TITLE}}", title)
    page_content = page_content.replace("{{SLUG}}", slug)
    page_content = page_content.replace("{{CATEGORY}}", category)
    page_content = page_content.replace("{{DATE}}", date)
    page_content = page_content.replace("{{AUTHOR}}", author)
    page_content = page_content.replace("{{EXCERPT}}", excerpt)
    page_content = page_content.replace("{{CONTENT}}", content)
    page_content = page_content.replace("{{KEYWORDS}}", keywords)
    page_content = page_content.replace("{{IMAGE}}", image)

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
        
        # 1. Post ONE pending article
        for i, row in enumerate(csv_rows):
            if i == 0: continue
            status = "pending"
            if len(row) >= 10:
                status = row[9].strip().lower()
            
            if status == "pending":
                print(f"Found pending article: {row[0]}")
                art = generate_article(row, template)
                if art:
                    articles_data.append(art)
                    
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
        all_posted_articles = []
        for i, row in enumerate(csv_rows):
            if i == 0: continue
            status = ""
            if len(row) >= 10:
                status = row[9].strip().lower()
            
            if (found_any and i == (sheet_row - 1)) or status == "posted":
                if len(row) >= 8:
                    expected_filepath = os.path.join(ARTICLES_DIR, f"{row[1]}.html")
                    if os.path.exists(expected_filepath):
                        all_posted_articles.append({
                            "title": row[0], "slug": row[1], "category": row[2], 
                            "date": row[3], "excerpt": row[5]
                        })
                    else:
                        print(f"Skipping {row[1]} from index: HTML file was manually deleted.")
        
        if all_posted_articles:
            all_posted_articles.reverse() # SORT: LATEST FIRST
            update_index(all_posted_articles)

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
