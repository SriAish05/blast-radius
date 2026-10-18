"""Empty the map (graph) completely, ready for a real crawl.

ONLY AISH RUNS THIS. It deletes everything in the shared cloud graph.
Run from the project root:  python seed/reset_graph.py
Then:  python crawler/crawl.py  ->  python crawler/ingest.py  ->  python watcher/watch.py --once
"""
import os
from pathlib import Path

from falkordb import FalkorDB

ROOT = Path(__file__).resolve().parent.parent
try:
    from dotenv import load_dotenv
    load_dotenv(ROOT / ".env")
except ImportError:
    pass

name = os.getenv("GRAPH_NAME", "agency_demo")
if input(f"This deletes EVERYTHING in graph '{name}'. Type YES to continue: ").strip() != "YES":
    raise SystemExit("Cancelled. Nothing changed.")

g = FalkorDB(
    host=os.getenv("FALKORDB_HOST", "localhost"),
    port=int(os.getenv("FALKORDB_PORT", "6379")),
    username=os.getenv("FALKORDB_USERNAME") or None,
    password=os.getenv("FALKORDB_PASSWORD") or None,
    ssl=os.getenv("FALKORDB_TLS", "false").lower() == "true",
).select_graph(name)

g.query("MATCH (n) DETACH DELETE n")
for label, prop in [("Page", "url"), ("Script", "url"), ("Domain", "name"), ("Site", "url"),
                    ("Client", "name"), ("Incident", "id")]:
    try:
        g.query(f"CREATE INDEX FOR (n:{label}) ON (n.{prop})")
    except Exception:
        pass  # index already exists
left = g.query("MATCH (n) RETURN count(n)").result_set[0][0]
print(f"Graph '{name}' is now empty ({left} nodes). Next: python crawler/crawl.py")
