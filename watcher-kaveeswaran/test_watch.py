"""Offline test for watch.check_once using a fake graph. Run: python watcher/test_watch.py"""
import os
import sys
from types import SimpleNamespace

sys.path.insert(0, os.path.dirname(__file__))
import watch  # noqa: E402


class FakeGraph:
    def __init__(self, scripts):
        self.scripts = scripts  # url -> props dict
        self.incidents = []

    def query(self, cypher, params=None):
        p = params or {}
        if cypher == watch.LIST_SCRIPTS:
            return SimpleNamespace(result_set=[[u, s["sha256"]] for u, s in self.scripts.items()])
        s = self.scripts.get(p.get("url"))
        if cypher == watch.STORE_HASH:
            s["sha256"] = p["new"]
        elif cypher == watch.MARK_CHANGED:
            s["previous_sha256"], s["sha256"], s["changed_at"] = s["sha256"], p["new"], p["now"]
        elif cypher == watch.CREATE_INCIDENT:
            self.incidents.append((p["url"], p["id"]))
        return SimpleNamespace(result_set=[])


CHAT = "https://cdn-demo.netlify.app/chat-widget.js"
ANA = "https://cdn-demo.netlify.app/analytics.js"
BAD = "https://cdn-demo.netlify.app/helper.js"
bodies = {CHAT: b"clean chat", ANA: b"clean analytics"}  # BAD is missing -> download error


def fetch(url):
    return bodies.get(url)


g = FakeGraph({u: {"sha256": "seed-" + u.rsplit("/", 1)[1]} for u in (CHAT, ANA, BAD)})

# 1. placeholders get a real hash, no alarm
assert watch.check_once(g, fetch) == []
assert g.scripts[CHAT]["sha256"] == watch.sha256_hex(b"clean chat")
assert g.scripts[BAD]["sha256"].startswith("seed-")  # error -> untouched

# 2. nothing changed -> no alarm
assert watch.check_once(g, fetch) == []

# 3. hack chat-widget.js -> exactly one alarm, hashes rotated
bodies[CHAT] = b"HACKED chat"
alarms = watch.check_once(g, fetch)
assert [a[0] for a in alarms] == [CHAT], alarms
assert g.scripts[CHAT]["previous_sha256"] == watch.sha256_hex(b"clean chat")
assert g.scripts[CHAT]["sha256"] == watch.sha256_hex(b"HACKED chat")
assert g.incidents == alarms and g.incidents[0][1].startswith("inc-")

# 4. same hacked content again -> no repeat alarm
assert watch.check_once(g, fetch) == []
print("PASS")
