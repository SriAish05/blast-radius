"""
Unit & Integration Test for Crawler (crawler/test_crawl.py)
-----------------------------------------------------------
Tests the crawler against a local mock server simulating:
1. SmileCare: direct chat-widget.js -> helper.js
2. SmartMart: tag-loader.js -> analytics.js & chat-widget.js -> helper.js
3. Cafe: no CDN scripts (safe control site)
4. SRI detection: script with integrity attribute

Verifies the exact criteria in Section 9.1 and DONE WHEN instructions.
"""

import asyncio
import hashlib
import http.server
import json
import socketserver
import threading
from pathlib import Path
from playwright.async_api import async_playwright

from crawl import crawl_page

PORT = 8899
BASE_URL = f"http://127.0.0.1:{PORT}"

TAG_LOADER_JS = f"""
const s1 = document.createElement('script');
s1.src = '{BASE_URL}/cdn/analytics.js';
document.head.appendChild(s1);

const s2 = document.createElement('script');
s2.src = '{BASE_URL}/cdn/chat-widget.js';
document.head.appendChild(s2);
"""

CHAT_WIDGET_JS = f"""
const helper = document.createElement('script');
helper.src = '{BASE_URL}/cdn/helper.js';
document.head.appendChild(helper);
"""

ANALYTICS_JS = "console.log('analytics loaded');"
HELPER_JS = "console.log('helper loaded');"
SAFE_JS = "console.log('safe local script');"

SMILECARE_HTML = f"""<!doctype html>
<html>
<head>
  <title>SmileCare</title>
  <script src="{BASE_URL}/cdn/chat-widget.js"></script>
</head>
<body><h1>SmileCare Dental</h1></body>
</html>"""

SMARTMART_HTML = f"""<!doctype html>
<html>
<head>
  <title>SmartMart</title>
  <script src="{BASE_URL}/cdn/tag-loader.js"></script>
</head>
<body><h1>SmartMart Store</h1></body>
</html>"""

CAFE_HTML = f"""<!doctype html>
<html>
<head>
  <title>Cafe</title>
  <script src="{BASE_URL}/safe/local.js"></script>
</head>
<body><h1>Cafe Local</h1></body>
</html>"""

SRI_TEST_HTML = f"""<!doctype html>
<html>
<head>
  <title>SRI Test</title>
  <script src="{BASE_URL}/cdn/analytics.js" integrity="sha384-mockhash"></script>
</head>
<body><h1>SRI Test</h1></body>
</html>"""


class MockHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        routes = {
            "/cdn/tag-loader.js": ("application/javascript", TAG_LOADER_JS.encode()),
            "/cdn/chat-widget.js": ("application/javascript", CHAT_WIDGET_JS.encode()),
            "/cdn/analytics.js": ("application/javascript", ANALYTICS_JS.encode()),
            "/cdn/helper.js": ("application/javascript", HELPER_JS.encode()),
            "/safe/local.js": ("application/javascript", SAFE_JS.encode()),
            "/smilecare/": ("text/html", SMILECARE_HTML.encode()),
            "/smartmart/": ("text/html", SMARTMART_HTML.encode()),
            "/cafe/": ("text/html", CAFE_HTML.encode()),
            "/sri/": ("text/html", SRI_TEST_HTML.encode()),
        }

        path = self.path.split("?")[0]
        if path in routes:
            content_type, body = routes[path]
            self.send_response(200)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(body)
        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, format, *args):
        # Silence server log spam during test
        pass


def run_server():
    socketserver.TCPServer.allow_reuse_address = True
    with socketserver.TCPServer(("127.0.0.1", PORT), MockHandler) as httpd:
        httpd.serve_forever()


