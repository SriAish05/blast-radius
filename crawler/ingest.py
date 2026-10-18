"""
Load crawler output (crawler/output/*.json) into FalkorDB idempotently.

Follows HANDBOOK.md Section 6.1, 6.2, and Section 9.1 strictly.
Safe to run many times (MERGE, no duplicate nodes or edges).
Client and developer metadata are mapped from crawler/sites.json.

By default, only THIRD-PARTY scripts are ingested into the map (first-party files are skipped).
Pass --all to ingest all scripts (first-party and third-party).

Usage:
    python crawler/ingest.py [--all] [--dir DIR] [--sites SITES] [DIR]
"""

import json
import logging
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parent.parent
HERE = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

try:
    from dotenv import load_dotenv
    load_dotenv(ROOT / ".env")
except ImportError:
    pass

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(levelname)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("ingest")

CYPHER_MERGE_SITE_META = """
MERGE (c:Client {name: $client})
MERGE (s:Site {url: $site})
ON CREATE SET s.domain = $domain
MERGE (c)-[:OWNS]->(s)
MERGE (dev:Developer {name: $dev})
MERGE (dev)-[:MAINTAINS]->(s)
"""

CYPHER_MERGE_PAGE = """
MATCH (s:Site {url: $site})
MERGE (p:Page {url: $page})
MERGE (s)-[:HAS_PAGE]->(p)
"""

CYPHER_MERGE_SCRIPT_AND_DOMAIN = """
MERGE (sc:Script {url: $url})
ON CREATE SET sc.sha256 = $sha, sc.has_sri = $sri, sc.first_seen = $now, sc.last_seen = $now
ON MATCH SET sc.sha256 = CASE WHEN $sha <> '' THEN $sha ELSE sc.sha256 END, sc.has_sri = $sri, sc.last_seen = $now
MERGE (d:Domain {name: $domain})
ON CREATE SET d.first_party = $first_party
MERGE (sc)-[:SERVED_FROM]->(d)
"""

CYPHER_MERGE_HTML_LOAD = """
MATCH (p:Page {url: $page}), (sc:Script {url: $url})
MERGE (p)-[r:LOADS]->(sc)
ON CREATE SET r.via = 'html'
ON MATCH SET r.via = 'html'
"""

CYPHER_MERGE_RUNTIME_LOAD = """
MATCH (parent:Script {url: $parent_url}), (sc:Script {url: $url})
MERGE (parent)-[r:LOADS]->(sc)
ON CREATE SET r.via = 'runtime'
ON MATCH SET r.via = 'runtime'
"""


def domain_of(url: str) -> str:
    """Extract domain hostname from URL."""
    return urlparse(url).netloc.lower() or url.lower()


def now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def load_sites_metadata(sites_file: Path) -> dict:
    """Load client and developer metadata from sites.json mapped by site URL and domain."""
    meta = {}
    if not sites_file.exists():
        return meta
    try:
        data = json.loads(sites_file.read_text(encoding="utf-8"))
        for entry in data:
            site_url = entry.get("site", "").rstrip("/")
            if site_url:
                meta[site_url] = entry
                meta[domain_of(site_url)] = entry
    except Exception as e:
        logger.warning("Could not read %s: %s", sites_file, e)
    return meta


def validate_crawl_data(data: dict) -> bool:
    """Ensure crawl JSON conforms to Section 6.2 schema."""
    if not isinstance(data, dict):
        return False
    if "site" not in data or "page" not in data or "scripts" not in data:
        return False
    if not isinstance(data.get("scripts"), list):
        return False
    for s in data["scripts"]:
        if not isinstance(s, dict) or "url" not in s or "loaded_by" not in s:
            return False
    return True


class IngestResult(dict):
    """Result object supporting both dict access and numeric comparison with script count."""
    @property
    def scripts(self) -> int:
        return self.get("scripts", 0)

    def __eq__(self, other):
        if isinstance(other, int):
            return self.get("scripts", 0) == other
        return super().__eq__(other)

    def __int__(self) -> int:
        return self.get("scripts", 0)


