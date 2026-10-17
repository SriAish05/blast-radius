"""The questions we ask the map. The agent's tools call these functions.

Run a quick check:  python graph/queries.py
"""
import os
import time

from falkordb import FalkorDB

HOST = os.getenv("FALKORDB_HOST", "localhost")
PORT = int(os.getenv("FALKORDB_PORT", "6379"))
GRAPH = os.getenv("GRAPH_NAME", "agency_demo")

_g = None


def graph():
    global _g
    if _g is None:
        _g = FalkorDB(host=HOST, port=PORT).select_graph(GRAPH)
    return _g


def run(cypher, params=None):
    """Run a query and return (rows as dicts, trace info)."""
    start = time.time()
    res = graph().query(cypher, params or {})
    cols = [h[1] if isinstance(h, (list, tuple)) else h for h in res.header]
    rows = [dict(zip(cols, r)) for r in res.result_set]
    trace = {"cypher": " ".join(cypher.split()), "params": params or {},
             "rows": len(rows), "time_ms": round((time.time() - start) * 1000, 1)}
    return rows, trace


# Path: Client -> Site -> Page -> Script ... Script.
# 3 hops means the page HTML loads it directly; more means it arrives at runtime.
_BLAST = """
MATCH path = (c:Client)-[:OWNS]->(s:Site)-[:HAS_PAGE]->(p:Page)-[:LOADS*1..5]->(sc:Script)
{where}
RETURN c.name AS client, s.url AS site, p.url AS page, sc.url AS script,
       [n IN nodes(path)[2..] | n.url] AS chain,
       length(path) > 3 AS runtime_only
ORDER BY site, page
"""


def blast_radius_script(url):
    """Every client, site and page that loads this script, with the chain."""
    return run(_BLAST.format(where="WHERE sc.url = $url"), {"url": url})


def blast_radius_domain(domain):
    """Every client, site and page that loads any script from this domain."""
    q = _BLAST.format(where="WHERE (sc)-[:SERVED_FROM]->(:Domain {name: $domain})")
    return run(q, {"domain": domain})


def load_chain(page, script):
    """The shortest chain from one page to one script."""
    return run(
        """
        MATCH path = (p:Page {url: $page})-[:LOADS*1..5]->(sc:Script {url: $script})
        WITH path ORDER BY length(path) LIMIT 1
        RETURN [n IN nodes(path) | n.url] AS chain
        """,
        {"page": page, "script": script},
    )


def single_points_of_failure(limit=10):
    """Third-party domains that reach the most client sites."""
    return run(
        """
        MATCH (s:Site)-[:HAS_PAGE]->(:Page)-[:LOADS*1..5]->(:Script)-[:SERVED_FROM]->(d:Domain)
        WHERE d.first_party = false
        RETURN d.name AS domain, count(DISTINCT s) AS sites_reached
        ORDER BY sites_reached DESC LIMIT $limit
        """,
        {"limit": limit},
    )


def scripts_changed_since(iso_time):
    """Scripts whose content changed after this time (set by the watcher)."""
    return run(
        """
        MATCH (sc:Script) WHERE sc.changed_at IS NOT NULL AND sc.changed_at >= $t
        RETURN sc.url AS script, sc.previous_sha256 AS old_hash, sc.sha256 AS new_hash, sc.changed_at AS changed_at
        """,
        {"t": iso_time},
    )


def owners(site):
    """Who maintains this site."""
    return run(
        "MATCH (d:Developer)-[:MAINTAINS]->(s:Site {url: $site}) RETURN d.name AS developer",
        {"site": site},
    )


if __name__ == "__main__":
    import json
    from pathlib import Path

    key = json.loads((Path(__file__).resolve().parent.parent / "contracts" / "answer_key.json").read_text())
    exp = key["expected"]

    rows, t = blast_radius_script("https://cdn-demo.netlify.app/chat-widget.js")
    got = sorted({r["page"] for r in rows})
    want = sorted(exp["pages_affected_if_chat_widget_is_hacked"])
    print("blast_radius_script(chat-widget.js):", "PASS" if got == want else f"FAIL got {got}")
    for r in rows:
        print("   ", " -> ".join(r["chain"]), "(runtime only)" if r["runtime_only"] else "")

    rows, t = blast_radius_domain("cdn-demo.netlify.app")
    got = sorted({r["page"] for r in rows})
    want = sorted(exp["pages_affected_if_cdn_demo_domain_is_hacked"])
    print("blast_radius_domain(cdn-demo):", "PASS" if got == want else f"FAIL got {got}")

    rows, t = load_chain("https://bakery-demo.netlify.app/", "https://cdn-demo.netlify.app/helper.js")
    print("load_chain(bakery home -> helper.js):", rows[0]["chain"] if rows else "not found")

    rows, t = single_points_of_failure()
    print("single_points_of_failure:", rows)

    rows, t = owners("https://bakery-demo.netlify.app")
    print("owners(bakery):", rows)
