"""
Offline Unit Test for Crawler Ingestion (crawler/test_ingest.py)
----------------------------------------------------------------
Tests crawler/ingest.py using an in-memory FakeGraph.
Does NOT connect to FalkorDB or make any network calls.

LIMITATION NOTICE:
FakeGraph simulates openCypher MERGE/ON CREATE/ON MATCH relationship semantics
in-memory. Verification against a live FalkorDB graph engine requires an active
FalkorDB instance.
"""

import sys
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from crawler import ingest


class FakeGraph:
    """In-memory mock graph capturing executed Cypher queries, entities, and relationship properties."""
    def __init__(self):
        self.queries = []
        self.nodes = set()
        # edges: map (source, type, target) -> properties dict
        self.edges = {}

    def query(self, cypher, params=None):
        p = params or {}
        self.queries.append({"cypher": cypher.strip(), "params": p})

        # Track created entities for idempotency assertions
        if "MERGE (c:Client" in cypher:
            self.nodes.add(("Client", p.get("client")))
            self.nodes.add(("Site", p.get("site")))
            self.nodes.add(("Developer", p.get("dev")))
            self.edges[(p.get("client"), "OWNS", p.get("site"))] = {}
            self.edges[(p.get("dev"), "MAINTAINS", p.get("site"))] = {}
        elif "MERGE (p:Page" in cypher:
            self.nodes.add(("Page", p.get("page")))
            self.edges[(p.get("site"), "HAS_PAGE", p.get("page"))] = {}
        elif "MERGE (sc:Script" in cypher:
            self.nodes.add(("Script", p.get("url")))
            self.nodes.add(("Domain", p.get("domain")))
            self.edges[(p.get("url"), "SERVED_FROM", p.get("domain"))] = {}
        elif "MERGE (p)-[r:LOADS]->(sc)" in cypher:
            # HTML load relationship: MERGE without via in pattern; updates via on create/match
            key = (p.get("page"), "LOADS", p.get("url"))
            props = self.edges.get(key, {})
            props["via"] = "html"
            self.edges[key] = props
        elif "MERGE (parent)-[r:LOADS]->(sc)" in cypher:
            # Runtime load relationship: MERGE without via in pattern; updates via on create/match
            key = (p.get("parent_url"), "LOADS", p.get("url"))
            props = self.edges.get(key, {})
            props["via"] = "runtime"
            self.edges[key] = props

        return SimpleNamespace(result_set=[])


SAMPLE_CRAWL = {
    "site": "https://smilecare-demo.netlify.app",
    "page": "https://smilecare-demo.netlify.app/",
    "crawled_at": "2026-10-18T10:00:00+05:30",
    "scripts": [
        {
            "url": "https://cdn-demo.netlify.app/tag-loader.js",
            "sha256": "hash-tag-loader-123",
            "has_sri": False,
            "loaded_by": "page",
        },
        {
            "url": "https://cdn-demo.netlify.app/chat-widget.js",
            "sha256": "hash-chat-widget-456",
            "has_sri": False,
            "loaded_by": "https://cdn-demo.netlify.app/tag-loader.js",
        },
        {
            "url": "https://cdn-demo.netlify.app/helper.js",
            "sha256": "hash-helper-789",
            "has_sri": False,
            "loaded_by": "https://cdn-demo.netlify.app/chat-widget.js",
        },
    ],
}

SITES_META = {
    "https://smilecare-demo.netlify.app": {
        "client": "SmileCare Clinic",
        "developer": "Teammate 3",
        "site": "https://smilecare-demo.netlify.app",
    }
}