def ingest_crawl_data(graph, data: dict, sites_meta: dict = None, keep_all: bool = False) -> IngestResult:
    """
    Ingest a single crawl dictionary into the FalkorDB graph idempotently.
    By default, filters out first-party scripts (keeps third-party only).
    Set keep_all=True to ingest all scripts.
    Returns IngestResult: {'pages': 1, 'scripts': count, 'skipped': count}.
    """
    if not validate_crawl_data(data):
        raise ValueError("Invalid crawl data structure (fails Section 6.2 schema)")

    site_url = data["site"]
    page_url = data["page"]
    scripts = data["scripts"]
    crawled_time = data.get("crawled_at") or now_iso()

    sites_meta = sites_meta or {}
    site_key = site_url.rstrip("/")
    site_entry = sites_meta.get(site_key) or sites_meta.get(domain_of(site_url)) or {}

    client_name = site_entry.get("client") or f"Client ({domain_of(site_url)})"
    dev_name = site_entry.get("developer") or "Unassigned Developer"

    # Known first-party site domains
    own_domain = domain_of(site_url)
    all_site_domains = {own_domain}
    for entry in sites_meta.values():
        if isinstance(entry, dict) and "site" in entry:
            all_site_domains.add(domain_of(entry["site"]))

    # 1. Merge Client, Site, Developer
    graph.query(
        CYPHER_MERGE_SITE_META,
        {
            "client": client_name,
            "site": site_url,
            "domain": own_domain,
            "dev": dev_name,
        },
    )

    # 2. Merge Page and HAS_PAGE relationship
    graph.query(CYPHER_MERGE_PAGE, {"site": site_url, "page": page_url})

    # 3. Filter scripts and merge Script, Domain, and LOADS relationships
    kept_urls = set()
    ingested_count = 0
    skipped_count = 0

    for s in scripts:
        script_url = s["url"]
        script_domain = domain_of(script_url)
        is_first_party = script_domain == own_domain

        # Third-party filtering: skip first-party scripts unless keep_all is True
        if not keep_all and is_first_party:
            skipped_count += 1
            continue

        kept_urls.add(script_url)
        is_known_site = script_domain in all_site_domains

        graph.query(
            CYPHER_MERGE_SCRIPT_AND_DOMAIN,
            {
                "url": script_url,
                "sha": s.get("sha256") or "",
                "sri": bool(s.get("has_sri", False)),
                "domain": script_domain,
                "first_party": is_known_site,
                "now": crawled_time,
            },
        )

        # 4. Merge LOADS arrows
        loaded_by = s.get("loaded_by")
        # If loaded by page, or parent was skipped (first-party), link directly to page via 'html'
        if not loaded_by or loaded_by == "page" or loaded_by == page_url or loaded_by not in kept_urls:
            graph.query(CYPHER_MERGE_HTML_LOAD, {"page": page_url, "url": script_url})
        else:
            # Runtime load by another third-party script that was kept
            parent_domain = domain_of(loaded_by)
            graph.query(
                CYPHER_MERGE_SCRIPT_AND_DOMAIN,
                {
                    "url": loaded_by,
                    "sha": "",
                    "sri": False,
                    "domain": parent_domain,
                    "first_party": parent_domain in all_site_domains,
                    "now": crawled_time,
                },
            )
            graph.query(
                CYPHER_MERGE_RUNTIME_LOAD,
                {"parent_url": loaded_by, "url": script_url},
            )
        ingested_count += 1

    return IngestResult({"pages": 1, "scripts": ingested_count, "skipped": skipped_count})


def ingest_directory(graph, output_dir: Path, sites_file: Path = None, keep_all: bool = False) -> dict:
    """Ingest all JSON files from output_dir into graph."""
    sites_meta = load_sites_metadata(sites_file) if sites_file else {}
    files = sorted(output_dir.glob("*.json"))
    if not files:
        logger.warning("No crawl files in %s", output_dir)
        return {"files": 0, "pages": 0, "scripts": 0, "skipped": 0}

    total_pages = 0
    total_scripts = 0
    total_skipped = 0
    ingested_files = 0

    for f in files:
        try:
            content = json.loads(f.read_text(encoding="utf-8"))
            res = ingest_crawl_data(graph, content, sites_meta, keep_all=keep_all)
            ingested_files += 1
            total_pages += res.get("pages", 1)
            total_scripts += res.get("scripts", 0)
            total_skipped += res.get("skipped", 0)
            logger.info("Ingested %s (%d scripts, %d skipped)", f.name, res.get("scripts", 0), res.get("skipped", 0))
        except Exception as e:
            logger.warning("Failed to ingest %s: %s", f.name, e)

    return {
        "files": ingested_files,
        "pages": total_pages,
        "scripts": total_scripts,
        "skipped": total_skipped,
    }


def connect():
    """Connect to FalkorDB per .env configuration."""
    from falkordb import FalkorDB

    host = os.getenv("FALKORDB_HOST", "localhost")
    port = int(os.getenv("FALKORDB_PORT", "6379"))
    username = os.getenv("FALKORDB_USERNAME") or None
    password = os.getenv("FALKORDB_PASSWORD") or None
    ssl = os.getenv("FALKORDB_TLS", "false").lower() == "true"
    graph_name = os.getenv("GRAPH_NAME", "agency_demo")

    db = FalkorDB(host=host, port=port, username=username, password=password, ssl=ssl)
    return db.select_graph(graph_name)


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Ingest crawl JSON outputs into FalkorDB.")
    parser.add_argument("pos_dir", nargs="?", default=None, help="Directory containing crawl JSONs (positional)")
    parser.add_argument("--dir", type=str, default=None, help="Directory containing crawl JSONs")
    parser.add_argument("--sites", type=str, default=str(HERE / "sites.json"), help="Path to sites.json")
    parser.add_argument("--all", action="store_true", help="Keep all scripts (default keeps only third-party)")
    args = parser.parse_args()

    target_dir_str = args.dir or args.pos_dir or str(HERE / "output")
    out_dir = Path(target_dir_str)
    sites_file = Path(args.sites)

    if not out_dir.exists():
        sys.exit(f"No crawl files in {out_dir}. Run python crawler/crawl.py first.")

    g = connect()
    res = ingest_directory(g, out_dir, sites_file, keep_all=args.all)
    graph_name = os.getenv("GRAPH_NAME", "agency_demo")
    print(
        f"Ingested {res['pages']} page(s), {res['scripts']} script record(s) into graph '{graph_name}' "
        f"(skipped {res['skipped']} first-party files)."
    )


if __name__ == "__main__":
    main()
