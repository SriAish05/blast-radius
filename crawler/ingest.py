"""Load crawler output (crawler/output/*.json) into FalkorDB.

Run from the project root:  python crawler/ingest.py
Uses the same .env settings as the rest of the project. Safe to run many times (MERGE, no duplicates).
Client/developer names come from crawler/sites.json.
By default only THIRD-PARTY scripts go into the map (a site's own files are skipped).
Add --all to keep everything:  python crawler/ingest.py --all
"""
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

from falkordb import FalkorDB

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
try:
    from dotenv import load_dotenv
    load_dotenv(ROOT / ".env")
except ImportError:
    pass


def domain_of(url):
    return urlparse(url).netloc


def main():
    sites = json.loads((HERE / "sites.json").read_text(encoding="utf-8"))
    meta = {s["site"].rstrip("/"): s for s in sites}
    site_domains = {domain_of(s["site"]) for s in sites}
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    keep_all = "--all" in sys.argv
    out_dir = Path(args[0]) if args else HERE / "output"
    files = sorted(out_dir.glob("*.json"))
    if not files:
        sys.exit(f"No crawl files in {out_dir}. Run python crawler/crawl.py first.")

    g = FalkorDB(
        host=os.getenv("FALKORDB_HOST", "localhost"),
        port=int(os.getenv("FALKORDB_PORT", "6379")),
        username=os.getenv("FALKORDB_USERNAME") or None,
        password=os.getenv("FALKORDB_PASSWORD") or None,
        ssl=os.getenv("FALKORDB_TLS", "false").lower() == "true",
    ).select_graph(os.getenv("GRAPH_NAME", "agency_demo"))
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")

    pages = scripts = skipped = 0
    for f in files:
        rec = json.loads(f.read_text(encoding="utf-8"))
        site = rec["site"].rstrip("/")
        m = meta.get(site, {})
        g.query(
            """
            MERGE (c:Client {name: $client})
            MERGE (s:Site {url: $site}) ON CREATE SET s.domain = $domain
            MERGE (c)-[:OWNS]->(s)
            MERGE (d:Developer {name: $dev})
            MERGE (d)-[:MAINTAINS]->(s)
            MERGE (p:Page {url: $page})
            MERGE (s)-[:HAS_PAGE]->(p)
            """,
            {"client": m.get("client", domain_of(site)), "site": site, "domain": domain_of(site),
             "dev": m.get("developer", "unknown"), "page": rec["page"]},
        )
        pages += 1
        own = domain_of(site)
        kept = set()
        for sc in rec["scripts"]:
            if not keep_all and domain_of(sc["url"]) == own:
                skipped += 1
                continue
            kept.add(sc["url"])
            g.query(
                """
                MERGE (sc:Script {url: $url})
                ON CREATE SET sc.first_seen = $now, sc.sha256 = $sha
                SET sc.has_sri = $sri, sc.last_seen = $now
                MERGE (dm:Domain {name: $domain}) ON CREATE SET dm.first_party = $fp
                MERGE (sc)-[:SERVED_FROM]->(dm)
                """,
                {"url": sc["url"], "now": now, "sha": sc.get("sha256") or "", "sri": bool(sc.get("has_sri")),
                 "domain": domain_of(sc["url"]), "fp": domain_of(sc["url"]) in site_domains},
            )
            if sc["loaded_by"] == "page" or sc["loaded_by"] not in kept:
                # loaded by the page, or by one of the site's own (skipped) files
                g.query("MATCH (p:Page {url: $page}), (sc:Script {url: $url}) MERGE (p)-[:LOADS {via: 'html'}]->(sc)",
                        {"page": rec["page"], "url": sc["url"]})
            else:
                g.query(
                    """
                    MERGE (parent:Script {url: $parent})
                    WITH parent
                    MATCH (sc:Script {url: $url})
                    MERGE (parent)-[:LOADS {via: 'runtime'}]->(sc)
                    """,
                    {"parent": sc["loaded_by"], "url": sc["url"]},
                )
            scripts += 1
    print(f"Ingested {pages} page(s), {scripts} third-party script record(s) into graph "
          f"'{os.getenv('GRAPH_NAME', 'agency_demo')}' (skipped {skipped} of the sites' own files).")


if __name__ == "__main__":
    main()