async def run_tests():
    output_dir = Path(__file__).resolve().parent / "test_output"
    output_dir.mkdir(parents=True, exist_ok=True)

    print("\n=======================================================")
    print("RUNNING CRAWLER AUTOMATED TESTS (Local Test Server)")
    print("=======================================================\n")

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context()

        # -----------------------------------------------------------------
        # TEST 1: SmileCare (chat-widget.js -> helper.js)
        # -----------------------------------------------------------------
        print("Test 1: SmileCare Dental...")
        smilecare_res = await crawl_page(
            context,
            f"{BASE_URL}/smilecare",
            f"{BASE_URL}/smilecare/",
            output_dir,
        )

        scripts_by_url = {s["url"]: s for s in smilecare_res["scripts"]}
        chat_url = f"{BASE_URL}/cdn/chat-widget.js"
        helper_url = f"{BASE_URL}/cdn/helper.js"

        assert chat_url in scripts_by_url, f"Missing chat-widget.js in {scripts_by_url.keys()}"
        assert helper_url in scripts_by_url, f"Missing helper.js in {scripts_by_url.keys()}"
        assert scripts_by_url[chat_url]["loaded_by"] == "page", f"Expected page, got {scripts_by_url[chat_url]['loaded_by']}"
        assert scripts_by_url[helper_url]["loaded_by"] == chat_url, f"Expected {chat_url}, got {scripts_by_url[helper_url]['loaded_by']}"
        assert scripts_by_url[chat_url]["sha256"] == hashlib.sha256(CHAT_WIDGET_JS.encode()).hexdigest()
        assert scripts_by_url[helper_url]["sha256"] == hashlib.sha256(HELPER_JS.encode()).hexdigest()
        print("  ✓ SmileCare passed: chat-widget.js loaded by 'page', helper.js loaded by chat-widget.js")

        # -----------------------------------------------------------------
        # TEST 2: SmartMart (tag-loader.js -> analytics.js & chat-widget.js -> helper.js)
        # -----------------------------------------------------------------
        print("Test 2: SmartMart Store...")
        smartmart_res = await crawl_page(
            context,
            f"{BASE_URL}/smartmart",
            f"{BASE_URL}/smartmart/",
            output_dir,
        )

        sm_scripts = {s["url"]: s for s in smartmart_res["scripts"]}
        tag_url = f"{BASE_URL}/cdn/tag-loader.js"
        analytics_url = f"{BASE_URL}/cdn/analytics.js"

        assert tag_url in sm_scripts, "Missing tag-loader.js"
        assert analytics_url in sm_scripts, "Missing analytics.js"
        assert chat_url in sm_scripts, "Missing chat-widget.js"
        assert helper_url in sm_scripts, "Missing helper.js"

        assert sm_scripts[tag_url]["loaded_by"] == "page"
        assert sm_scripts[analytics_url]["loaded_by"] == tag_url
        assert sm_scripts[chat_url]["loaded_by"] == tag_url
        assert sm_scripts[helper_url]["loaded_by"] == chat_url
        print("  ✓ SmartMart passed: tag-loader.js -> analytics.js & chat-widget.js -> helper.js")

        # -----------------------------------------------------------------
        # TEST 3: Cafe (Safe site, no cdn-demo scripts)
        # -----------------------------------------------------------------
        print("Test 3: Cafe (safe site)...")
        cafe_res = await crawl_page(
            context,
            f"{BASE_URL}/cafe",
            f"{BASE_URL}/cafe/",
            output_dir,
        )

        for s in cafe_res["scripts"]:
            assert "/cdn/" not in s["url"], f"Found unexpected CDN script in cafe: {s['url']}"
        print("  ✓ Cafe passed: 0 cdn scripts recorded")

        # -----------------------------------------------------------------
        # TEST 4: SRI Detection
        # -----------------------------------------------------------------
        print("Test 4: Subresource Integrity (has_sri)...")
        sri_res = await crawl_page(
            context,
            f"{BASE_URL}/sri",
            f"{BASE_URL}/sri/",
            output_dir,
        )
        sri_scripts = {s["url"]: s for s in sri_res["scripts"]}
        assert sri_scripts[analytics_url]["has_sri"] is True, "SRI detection failed"
        print("  ✓ SRI passed: script[integrity] correctly detected as has_sri = True")

        await browser.close()

    print("\n=======================================================")
    print("ALL CRAWLER TESTS PASSED PERFECTLY!")
    print("=======================================================\n")


if __name__ == "__main__":
    server_thread = threading.Thread(target=run_server, daemon=True)
    server_thread.start()
    asyncio.run(run_tests())
