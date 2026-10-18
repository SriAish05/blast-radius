# Script Blast Radius Agent: Team Handbook

> **For AI assistants (Antigravity, Claude, etc.):** this file is the single source of truth for this project. Read it fully before writing code. Follow the contracts in section 6 exactly. Only change the files your human asks about. If something here conflicts with the code, trust the code and tell the human.
>
> **For teammates:** you can start from any section. Read section 1 (what we build), section 3 (how the parts fit), then jump to the part you're working on.

Last updated: Sat 17 Oct 2026, 10 PM IST.

---

## Contents
1. What we are building (plain English)
2. Words you need (glossary)
3. How the parts fit together
4. Status: what's done, what's left, who owns it
5. Repo map: every folder and file
6. Contracts (the rules everyone follows)
7. Setup on a new laptop (Windows)
8. Part by part: how each piece works
9. Parts still to build: full specs (robot, watcher, dashboard)
10. The live demo, step by step
11. Team rules
12. Known issues and to-dos
13. Questions judges may ask

---

## 1. What we are building (plain English)

**The problem.** Websites load small code files called *scripts* from other websites: chat bubbles, analytics counters, tag managers. Some scripts load *more* scripts by themselves while the page runs, so those never appear in the website's own code. If any of these outside scripts gets hacked, every website using it runs the hacked code. This really happened in 2024 with **polyfill.io**: one domain changed hands, the script turned malicious, and over 100,000 websites were affected.

**Who suffers most.** Small web agencies and freelancers who look after many client websites with no security team. When a script goes bad, they need to know *tonight*: which clients are affected, how, and what to do.

**What our tool does.**
1. A **robot** visits each client website like a visitor and records every script, plus *which script loaded which*.
2. Everything goes into a **graph database (FalkorDB)** as a map: client → site → page → script → script → domain.
3. A **watcher** keeps re-checking the scripts. If one changes, it raises an **alarm (incident)**.
4. An **AI agent** answers questions like "which sites use chat-widget.js?" by running fixed graph queries, and explains the result.
5. A **fix maker** prepares the fix (SRI hash, CSP rule, patch) and a message for each client.
6. A **dashboard** shows the alarm, the affected sites, the exact path, what FalkorDB did, and an **Approve** button. Nothing changes until a human approves.

**Why the graph is essential (the rule we must pass).** The hackathon disqualifies projects that still work without FalkorDB. Ours can't: finding a script that's loaded *through other scripts* means following a chain of arrows of unknown length. That is exactly what a graph query does in one step (`-[:LOADS*1..5]->`). Searching the code finds nothing, because the code never mentions the hidden script.

**Hackathon facts.** Graph Hacks 2026 (WeMakeDevs × FalkorDB). We enter **Track 01: Agents That Act on Connected Data**. Judges look for: multi-hop reasoning, graph queries as agent tools, tool selection through MCP, actions based on the graph, explainable results. Deadline **Sun 18 Oct 2026, 11:59 PM IST**; our target is **9 PM**. Submission needs a public repo, README with setup and graph model, the Cypher queries, a demo video, a live link or local setup steps, the track name, and disclosure of AI tools used.

---

## 2. Words you need (glossary)

| Word | Meaning |
|---|---|
| Script | A `.js` file a web page loads and runs. |
| CDN | A server that hosts files for other sites. Ours is `cdn-demo.netlify.app`, our own "script server" for the demo. |
| Runtime-loaded / hidden script | A script that another script injects while the page runs. It is not in the page's HTML. |
| Blast radius | Everything affected if one script or domain goes bad. |
| Graph | Data stored as **nodes** (things) and **edges/relationships** (arrows between things). |
| FalkorDB | Our graph database (required by the hackathon). Speaks the Redis protocol. Queried with **Cypher**. |
| Cypher | The graph query language. `MATCH (a)-[:LOADS]->(b) RETURN b` = "find what a loads". |
| SRI | Subresource Integrity. A hash in the `<script>` tag (`integrity="sha384-..."`). The browser refuses the file if even one byte changes. **It cannot protect runtime-injected scripts**, because the page never names them. |
| CSP | Content-Security-Policy. A rule that lists which domains a page may load scripts from. Can block a bad domain. |
| Incident | An alarm stored in the graph: "this script changed". |
| Robot / crawler | Program that visits sites and records scripts (not built yet). |
| Watcher | Program that re-downloads scripts and raises incidents on change (not built yet). |
| Agent | The AI part: Gemini picks a graph tool, our code runs it, Gemini explains. |
| MCP | Model Context Protocol. A standard plug that lets any AI app (Claude Desktop, Antigravity) use our tools. |
| Answer key | `contracts/answer_key.json`. The correct list of which page loads which script. Everything is tested against it. |
| Seed | `seed/seed_graph.py`. Builds the map from the answer key. **Wipes the graph first.** |

