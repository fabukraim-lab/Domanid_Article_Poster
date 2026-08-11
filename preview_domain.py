from pathlib import Path
from playwright.sync_api import sync_playwright

URL = "http://localhost:8000/domains/attorneyauto-com/"

OUTPUT_DIR = Path("preview")
OUTPUT_DIR.mkdir(exist_ok=True)

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)

    # Desktop
    desktop = browser.new_page(
        viewport={
            "width": 1440,
            "height": 1000,
        }
    )

    desktop.goto(
        URL,
        wait_until="networkidle",
    )

    desktop.screenshot(
        path=str(
            OUTPUT_DIR / "domain_desktop.png"
        ),
        full_page=True,
    )

    print(
        "[OK] Desktop:",
        OUTPUT_DIR / "domain_desktop.png",
    )

    # Mobile
    mobile = browser.new_page(
        viewport={
            "width": 390,
            "height": 844,
        },
        device_scale_factor=1,
        is_mobile=True,
    )

    mobile.goto(
        URL,
        wait_until="networkidle",
    )

    mobile.screenshot(
        path=str(
            OUTPUT_DIR / "domain_mobile.png"
        ),
        full_page=True,
    )

    print(
        "[OK] Mobile:",
        OUTPUT_DIR / "domain_mobile.png",
    )

    browser.close()

print("[PASS] Domain previews generated.")
