# Script Watcher (`watcher/`)

The watcher re-downloads every script stored in the graph, compares its SHA-256 hash with the stored one, and raises an **ALARM** (an Incident in FalkorDB) when a script changes.

It implements **HANDBOOK.md Section 9.2**.

---

## 🛠️ Prerequisites & Setup

```bash
pip install falkordb python-dotenv
```

Copy `.env.example` to `.env` and fill in the `FALKORDB_*` and `GRAPH_NAME` values (see HANDBOOK.md Section 7). The watcher only needs the standard library besides those two packages.

---

## 📁 File Structure

```
watcher/
├── watch.py        # Main watcher script
├── test_watch.py   # Offline test (fake graph, no database needed)
├── README.md       # This guide
└── .gitignore
```

---

## 🚀 Running the Watcher

From the root of the project:

```bash
python watcher/watch.py --once        # one pass, then exit (testing)
python watcher/watch.py               # loop forever, every 30 seconds
python watcher/watch.py --interval 10 # loop, every 10 seconds
```

---

## ⚙️ How it works

1. `MATCH (s:Script) RETURN s.url, s.sha256`
2. Each URL is downloaded with a `?t=<timestamp>` cache-buster and `Cache-Control: no-cache`, then hashed with SHA-256.
3. Stored hash starts with `seed-` (placeholder): the real hash is saved, **no alarm**.
4. Hash differs: `previous_sha256`, `sha256` and `changed_at` are updated, an Incident is created (same Cypher as the API's simulate endpoint), and this is printed:

```
ALARM: chat-widget.js changed → incident inc-123456
```

5. Download errors are logged and skipped (**no alarm**).

---

## 🧪 Running Automated Tests

```bash
python watcher/test_watch.py
```

Prints `PASS` when placeholders, unchanged scripts, a hacked script and download errors all behave correctly.
