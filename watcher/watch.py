"""Script watcher: re-download every Script in the graph, compare sha256, raise incidents.

Usage:
    python watcher/watch.py --once          # one pass, then exit (for testing)
    python watcher/watch.py                 # loop forever, every 30 s
    python watcher/watch.py --interval 10   # loop, every 10 s

Spec: HANDBOOK.md section 9.2. Reads FALKORDB_* and GRAPH_NAME from .env.
"""
import argparse
import hashlib
import os
import random
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from urllib.parse import urlparse

DEFAULT_INTERVAL = 30
PLACEHOLDER_PREFIX = "seed-"  # seed_graph.py stores seed-<filename> until a real hash exists
TIMEOUT = 15

LIST_SCRIPTS = "MATCH (s:Script) RETURN s.url, s.sha256"
STORE_HASH = "MATCH (s:Script {url: $url}) SET s.sha256 = $new, s.last_seen = $now"
TOUCH = "MATCH (s:Script {url: $url}) SET s.last_seen = $now"
MARK_CHANGED = (
    "MATCH (s:Script {url: $url}) "
    "SET s.previous_sha256 = s.sha256, s.sha256 = $new, s.changed_at = $now, s.last_seen = $now"
)
# Same Cypher as the API's /incidents/simulate endpoint (HANDBOOK 9.2).
CREATE_INCIDENT = (
    "MATCH (s:Script {url: $url}) "
    "CREATE (i:Incident {id: $id, kind: 'hash_change', status: 'open', created_at: $t})-[:ABOUT]->(s)"
)


def now_iso():
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def log(msg):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}", flush=True)


def short_name(url):
    return os.path.basename(urlparse(url).path) or url


def fetch_script(url):
    """Download a script bypassing caches. Returns bytes, or None on any error."""
    sep = "&" if "?" in url else "?"
    busted = f"{url}{sep}t={int(time.time() * 1000)}"
    req = urllib.request.Request(
        busted,
        headers={"Cache-Control": "no-cache", "Pragma": "no-cache", "User-Agent": "blast-radius-watcher/1.0"},
    )
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
            return resp.read()
    except (urllib.error.URLError, OSError, ValueError) as e:  # HTTPError is a URLError
        log(f"download error for {url}: {e} (skipped)")
        return None


def sha256_hex(data):
    return hashlib.sha256(data).hexdigest()


def new_incident_id():
    return f"inc-{random.randint(0, 999999):06d}"


def check_once(graph, fetch=fetch_script):
    """One pass over all scripts. Returns a list of (url, incident_id) for each alarm raised."""
    rows = graph.query(LIST_SCRIPTS).result_set
    alarms = []
    for url, stored in rows:
        body = fetch(url)
        if body is None:
            continue  # download error: log and skip, no alarm
        new = sha256_hex(body)
        now = now_iso()

        if not stored or str(stored).startswith(PLACEHOLDER_PREFIX):
            graph.query(STORE_HASH, {"url": url, "new": new, "now": now})
            log(f"baseline stored for {short_name(url)}")
        elif new != stored:
            graph.query(MARK_CHANGED, {"url": url, "new": new, "now": now})
            inc_id = new_incident_id()
            graph.query(CREATE_INCIDENT, {"url": url, "id": inc_id, "t": now})
            print(f"ALARM: {short_name(url)} changed → incident {inc_id}", flush=True)
            alarms.append((url, inc_id))
        else:
            graph.query(TOUCH, {"url": url, "now": now})
    log(f"checked {len(rows)} script(s), {len(alarms)} alarm(s)")
    return alarms


def connect():
    try:
        from dotenv import load_dotenv

        load_dotenv()
    except ImportError:
        pass
    from falkordb import FalkorDB

    db = FalkorDB(
        host=os.getenv("FALKORDB_HOST", "localhost"),
        port=int(os.getenv("FALKORDB_PORT", "6379")),
        username=os.getenv("FALKORDB_USERNAME") or None,
        password=os.getenv("FALKORDB_PASSWORD") or None,
        ssl=os.getenv("FALKORDB_TLS", "false").lower() == "true",
    )
    return db.select_graph(os.getenv("GRAPH_NAME", "agency_demo"))


def main(argv=None):
    ap = argparse.ArgumentParser(description="Watch scripts for content changes.")
    ap.add_argument("--once", action="store_true", help="run a single pass and exit")
    ap.add_argument("--interval", type=int, default=DEFAULT_INTERVAL, help="seconds between passes")
    args = ap.parse_args(argv)

    graph = connect()
    log(f"watcher started ({'once' if args.once else f'every {args.interval}s'})")
    try:
        while True:
            try:
                check_once(graph)
            except Exception as e:  # a DB hiccup must not kill the loop during the demo
                if args.once:
                    raise
                log(f"pass failed: {e}")
            if args.once:
                return 0
            time.sleep(args.interval)
    except KeyboardInterrupt:
        log("stopped")
        return 0


if __name__ == "__main__":
    sys.exit(main())