---

## 3. How the parts fit together

```
 Client websites (Netlify/Vercel)          Our demo CDN (cdn-demo.netlify.app)
 SmileCare, SmartMart, Aurelis,    ──load──►  tag-loader.js ─► analytics.js
 Wedding hall, Cafe                           tag-loader.js ─► chat-widget.js ─► helper.js
        │
        │ visited by
        ▼
 ┌──────────────┐  writes   ┌──────────────────────┐  reads  ┌──────────────┐
 │ ROBOT        │ ────────► │      FalkorDB        │ ◄────── │ AGENT tools  │◄── Gemini (explains)
 │ crawler/     │           │  graph "agency_demo" │         │ agent/       │◄── MCP clients
 └──────────────┘           │                      │         └──────┬───────┘
 ┌──────────────┐  writes   │  Client Site Page    │  reads  ┌──────┴───────┐
 │ WATCHER      │ ────────► │  Script Domain       │ ◄────── │ FIX MAKER    │
 │ watcher/     │ incidents │  Developer Incident  │         │ fixer/       │
 └──────────────┘           └──────────▲───────────┘         └──────┬───────┘
                                       │ queries                    │
                                ┌──────┴────────────────────────────┴──┐
                                │ API (FastAPI)  api/main.py :8000      │
                                └──────────────────▲────────────────────┘
                                                   │ HTTP JSON
                                        ┌──────────┴──────────┐
                                        │ DASHBOARD  web/     │ ── Approve (human)
                                        └─────────────────────┘
```

**The story in one line:** robot builds the map → watcher sees a change → API + agent + fix maker read the map → dashboard shows it → human approves.

---

## 4. Status: what's done, what's left, who owns it

| Part | Folder | Status | Owner |
|---|---|---|---|
| Contracts (rules sheet), answer key, mocks | `contracts/`, `mocks/` | ✅ Done (answer key uses **dummy** demo URLs) | Aish |
| Starting map script | `seed/seed_graph.py` | ✅ Done, tested | Aish |
| Graph queries | `graph/queries.py` | ✅ Done, tested (PASS) | Aish |
| Cloud FalkorDB | FalkorDB Cloud (AWS ap-south-1) | ✅ Running, map loaded | Aish |
| Fix maker | `fixer/fix.py` | ✅ Done, tested | Aish |
| API | `api/main.py` | ✅ Done, all endpoints tested | Aish |
| Demo CDN + "hacked" version | `demo-sites/cdn`, `demo-sites/cdn-hacked` | ✅ Built + browser-tested; **not online yet** | Aish to upload |
| Backup demo sites | `demo-sites/bakery`, `clinic`, `coaching` | ✅ Built (backup only) | - |
| AI agent + tests | `agent/` | ✅ Done, 12/12 tests pass, connected to API | Teammate 2 |
| MCP server | `agent/mcp_server.py` | ✅ Built; live proof in progress | Teammate 2 |
| Real client websites (5) | their own repos/hosting | 🔨 In progress | Teammates 3 & 4 |
| Robot (crawler + ingest) | `crawler/` | ❌ Not built: spec in 9.1 | Aish (with AI help) |
| Watcher | `watcher/` | ❌ Not built: spec in 9.2 | Aish (with AI help) |
| Dashboard | `web/` | 🔨 In progress: spec in 9.3 | Teammate 2 |
| README, demo video, blog post | root | ❌ Sunday | Team |

---

## 5. Repo map: every folder and file

