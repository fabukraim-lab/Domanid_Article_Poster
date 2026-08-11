from pathlib import Path
import contextlib
import http.server
import socketserver
import threading
import time

from playwright.sync_api import sync_playwright


PROJECT_ROOT = Path(__file__).resolve().parent
PORT = 8000


class QuietHandler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, format, *args):
        pass


def start_server():
    handler = lambda *args, **kwargs: QuietHandler(
        *args,
        directory=str(PROJECT_ROOT),
        **kwargs,
    )

    server = socketserver.TCPServer(
        ("127.0.0.1", PORT),
        handler,
    )

    thread = threading.Thread(
        target=server.serve_forever,
        daemon=True,
    )

    thread.start()

    return server


def capture(page, name, width, height):
    print(f"[INFO] Capturing {name}: {width}x{height}")

    page.set_viewport_size({
        "width": width,
        "height": height,
    })

    page.goto(
        f"http://127.0.0.1:{PORT}/",
        wait_until="networkidle",
    )

    output = PROJECT_ROOT / f"homepage_preview_{name}.png"

    page.screenshot(
        path=str(output),
        full_page=True,
    )

    print(f"[PASS] {output.name}")


def main():
    server = None

    try:
        print("DomanID Visual Preview")
        print("-" * 50)

        server = start_server()

        print(
            f"[INFO] Local server started on port {PORT}"
        )

        time.sleep(1)

        with sync_playwright() as p:
            browser = p.chromium.launch(
                headless=True
            )

            page = browser.new_page()

            capture(
                page,
                "desktop",
                1440,
                1000,
            )

            capture(
                page,
                "tablet",
                768,
                1000,
            )

            capture(
                page,
                "mobile",
                390,
                844,
            )

            page.set_viewport_size({
                "width": 1440,
                "height": 1000,
            })

            page.goto(
                f"http://127.0.0.1:{PORT}/domains/attorneyauto-com/",
                wait_until="networkidle",
            )

            domain_output = (
                PROJECT_ROOT
                / "domain_preview_attorneyauto.png"
            )

            page.screenshot(
                path=str(domain_output),
                full_page=True,
            )

            print(
                f"[PASS] {domain_output.name}"
            )

            browser.close()

        print()
        print(
            "[PASS] All visual previews generated."
        )

    finally:
        if server:
            server.shutdown()
            server.server_close()

            print(
                "[INFO] Local server stopped."
            )


if __name__ == "__main__":
    main()