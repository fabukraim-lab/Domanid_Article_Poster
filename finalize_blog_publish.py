from pathlib import Path
import json
import os
import sys
import time
import requests

APPS_SCRIPT_URL = (
    "https://script.google.com/macros/s/"
    "AKfycbwwn9irH9UZbvX6b25lctzMIPeorl2926QLUfnwO_SxrOy3CnMCG5gtEH-OpSmjhpS5kw/exec"
)

PUBLISH_STATE_FILE = Path(
    os.environ.get(
        "DOMANID_PUBLISH_STATE",
        "/tmp/domanid_publish.json",
    )
)

TELEGRAM_BOT_TOKEN = os.environ.get(
    "TELEGRAM_BOT_TOKEN",
    "",
).strip()

TELEGRAM_CHAT_ID = os.environ.get(
    "TELEGRAM_CHAT_ID",
    "",
).strip()


def send_telegram(text, attempts=3, delay=5):
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("[INFO] Telegram credentials not configured.")
        return False

    url = (
        f"https://api.telegram.org/"
        f"bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    )

    for attempt in range(1, attempts + 1):
        try:
            response = requests.post(
                url,
                json={
                    "chat_id": TELEGRAM_CHAT_ID,
                    "text": text,
                    "parse_mode": "HTML",
                },
                timeout=30,
            )

            response.raise_for_status()

            print("[PASS] Telegram notification sent.")
            return True

        except requests.RequestException as exc:
            print(
                f"[WARN] Telegram attempt "
                f"{attempt}/{attempts} failed: {exc}"
            )

            if attempt < attempts:
                time.sleep(delay)

    print(
        "[WARN] Article publication succeeded, "
        "but Telegram notification could not be delivered."
    )

    return False


def wait_until_public(url, attempts=30, delay=10):
    print(f"[INFO] Waiting for public deployment: {url}")

    for attempt in range(1, attempts + 1):
        try:
            response = requests.get(
                url,
                timeout=20,
                allow_redirects=True,
            )

            print(
                f"[CHECK {attempt}/{attempts}] "
                f"HTTP {response.status_code}"
            )

            if response.status_code == 200:
                print("[PASS] Public article returned HTTP 200.")
                return True

        except requests.RequestException as exc:
            print(
                f"[CHECK {attempt}/{attempts}] "
                f"{type(exc).__name__}"
            )

        if attempt < attempts:
            time.sleep(delay)

    return False


def update_sheet_status(sheet_row):
    response = requests.get(
        APPS_SCRIPT_URL,
        params={
            "row": sheet_row,
            "status": "posted",
        },
        timeout=30,
    )

    response.raise_for_status()

    print(
        "[INFO] Google Sheet response:",
        response.text[:500],
    )

    return response


def main():
    if not PUBLISH_STATE_FILE.exists():
        print(
            "[INFO] No article publication is awaiting finalization."
        )
        return 0

    state = json.loads(
        PUBLISH_STATE_FILE.read_text(
            encoding="utf-8",
        )
    )

    required = [
        "title",
        "slug",
        "date",
        "category",
        "sheet_row",
    ]

    missing = [
        key
        for key in required
        if not state.get(key)
    ]

    if missing:
        raise RuntimeError(
            "Invalid publication state. Missing: "
            + ", ".join(missing)
        )

    slug = state["slug"]
    public_url = (
        f"https://domanid.com/articles/{slug}.html"
    )

    if not wait_until_public(public_url):
        raise RuntimeError(
            "Article was pushed but did not become publicly "
            f"available with HTTP 200: {public_url}"
        )

    # Only after the public page is confirmed.
    update_sheet_status(
        state["sheet_row"]
    )

    message = (
        "✅ <b>Article Published Successfully</b>\n\n"
        f"📄 <b>{state['title']}</b>\n"
        f"📅 {state['date']}  |  📂 {state['category']}\n"
        f"🔗 {public_url}"
    )

    send_telegram(message)

    print(
        "[PASS] Publication finalized: "
        f"{slug}"
    )

    try:
        PUBLISH_STATE_FILE.unlink()
    except FileNotFoundError:
        pass

    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())

    except Exception as exc:
        print(
            "[ERROR] Publication finalization failed:",
            exc,
        )

        try:
            send_telegram(
                "❌ <b>DomanID publication finalization failed</b>\n\n"
                f"<code>{str(exc)[:1500]}</code>"
            )
        except Exception as telegram_exc:
            print(
                "[WARN] Failure notification could not be sent:",
                telegram_exc,
            )

        sys.exit(1)