```
blast-radius/
├── HANDBOOK.md            ← this file
├── README.md              ← public setup guide for judges
├── AGENT_BRIEF.md         ← the brief used to build agent/
├── requirements.txt       ← falkordb, python-dotenv, fastapi, uvicorn (+ agent needs google-genai)
├── docker-compose.yml     ← optional local FalkorDB (ports 6379 + 3000)
├── .env.example           ← copy to .env and fill in (never commit .env)
├── contracts/
│   ├── schema.md          ← graph names (nodes, arrows, properties)
│   ├── crawl_example.json ← what the robot must output per page
│   ├── api.md             ← API endpoints list
│   └── answer_key.json    ← correct page→script chains + expected results
├── mocks/                 ← fake API answers for the dashboard (same shapes as the real API)
├── seed/seed_graph.py     ← builds the map from answer_key.json (WIPES the graph first)
├── graph/queries.py       ← all graph questions; the agent and API call these
├── fixer/
│   ├── fix.py             ← builds SRI / CSP / patch / client message
│   └── known_good/        ← clean copies of scripts (used for SRI). Never put hacked copies here.
├── api/main.py            ← FastAPI server, run with uvicorn
├── agent/
│   ├── tools.py           ← tool wrappers + name lookup (chat-widget.js → full URL)
│   ├── agent.py           ← ask(question) using Gemini, cache, fallback, AI_OFF mode
│   ├── test_agent.py      ← 12 test questions, both modes
│   ├── mcp_server.py      ← MCP server exposing the same read-only tools
│   └── MCP_README.md      ← how to connect MCP clients
├── demo-sites/
│   ├── cdn/               ← upload to Netlify as "cdn-demo" (4 scripts + index page)
│   ├── cdn-hacked/        ← same, but chat-widget.js adds a red banner. Only for the demo hack.
│   ├── bakery/ clinic/ coaching/  ← backup demo sites (fictional)
│   ├── set_names.py       ← rewrites URLs if a Netlify name was taken
│   └── DEPLOY.md          ← Netlify steps
├── crawler/               ← (to build) crawl.py, ingest.py
├── watcher/               ← (to build) watch.py
└── web/                   ← (in progress) dashboard
```

---

## 6. Contracts (the rules everyone follows)

Never rename these without telling the whole team.

### 6.1 Graph schema (graph name `agency_demo`)

**Nodes**

