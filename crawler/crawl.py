"""
Robot Crawler (crawler/crawl.py)
---------------------------------
Visits configured websites using Playwright with Chrome DevTools Protocol (CDP).
Records every script loaded by the page, who loaded it, its SHA-256 hash,
and whether Subresource Integrity (SRI) is present.

Follows HANDBOOK.md Section 6.2 and Section 9.1 strictly.
No database operations. Saves one JSON file per page to crawler/output/.
"""

import asyncio
import hashlib
import json
import logging
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urljoin, urlparse

from playwright.async_api import async_playwright

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(levelname)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("crawler")


def safe_slug(url: str) -> str:
    """Generate a safe filename slug from a URL."""
    parsed = urlparse(url)
    slug = f"{parsed.netloc}{parsed.path}"
    slug = re.sub(r"[^a-zA-Z0-9_\-]", "_", slug).strip("_")
    return slug or "index"


async def fetch_script_sha256(request_context, url: str) -> str:
    """Download a script's content and compute its SHA-256 hash."""
    try:
        response = await request_context.get(url, timeout=10000)
        if response.status == 200:
            body = await response.body()
            return hashlib.sha256(body).hexdigest()
        logger.warning("Failed to fetch %s (HTTP %s)", url, response.status)
        return ""
    except Exception as e:
        logger.warning("Error fetching %s for hash: %s", url, e)
        return ""


async def crawl_page(context, site_url: str, page_url: str, output_dir: Path) -> dict:
    """
    Crawl a single page using CDP Network.requestWillBeSent to trace script initiators.
    """
    logger.info("Visiting page: %s", page_url)
    found_raw = []

    page = await context.new_page()
    try:
        # 1. Attach CDP session to capture request initiator stack traces
        cdp = await page.context.new_cdp_session(page)
        await cdp.send("Network.enable")

        def on_request(e):
            if e.get("type") != "Script":
                return
            req_url = e.get("request", {}).get("url", "")
            if not req_url or req_url.startswith("data:"):
                return

            ini = e.get("initiator", {})
            by = None
            if ini.get("type") == "script":
                stack = ini.get("stack") or {}
                while stack and not by:  # walk parent stacks too
                    frames = stack.get("callFrames") or []
                    by = next((f.get("url") for f in frames if f.get("url")), None)
                    stack = stack.get("parent")

            # Parser / HTML or self-referential -> "page"
            loaded_by = by if by and by != page_url else "page"
            found_raw.append({"url": req_url, "loaded_by": loaded_by})

        cdp.on("Network.requestWillBeSent", on_request)

        # 2. Navigate to page and wait for network idle + delay for runtime scripts
        try:
            await page.goto(page_url, wait_until="networkidle", timeout=30000)
        except Exception as e:
            logger.warning("Page goto reached timeout or error on %s: %s", page_url, e)

        # Allow runtime-injected scripts (timers, tags) sufficient time to load
        await page.wait_for_timeout(1500)

        # 3. Detect scripts that have Subresource Integrity (has_sri) in the DOM
        try:
            sri_urls = await page.eval_on_selector_all(
                "script[src][integrity]",
                "els => els.map(e => e.src)"
            )
            sri_set = set(sri_urls)
        except Exception as e:
            logger.warning("Could not evaluate SRI scripts on %s: %s", page_url, e)
            sri_set = set()

    finally:
        await page.close()

    # 4. Deduplicate requests while preserving insertion order
    seen = set()
    unique_requests = []
    for item in found_raw:
        key = (item["url"], item["loaded_by"])
        if key not in seen:
            seen.add(key)
            unique_requests.append(item)

    # 5. Fetch bodies and compute sha256 for each unique script
    # Cache hashes by URL so we don't re-download the same script URL repeatedly
    hash_cache = {}
    scripts = []
    for item in unique_requests:
        script_url = item["url"]
        if script_url not in hash_cache:
            hash_cache[script_url] = await fetch_script_sha256(context.request, script_url)

        scripts.append({
            "url": script_url,
            "sha256": hash_cache[script_url],
            "has_sri": script_url in sri_set,
            "loaded_by": item["loaded_by"],
        })

    # 6. Format result exactly per contracts/crawl_example.json (HANDBOOK 6.2)
    crawled_at = datetime.now(timezone.utc).astimezone().isoformat()
    result = {
        "site": site_url,
        "page": page_url,
        "crawled_at": crawled_at,
        "scripts": scripts,
    }

    # 7. Save JSON to crawler/output/
    output_dir.mkdir(parents=True, exist_ok=True)
    filename = f"{safe_slug(page_url)}.json"
    output_path = output_dir / filename
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2)

    logger.info("Saved %d scripts to %s", len(scripts), output_path)
    return result


async def run_crawler(sites_file: Path, output_dir: Path):
    """Load sites list and crawl all pages."""
    if not sites_file.is_file():
        logger.error("Sites configuration file not found at %s", sites_file)
        sys.exit(1)

    with open(sites_file, "r", encoding="utf-8") as f:
        sites_data = json.load(f)

    logger.info("Loaded %d client sites from %s", len(sites_data), sites_file)

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
        )

        for site_info in sites_data:
            client = site_info.get("client", "Unknown Client")
            site_url = site_info.get("site", "").rstrip("/")
            pages = site_info.get("pages", ["/"])

            logger.info("--- Crawling client: %s (%s) ---", client, site_url)

            for page_path in pages:
                if page_path.startswith("http://") or page_path.startswith("https://"):
                    full_page_url = page_path
                else:
                    full_page_url = f"{site_url}{page_path}" if page_path.startswith("/") else f"{site_url}/{page_path}"

                try:
                    await crawl_page(context, site_url, full_page_url, output_dir)
                except Exception as e:
                    logger.error("Failed to crawl %s: %s", full_page_url, e)

        await browser.close()

    logger.info("Crawling completed. Results stored in %s", output_dir)


def main():
    """Main entrypoint for running the crawler."""
    # Find repository root or current directory
    current_dir = Path(__file__).resolve().parent
    sites_file = current_dir / "sites.json"
    output_dir = current_dir / "output"

    if len(sys.argv) > 1:
        sites_file = Path(sys.argv[1])
    if len(sys.argv) > 2:
        output_dir = Path(sys.argv[2])

    asyncio.run(run_crawler(sites_file, output_dir))


if __name__ == "__main__":
    main()