def run_tests():
    print("Running crawler ingest offline tests...")

    # 1. Validation tests
    assert ingest.validate_crawl_data(SAMPLE_CRAWL) is True
    assert ingest.validate_crawl_data({}) is False
    assert ingest.validate_crawl_data({"site": "x", "page": "y"}) is False
    assert ingest.validate_crawl_data({"site": "x", "page": "y", "scripts": "not-a-list"}) is False
    print("PASS: Schema validation tests")

    # 2. Cypher query structure verification
    assert "{via:" not in ingest.CYPHER_MERGE_HTML_LOAD, "CYPHER_MERGE_HTML_LOAD must not have via in MERGE pattern"
    assert "MERGE (p)-[r:LOADS]->(sc)" in ingest.CYPHER_MERGE_HTML_LOAD
    assert "ON CREATE SET r.via = 'html'" in ingest.CYPHER_MERGE_HTML_LOAD
    assert "ON MATCH SET r.via = 'html'" in ingest.CYPHER_MERGE_HTML_LOAD

    assert "{via:" not in ingest.CYPHER_MERGE_RUNTIME_LOAD, "CYPHER_MERGE_RUNTIME_LOAD must not have via in MERGE pattern"
    assert "MERGE (parent)-[r:LOADS]->(sc)" in ingest.CYPHER_MERGE_RUNTIME_LOAD
    assert "ON CREATE SET r.via = 'runtime'" in ingest.CYPHER_MERGE_RUNTIME_LOAD
    assert "ON MATCH SET r.via = 'runtime'" in ingest.CYPHER_MERGE_RUNTIME_LOAD
    print("PASS: Cypher MERGE pattern and ON CREATE/MATCH structure")

    # 3. Ingestion execution
    g = FakeGraph()
    count = ingest.ingest_crawl_data(g, SAMPLE_CRAWL, SITES_META)
    assert count == 3, f"Expected 3 scripts ingested, got {count}"

    # Verify nodes & edges
    assert ("Client", "SmileCare Clinic") in g.nodes
    assert ("Site", "https://smilecare-demo.netlify.app") in g.nodes
    assert ("Page", "https://smilecare-demo.netlify.app/") in g.nodes
    assert ("Developer", "Teammate 3") in g.nodes
    assert ("Script", "https://cdn-demo.netlify.app/tag-loader.js") in g.nodes
    assert ("Script", "https://cdn-demo.netlify.app/chat-widget.js") in g.nodes
    assert ("Script", "https://cdn-demo.netlify.app/helper.js") in g.nodes
    assert ("Domain", "cdn-demo.netlify.app") in g.nodes

    # Verify relationships & properties
    tag_key = ("https://smilecare-demo.netlify.app/", "LOADS", "https://cdn-demo.netlify.app/tag-loader.js")
    chat_key = ("https://cdn-demo.netlify.app/tag-loader.js", "LOADS", "https://cdn-demo.netlify.app/chat-widget.js")
    helper_key = ("https://cdn-demo.netlify.app/chat-widget.js", "LOADS", "https://cdn-demo.netlify.app/helper.js")

    assert tag_key in g.edges and g.edges[tag_key]["via"] == "html"
    assert chat_key in g.edges and g.edges[chat_key]["via"] == "runtime"
    assert helper_key in g.edges and g.edges[helper_key]["via"] == "runtime"
    print("PASS: Entity and multi-hop relationship creation with via properties")

    # 4. Idempotency test: re-ingest identical input
    prev_nodes_count = len(g.nodes)
    prev_edges_count = len(g.edges)

    ingest.ingest_crawl_data(g, SAMPLE_CRAWL, SITES_META)
    assert len(g.nodes) == prev_nodes_count, "Running ingest twice must NOT create duplicate nodes"
    assert len(g.edges) == prev_edges_count, "Running ingest twice must NOT create duplicate edges"
    print("PASS: Re-ingestion idempotency (zero duplicate nodes or edges on re-run)")

    # 5. Pre-existing LOADS relationship without a via property
    g_pre = FakeGraph()
    pre_edge_key = ("https://smilecare-demo.netlify.app/", "LOADS", "https://cdn-demo.netlify.app/tag-loader.js")
    # Simulate pre-existing relationship without 'via' property
    g_pre.edges[pre_edge_key] = {}
    assert "via" not in g_pre.edges[pre_edge_key]
    initial_edge_count = len(g_pre.edges)

    ingest.ingest_crawl_data(g_pre, SAMPLE_CRAWL, SITES_META)
    # The pre-existing LOADS relationship must be matched (not duplicated) and updated with via='html'
    loads_edges = [k for k in g_pre.edges.keys() if k[1] == "LOADS" and k[0] == pre_edge_key[0] and k[2] == pre_edge_key[2]]
    assert len(loads_edges) == 1, f"Expected exactly 1 LOADS edge between endpoints, found {len(loads_edges)}"
    assert g_pre.edges[pre_edge_key]["via"] == "html", "Pre-existing edge without via must be updated to via='html'"
    print("PASS: Pre-existing LOADS relationship without via updated idempotently without duplication")

    # 6. Pre-existing relationship whose via value differs
    g_diff = FakeGraph()
    diff_key = ("https://smilecare-demo.netlify.app/", "LOADS", "https://cdn-demo.netlify.app/tag-loader.js")
    # Simulate pre-existing relationship with via='runtime' (or legacy value)
    g_diff.edges[diff_key] = {"via": "runtime"}
    initial_diff_edges = len(g_diff.edges)

    ingest.ingest_crawl_data(g_diff, SAMPLE_CRAWL, SITES_META)
    loads_diff = [k for k in g_diff.edges.keys() if k[1] == "LOADS" and k[0] == diff_key[0] and k[2] == diff_key[2]]
    assert len(loads_diff) == 1, f"Expected exactly 1 LOADS edge between endpoints, found {len(loads_diff)}"
    assert g_diff.edges[diff_key]["via"] == "html", "Pre-existing edge with differing via must be updated to via='html'"
    print("PASS: Pre-existing LOADS relationship with differing via updated idempotently without duplication")

    print("ALL INGEST TESTS PASSED (100% OFFLINE)")


if __name__ == "__main__":
    run_tests()