| Label | Properties |
|---|---|
| Client | name |
| Site | url (e.g. `https://bakery-demo.netlify.app`), domain |
| Page | url (home page ends with `/`) |
| Script | url, sha256, previous_sha256, has_sri, changed_at, first_seen, last_seen |
| Domain | name (e.g. `cdn-demo.netlify.app`), first_party (true if it's one of our client sites) |
| Developer | name |
| Advisory | source, reason, date (optional) |
| Incident | id (e.g. `inc-180752`), kind (`hash_change` / `advisory`), status (`open` / `approved`), created_at, approved_at |

**Arrows (relationships)**

| Arrow | Meaning |
|---|---|
| `(Client)-[:OWNS]->(Site)` | client owns the site |
| `(Site)-[:HAS_PAGE]->(Page)` | page belongs to site |
| `(Page)-[:LOADS {via:'html'}]->(Script)` | the page HTML loads the script |
| `(Script)-[:LOADS {via:'runtime'}]->(Script)` | a script injected another script |
| `(Script)-[:SERVED_FROM]->(Domain)` | where the file lives |
| `(Developer)-[:MAINTAINS]->(Site)` | who to notify |
| `(Advisory)-[:FLAGS]->(Domain)` | domain reported bad |
| `(Incident)-[:ABOUT]->(Script)` | alarm about this script |

Rules: store full URLs exactly as the browser requests them. Always pass values as query **parameters**, never build Cypher by string concatenation.

### 6.2 Robot output (one JSON object per page): `contracts/crawl_example.json`
```json
{
  "site": "https://bakery-demo.netlify.app",
  "page": "https://bakery-demo.netlify.app/",
  "crawled_at": "2026-10-17T19:30:00+05:30",
  "scripts": [
    {"url": "https://cdn-demo.netlify.app/tag-loader.js", "sha256": "…", "has_sri": false, "loaded_by": "page"},
    {"url": "https://cdn-demo.netlify.app/chat-widget.js", "sha256": "…", "has_sri": false,
     "loaded_by": "https://cdn-demo.netlify.app/tag-loader.js"}
  ]
}
```
`loaded_by` is `"page"` when the HTML itself loaded the script, otherwise the URL of the script that injected it.

### 6.3 API (base `http://localhost:8000/api`, CORS open)

| Method + path | Body | Returns |
|---|---|---|
| GET `/health` | - | `{ok, nodes}` |
| GET `/graph` | - | `{nodes:[{id,label,name}], edges:[{from,to,type}]}` |
| POST `/incidents/simulate` | `{"script":"chat-widget.js"}` (name or full URL) | `{id, script}` or 404 |
| GET `/incidents` | - | `[{id, kind, status, created_at, script, pages_affected}]` |
| GET `/incidents/{id}` | - | `{id, kind, status, created_at, script, summary, affected:[{client, site, page, chain:[urls], runtime_only, owner}], trace:[{step, tool, inputs, cypher, rows, time_ms}], fix:{sri, sri_note, csp, patch, sites:[…]}, message}` |
| POST `/incidents/{id}/approve` | - | `{status:"approved", id, pr_url:null, note}` |
| POST `/ask` | `{"question":"…"}` | agent output `{question, answer, trace, used_ai}`; 503 if agent missing |
| GET `/spof` | - | `[{domain, sites_reached}]` |

Interactive test page: `http://localhost:8000/docs`.

---

## 7. Setup on a new laptop (Windows)

1. Install **Python 3.11+** (tick "Add to PATH") and **Git**.
2. `git clone https://github.com/<owner>/blast-radius.git` then `cd blast-radius`
3. `pip install -r requirements.txt` (agent work also needs `pip install google-genai`; robot work needs `pip install playwright` then `playwright install chromium`)
4. `copy .env.example .env` then `notepad .env` and fill in:
   ```
   FALKORDB_HOST=<cloud host, ask Aish privately>
   FALKORDB_PORT=55695
   FALKORDB_USERNAME=falkordb
   FALKORDB_PASSWORD=<ask Aish privately>
   FALKORDB_TLS=false          ← cloud works with false; true timed out
   GRAPH_NAME=agency_demo
   GEMINI_API_KEY=<your own free key from aistudio.google.com>
   AI_OFF=false
   ```
   Watch out: Notepad may save it as `.env.txt`. Fix with `ren .env.txt .env`.
5. Check the connection: `python graph/queries.py` should print **PASS** twice.
6. **Do NOT run `python seed/seed_graph.py`** on the shared cloud database. It wipes and rebuilds the map. Only Aish runs it.
7. Start the API: `uvicorn api.main:app --reload --port 8000` and open `http://localhost:8000/docs`.

Opening a Command Prompt in a folder: open it in File Explorer → click the address bar → type `cmd` → Enter.

---

## 8. Part by part: how each piece works

### 8.1 FalkorDB and the graph
- Hosted on **FalkorDB Cloud** (free tier, one instance). Browser UI: log in at the FalkorDB Browser with host/port/user/password, select graph `agency_demo`.
- View the whole map: `MATCH (n)-[r]->(m) RETURN n,r,m`
- See the hidden chain: `MATCH path=(p:Page)-[:LOADS*1..5]->(s:Script {url:'https://cdn-demo.netlify.app/helper.js'}) RETURN path`
- **FalkorDB quirks we hit (important for anyone writing Cypher):**
  - No regex operator `=~`. Use `STARTS WITH`, `ENDS WITH`, `CONTAINS`.
  - No label expressions like `(n:A|B)`.
  - Sorting by the path after only returning a projection fails (`Unable to locate a value with alias path`). Fix: `WITH path ORDER BY length(path) LIMIT 1 RETURN …`.
  - Python `str.format()` on Cypher breaks on `{name: $x}` braces. Don't format Cypher strings; use parameters.

### 8.2 `seed/seed_graph.py`
Reads `contracts/answer_key.json` and builds the map: Client → OWNS → Site → HAS_PAGE → Page → LOADS → Script (nested `loads` become Script→Script runtime arrows), Script → SERVED_FROM → Domain, Developer → MAINTAINS → Site. Uses MERGE, so no duplicates. **Deletes the graph first.** Adds indexes on Page.url, Script.url, Domain.name, Site.url. Placeholder hashes `seed-<filename>` until the robot fills real ones.

### 8.3 `graph/queries.py`
Every function returns `(rows, trace)`: `rows` is a list of dicts, `trace` is `{cypher, params, rows, time_ms}`. The trace is what the dashboard shows as "what FalkorDB did".

| Function | What it answers |
|---|---|
| `blast_radius_script(url)` | every client/site/page that loads this script, with the chain and `runtime_only` |
| `blast_radius_domain(domain)` | same, for any script from that domain |
| `load_chain(page, script)` | shortest path page → script |
| `single_points_of_failure(limit=10)` | third-party domains reaching the most sites |
| `scripts_changed_since(iso_time)` | scripts with `changed_at` after a time (set by the watcher) |
| `owners(site)` | who maintains the site |
| `run(cypher, params)` | low-level helper used by everything |

How `runtime_only` works: the path is Client→Site→Page→Script… Three arrows means the page loads the script directly; more than three means it came through another script, so `length(path) > 3` means hidden. `python graph/queries.py` runs self-checks against the answer key.

### 8.4 `fixer/fix.py`: `propose_fix(script_url, clean_content=None)`
1. Finds affected pages with `blast_radius_script`.
2. **SRI**: hashes the *known-good* copy from `fixer/known_good/<filename>` (sha384). It never hashes the live file, which may already be the hacked one.
3. **Per site CSP**: `script-src 'self'` + every third-party domain the site uses (from the graph) **except the bad domain**.
4. **Patch preview per page**:
   - Directly loaded: replace the tag with a self-hosted copy plus the SRI hash.
   - Runtime-loaded: pause the *loader* script, because SRI can't protect injected scripts. This is our key security insight.
5. **Client message** per site, signed by the site's Developer.
Returns `{script, found, bad_domain, sri, sri_note, summary, sites:[{client, site, owner, pages, csp, patch, message}], trace}`. Run `python fixer/fix.py` to see it.

### 8.5 `api/main.py`
A FastAPI server joining everything. `simulate` creates an Incident node exactly like the watcher will. `incidents/{id}` combines blast radius + fix + trace into one response for the dashboard. `approve` sets status `approved` (opening a real pull request is not connected yet). `ask` imports `agent.agent.ask`.

### 8.6 `agent/` (built by Teammate 2)
- `ask(question)` → Gemini Flash-Lite (model name in `.env`, `GEMINI_MODEL`) with automatic function calling capped at **3 calls** (`AutomaticFunctionCallingConfig(maximum_remote_calls=3)`), temperature 0.
- Tools: `blast_radius`, `load_chain`, `single_points_of_failure`, `scripts_changed_since`, `owners`, plus a name resolver (`ENDS WITH` lookup) so "chat-widget.js" becomes the full URL.
- Safety nets: in-memory cache; template answer if Gemini errors; `AI_OFF=true` uses keyword rules and templates (`used_ai:false`); 0 rows → "not found"; off-topic → polite refusal. Gemini never writes Cypher.
- `test_agent.py`: 12 questions (incl. typo + off-topic), all pass in both modes.
- `mcp_server.py`: the same 5 read-only tools over MCP; setup in `MCP_README.md`.

### 8.7 `demo-sites/`: the CDN and the hack
- `cdn/tag-loader.js` injects `analytics.js` and `chat-widget.js`. `chat-widget.js` shows a green "Chat with us" bubble and injects `helper.js`. All harmless (console logs only).
- `cdn-hacked/chat-widget.js` = same + a red banner "DEMO COMPROMISE…". Still harmless.
- **The hack:** Netlify → cdn-demo site → Deploys → drag `cdn-hacked` folder. **Undo:** drag `cdn` again. The CDN's URL stays the same; only the file content (and its hash) changes.
- Real client sites and their one line (pasted before `</head>`):

| Site | Line | Expected chain |
|---|---|---|
| SmileCare | `<script src="https://cdn-demo.netlify.app/chat-widget.js"></script>` | page → chat-widget.js → helper.js |
| SmartMart | `…/tag-loader.js` | page → tag-loader.js → analytics.js + chat-widget.js → helper.js |
| Aurelis | `…/tag-loader.js` | same as SmartMart |
| Wedding hall | `…/analytics.js` | page → analytics.js |
| Cafe | nothing | no scripts from us (the "safe" control site) |

  So hacking `chat-widget.js` hits SmileCare (directly) and SmartMart + Aurelis (hidden). Wedding hall and cafe stay safe.
- Tested in headless Chromium: the chain and initiators are recorded correctly; the bubble and banner render.

---

## 9. Parts still to build: full specs

### 9.1 Robot (crawler): `crawler/crawl.py` + `crawler/ingest.py`

**Goal:** visit each page, record every script and who loaded it, save JSON in the 6.2 format, then load it into FalkorDB.

**Input:** `crawler/sites.json`, e.g.
```json
[
  {"client": "SmileCare Dental Clinic", "developer": "Teammate 3",
   "site": "https://smilecare-xxx.netlify.app", "pages": ["/", "/about"]},
  {"client": "Cafe", "developer": "Teammate 4", "site": "https://cafe-xxx.vercel.app", "pages": ["/"]}
]
```

**How to detect "who loaded which" (tested, works):** use Playwright with a Chrome DevTools Protocol session and listen to `Network.requestWillBeSent` for `type == "Script"`:
```python
cdp = await page.context.new_cdp_session(page)
await cdp.send("Network.enable")
def on_request(e):
    if e.get("type") != "Script":
        return
    ini = e["initiator"]
    by = None
    if ini.get("type") == "script":
        stack = ini.get("stack") or {}
        while stack and not by:                      # walk parent stacks too
            frames = stack.get("callFrames") or []
            by = next((f["url"] for f in frames if f.get("url")), None)
            stack = stack.get("parent")
    loaded_by = by if by and by != page_url else "page"   # parser / HTML → "page"
    found.append({"url": e["request"]["url"], "loaded_by": loaded_by})
cdp.on("Network.requestWillBeSent", on_request)
await page.goto(page_url, wait_until="networkidle")
await page.wait_for_timeout(1500)   # give injected scripts time to load
```
Then for each script:
- **sha256:** download the body (`page.request.get(url)` or `httpx`) and hash it.
- **has_sri:** check the DOM: `await page.eval_on_selector_all("script[src][integrity]", "els => els.map(e => e.src)")`.
- Ignore duplicate requests (same url + loaded_by). Keep first-party scripts too (the Domain gets `first_party=true`).

**Output:** one JSON per page into `crawler/output/` (folder in `.gitignore` is fine, or commit for the demo).

**`ingest.py`:** for each JSON, MERGE Client/Site/Page/Developer as in `seed_graph.py`, MERGE each Script (set `sha256`, `has_sri`, `last_seen`; set `first_seen` ON CREATE), MERGE `SERVED_FROM` Domain, and MERGE `(Page)-[:LOADS {via:'html'}]->(Script)` when `loaded_by=="page"`, else `(parent Script)-[:LOADS {via:'runtime'}]->(Script)`. Reuse the Cypher patterns in `seed/seed_graph.py`. Running twice must create no duplicates.

**Done when:** crawling the real sites produces the chains in the 8.7 table, including `helper.js` loaded by `chat-widget.js`; `python graph/queries.py`-style checks pass against the real-site answer key; the map in FalkorDB Browser shows the real sites.

**Gotchas:** wait for network idle plus a short delay; some pages load third-party scripts (Google Fonts, analytics), which is fine and makes the map richer; only crawl our own sites and public pages; never log in anywhere.

### 9.2 Watcher: `watcher/watch.py`

**Goal:** notice when a script's content changes and raise an incident.

**Logic (every N seconds, e.g. 30; plus `--once` flag for testing):**
1. `MATCH (s:Script) RETURN s.url, s.sha256`
2. Download each URL with a cache-busting query (`?t=<timestamp>`) and `Cache-Control: no-cache`; hash with sha256.
3. If the stored hash starts with `seed-` (placeholder), just store the real hash. No alarm.
4. If the hash differs: `SET s.previous_sha256 = s.sha256, s.sha256 = $new, s.changed_at = $now`, then create an incident with the **same Cypher as the API's simulate endpoint**:
   ```cypher
   MATCH (s:Script {url: $url})
   CREATE (i:Incident {id: $id, kind: 'hash_change', status: 'open', created_at: $t})-[:ABOUT]->(s)
   ```
   Print a clear line: `ALARM: chat-widget.js changed → incident inc-XXXX`.
5. Download errors: log and skip (no alarm).

**Done when:** after dragging `cdn-hacked` onto the CDN, the watcher raises an incident within one interval, the dashboard shows it, and `GET /api/incidents` lists it.

### 9.3 Dashboard: `web/` (React + Vite)

**Goal:** the screen judges see. API base URL in one config (default `http://localhost:8000/api`); fall back to `mocks/` if the API is down.

Build in this order:
1. **Incident page:** summary, table of affected sites/pages, each chain as breadcrumbs, red "runtime only" badge.
2. **"What FalkorDB did" trace panel:** tool, Cypher (monospace), rows, time.
3. **Fix panel:** CSP lines, patch as a diff (red `-`, green `+`), client message, **Approve** with an in-page confirm step.
4. **Simulate hack** button → POST `/incidents/simulate` → open the new incident.
5. **Ask box:** question → answer + trace.
6. **Graph view** of `/graph` (react-force-graph-2d or cytoscape); Script nodes in a distinct colour.
7. **Single points of failure** list from `/spof`.
8. (nice) Poll `/incidents` every 5 s and show a toast when a new one appears, so the watcher's alarm pops up live.

---

## 10. The live demo, step by step (about 3 minutes)

1. Show the 5 client sites (normal, green bubble on 3 of them).
2. Show the map in FalkorDB Browser or the dashboard graph view.
3. Ask the agent: "Which sites use chat-widget.js?" It answers with 3 sites, 2 hidden, and the trace shows the Cypher.
4. **Hack:** drag `cdn-hacked` onto the CDN's Netlify Deploys. The sites show the red banner.
5. The watcher raises the alarm. The dashboard shows: 3 sites affected, chains, "runtime only" badges, cafe and wedding hall safe.
6. Show the fix: SRI for the direct site, pause the loader for the hidden ones, CSP. Click **Approve**.
7. Show the same tool working from an MCP client (Antigravity / Claude Desktop).
8. Undo the hack (drag `cdn` back).

**Backups:** record the video early; if the watcher fails live, use the dashboard's Simulate button; if Gemini fails, `AI_OFF=true` still answers.

---

## 11. Team rules

- **Never commit `.env`** or any password/key. Check `git status` before every commit.
- **Never run `seed/seed_graph.py` on the cloud DB** unless you're Aish.
- One branch per part: `feat/agent`, `feat/dashboard`, `feat/robot`, `feat/watcher`. Merge to `main` with a pull request.
- Don't change contracts (section 6) alone. Tell the group first.
- Only our own demo sites and public pages. No logging in, no personal data.
- Every AI-written file: run it once and read it once. You must be able to explain your part to judges.
- AI tools used (disclose in README): Claude, Claude Code, Antigravity, Gemini.
- After **1 AM Sunday: no new features**, only fixes.

---

## 12. Known issues and to-dos

- `answer_key.json` still has **dummy** URLs (bakery-demo etc.). Replace with the real 5 sites once links arrive, then re-seed once (Aish).
- `cdn-demo` must be uploaded to Netlify. If the name is taken, use `demo-sites/set_names.py` and update the script lines on the sites.
- Approve records approval but doesn't open a real pull request yet (optional stretch).
- `fixer/known_good/` holds clean `chat-widget.js` and `tag-loader.js`. Keep it clean.
- The cloud DB password was shared in chats. **Reset it after the hackathon.**
- Gemini free tier is limited. Use your own key for testing, record the demo when quota is fresh.

---

## 13. Questions judges may ask

- **Why a graph, not SQL?** Finding hidden scripts means following chains of unknown length (`-[:LOADS*1..5]->`) across many sites. One graph query does it, and returns the path as proof. In SQL it's recursive joins.
- **Doesn't Cloudflare / cside already do this?** They monitor scripts per site and need to be installed on each site. We map a whole agency portfolio from outside, show the hidden chain, and an agent drafts the fix with human approval. Open source.
- **What if Gemini fails?** The core is plain code. Gemini only picks the tool and words the answer; there's a template fallback and an AI-off mode.
- **Why not just use SRI everywhere?** SRI can't protect scripts injected at runtime. That's exactly the gap our graph exposes, and why the fix pauses the loader instead.
- **Is any real harm done in the demo?** No. All scripts are ours, the "hack" only shows a banner, and the sites are our own.
