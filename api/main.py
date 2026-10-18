"""The API: the glue between the map, the agent, the fix maker and the dashboard.

Run from the project root:
    uvicorn api.main:app --reload --port 8000
Then open http://localhost:8000/docs to try every endpoint in the browser.

Responses follow contracts/api.md and the shapes in mocks/.
"""
import sys
from datetime import datetime, timezone
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from graph import queries as q  # noqa: E402
from fixer.fix import propose_fix  # noqa: E402

app = FastAPI(title="Script Blast Radius API")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])


class Question(BaseModel):
    question: str


class Simulate(BaseModel):
    script: str  # full URL, or just the file name like "chat-widget.js"


def now():
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def find_script(name_or_url):
    rows, _ = q.run("MATCH (s:Script) WHERE s.url = $v OR s.url ENDS WITH $slash RETURN s.url AS url",
                    {"v": name_or_url, "slash": "/" + name_or_url.rsplit("/", 1)[-1]})
    return rows[0]["url"] if rows else None


@app.get("/api/health")
def health():
    try:
        rows, _ = q.run("MATCH (n) RETURN count(n) AS nodes")
        node_count = rows[0]["nodes"] if rows else 0
        return {"ok": True, "nodes": node_count}
    except Exception:
        # Do not leak credentials, connection strings, or internal stack traces
        return {
            "ok": False,
            "nodes": 0,
            "error": "database_unavailable",
            "detail": "Graph database unreachable",
        }


@app.get("/api/graph")
def graph():
    """Nodes and arrows for the graph picture on the dashboard."""
    rows, _ = q.run(
        """
        MATCH (a)-[r]->(b) WHERE NOT a:Incident
        RETURN ID(a) AS a_id, labels(a)[0] AS a_label, coalesce(a.name, a.url) AS a_name,
               type(r) AS type,
               ID(b) AS b_id, labels(b)[0] AS b_label, coalesce(b.name, b.url) AS b_name
        """
    )
    nodes, edges = {}, []
    for r in rows:
        nodes[r["a_id"]] = {"id": str(r["a_id"]), "label": r["a_label"], "name": r["a_name"]}
        nodes[r["b_id"]] = {"id": str(r["b_id"]), "label": r["b_label"], "name": r["b_name"]}
        edges.append({"from": str(r["a_id"]), "to": str(r["b_id"]), "type": r["type"]})
    return {"nodes": list(nodes.values()), "edges": edges}


@app.post("/api/incidents/simulate")
def simulate(body: Simulate):
    """Create an alarm by hand (for testing and the demo). The watcher creates them the same way."""
    url = find_script(body.script)
    if not url:
        raise HTTPException(404, f"No script named {body.script} in the map")
    inc_id = "inc-" + datetime.now().strftime("%H%M%S")
    q.run(
        """
        MATCH (s:Script {url: $url})
        CREATE (i:Incident {id: $id, kind: 'hash_change', status: 'open', created_at: $t})-[:ABOUT]->(s)
        """,
        {"url": url, "id": inc_id, "t": now()},
    )
    return {"id": inc_id, "script": url}


@app.get("/api/incidents")
def incidents():
    rows, _ = q.run(
        """
        MATCH (i:Incident)-[:ABOUT]->(s:Script)
        RETURN i.id AS id, i.kind AS kind, i.status AS status, i.created_at AS created_at, s.url AS script
        ORDER BY created_at DESC
        """
    )
    for r in rows:
        pages, _ = q.blast_radius_script(r["script"])
        r["pages_affected"] = len({p["page"] for p in pages})
    return rows


def get_incident(inc_id):
    rows, _ = q.run(
        """
        MATCH (i:Incident {id: $id})-[:ABOUT]->(s:Script)
        RETURN i.id AS id, i.kind AS kind, i.status AS status, i.created_at AS created_at, s.url AS script
        """,
        {"id": inc_id},
    )
    if not rows:
        raise HTTPException(404, f"No incident {inc_id}")
    return rows[0]


@app.get("/api/incidents/{inc_id}")
def incident(inc_id: str):
    inc = get_incident(inc_id)
    fix = propose_fix(inc["script"])
    affected, _ = q.blast_radius_script(inc["script"])
    owner_by_site = {s["site"]: s["owner"] for s in fix["sites"]}
    trace = [{"step": i + 1, "tool": t["tool"], "inputs": t.get("inputs", {}), "cypher": t["cypher"],
              "rows": t["rows"], "time_ms": t["time_ms"]} for i, t in enumerate(fix["trace"])]
    return {
        **inc,
        "summary": fix["summary"],
        "affected": [{"client": r["client"], "site": r["site"], "page": r["page"], "chain": r["chain"],
                      "runtime_only": r["runtime_only"], "owner": owner_by_site.get(r["site"])} for r in affected],
        "trace": trace,
        "fix": {
            "sri": fix["sri"],
            "sri_note": fix["sri_note"],
            "csp": "\n".join(f"{s['site']}  ->  {s['csp']}" for s in fix["sites"]),
            "patch": "\n\n".join(s["patch"] for s in fix["sites"]),
            "sites": fix["sites"],
        },
        "message": "\n\n".join(s["message"] for s in fix["sites"]),
    }


@app.post("/api/incidents/{inc_id}/approve")
def approve(inc_id: str):
    """A human clicked Approve. Recorded in the graph. Opening the pull request is connected later."""
    get_incident(inc_id)
    q.run("MATCH (i:Incident {id: $id}) SET i.status = 'approved', i.approved_at = $t", {"id": inc_id, "t": now()})
    return {"status": "approved", "id": inc_id, "pr_url": None,
            "note": "Approval saved. Pull request creation not connected yet."}


@app.post("/api/ask")
def ask(body: Question):
    """Hands the question to the agent (agent/agent.py, built by the agent teammate)."""
    try:
        from agent.agent import ask as agent_ask
    except Exception as e:
        raise HTTPException(503, f"Agent not connected yet: {e}")
    return agent_ask(body.question)


@app.get("/api/spof")
def spof():
    rows, _ = q.single_points_of_failure()
    return rows
