"""Build the starting map in FalkorDB from contracts/answer_key.json.

Run:  python seed/seed_graph.py
Needs FalkorDB running (docker compose up) and: pip install falkordb
Running it again wipes the graph and rebuilds it, so it is always clean.
"""
import json
import os
from pathlib import Path
from urllib.parse import urlparse

from falkordb import FalkorDB

try:
    from dotenv import load_dotenv
    load_dotenv()  # reads settings from .env
except ImportError:
    pass

ROOT = Path(__file__).resolve().parent.parent
KEY_FILE = ROOT / "contracts" / "answer_key.json"

HOST = os.getenv("FALKORDB_HOST", "localhost")
PORT = int(os.getenv("FALKORDB_PORT", "6379"))
USER = os.getenv("FALKORDB_USERNAME") or None
PASSWORD = os.getenv("FALKORDB_PASSWORD") or None
TLS = os.getenv("FALKORDB_TLS", "false").lower() == "true"


def domain_of(url):
    return urlparse(url).netloc


def main():
    key = json.loads(KEY_FILE.read_text())
    graph_name = key.get("agency", "agency_demo")
    db = FalkorDB(host=HOST, port=PORT, username=USER, password=PASSWORD, ssl=TLS)
    g = db.select_graph(graph_name)

    # start clean
    try:
        g.delete()
    except Exception:
        pass  # graph did not exist yet
    g = db.select_graph(graph_name)

    site_domains = {domain_of(s["url"]) for c in key["clients"] for s in c["sites"]}

    def add_script(url, has_sri):
        g.query(
            """
            MERGE (sc:Script {url: $url})
            ON CREATE SET sc.sha256 = $sha, sc.has_sri = $sri
            MERGE (d:Domain {name: $domain})
            ON CREATE SET d.first_party = $first_party
            MERGE (sc)-[:SERVED_FROM]->(d)
            """,
            {
                "url": url,
                "sha": "seed-" + url.rsplit("/", 1)[-1],
                "sri": has_sri,
                "domain": domain_of(url),
                "first_party": domain_of(url) in site_domains,
            },
        )

    def walk(parent_script, items):
        # a script that loads other scripts at runtime
        for item in items:
            add_script(item["script"], item.get("has_sri", False))
            g.query(
                """
                MATCH (a:Script {url: $a}), (b:Script {url: $b})
                MERGE (a)-[:LOADS {via: 'runtime'}]->(b)
                """,
                {"a": parent_script, "b": item["script"]},
            )
            walk(item["script"], item.get("loads", []))

    for client in key["clients"]:
        for site in client["sites"]:
            g.query(
                """
                MERGE (c:Client {name: $client})
                MERGE (s:Site {url: $site})
                ON CREATE SET s.domain = $domain
                MERGE (c)-[:OWNS]->(s)
                MERGE (dev:Developer {name: $dev})
                MERGE (dev)-[:MAINTAINS]->(s)
                """,
                {"client": client["name"], "site": site["url"],
                 "domain": domain_of(site["url"]), "dev": client.get("developer", "unknown")},
            )
            for page in site["pages"]:
                g.query(
                    """
                    MATCH (s:Site {url: $site})
                    MERGE (p:Page {url: $page})
                    MERGE (s)-[:HAS_PAGE]->(p)
                    """,
                    {"site": site["url"], "page": page["url"]},
                )
                for item in page["loads"]:
                    add_script(item["script"], item.get("has_sri", False))
                    g.query(
                        """
                        MATCH (p:Page {url: $page}), (sc:Script {url: $script})
                        MERGE (p)-[:LOADS {via: 'html'}]->(sc)
                        """,
                        {"page": page["url"], "script": item["script"]},
                    )
                    walk(item["script"], item.get("loads", []))

    for label, prop in [("Page", "url"), ("Script", "url"), ("Domain", "name"), ("Site", "url")]:
        try:
            g.query(f"CREATE INDEX FOR (n:{label}) ON (n.{prop})")
        except Exception:
            pass  # index already exists

    counts = g.query("MATCH (n) RETURN labels(n)[0] AS label, count(n) AS n ORDER BY label").result_set
    print(f"Graph '{graph_name}' built:")
    for label, n in counts:
        print(f"  {label}: {n}")


if __name__ == "__main__":
    main()
