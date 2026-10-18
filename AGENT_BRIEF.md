# Briefing for the coding agent (Antigravity): build the AI agent

You are the coding agent in Antigravity, working inside this repository (`blast-radius`). You can read files, create and edit files, and run terminal commands. You are helping a college student build one part of a hackathon project. He is a beginner with LLM tool calling, so:

- **Before coding, read these files:** `contracts/schema.md`, `contracts/answer_key.json`, `graph/queries.py`, `mocks/ask.json`, `.env.example`. Then show him a short plan (5 to 8 steps) and wait for his OK.
- Work **one small step at a time**. After each step: say in simple English what you did, run it in the terminal, and show whether it worked.
- Explain in very simple English. No jargon without a one-line explanation.
- He is on **Windows**. Use Windows-friendly commands (`python`, not `python3`).
- After writing each file, explain what each part does in 3 to 5 short bullets. He must be able to explain this code to hackathon judges, so do not write code he cannot follow.
- If a command fails, read the error, fix it, and tell him what went wrong in one line.
- Do not add features beyond the list below. Time is short.
- **Only create or edit files inside `agent/`** (plus `.env`, which must never be committed). Do not change other folders.

## The hackathon

- **Graph Hacks 2026** by WeMakeDevs with FalkorDB. Online. Deadline **Sunday 18 Oct 2026, 11:59 PM IST**. Team submits by 9 PM.
- Rule: **FalkorDB (a graph database) must do the real work.** If the product still works without FalkorDB, it is disqualified.
- We are in **Track 01: Agents That Act on Connected Data.** Judges look for: multi-hop reasoning, graph queries used as agent tools, tool selection (MCP is a bonus), actions based on the graph, explainable results.
- AI coding help is allowed but must be disclosed in the README.

## The project: Script Blast Radius Agent

Websites load small code files called scripts (chat widgets, analytics, tag managers) from other domains. Some scripts load *other* scripts at runtime, so those never appear in the site's own HTML. If one script gets hacked (this really happened with polyfill.io in 2024, 100,000+ sites hit), a web agency needs to know fast: which client sites are affected, through which chain, and how to fix it.

Our flow:
1. A crawler (teammate 2) visits sites and records every script and who loaded it.
2. That goes into FalkorDB as a graph.
3. A watcher spots when a script's content changes.
4. **The agent (your job)** answers questions by calling fixed graph queries, then explains the result.
5. A fix is prepared, and a human clicks Approve before anything changes.
6. A dashboard (teammate 3) shows the answer, the chain and the agent's steps.

## The graph (already built, already tested)

Graph name: `agency_demo`. FalkorDB runs locally on port 6379 (browser UI on http://localhost:3000).

Nodes: Client(name), Site(url, domain), Page(url), Script(url, sha256, previous_sha256, has_sri, changed_at), Domain(name, first_party), Developer(name).

Arrows: (Client)-[:OWNS]->(Site), (Site)-[:HAS_PAGE]->(Page), (Page)-[:LOADS]->(Script), (Script)-[:LOADS]->(Script) for runtime loads, (Script)-[:SERVED_FROM]->(Domain), (Developer)-[:MAINTAINS]->(Site).

Full rules: `contracts/schema.md`. Test data: `contracts/answer_key.json` (dummy demo URLs like `https://cdn-demo.netlify.app/chat-widget.js`; real ones come later, nothing else changes).

## What already exists in the repo (do NOT rewrite these)

`graph/queries.py`. Every function returns a tuple `(rows, trace)`:
- `rows` = list of dicts
- `trace` = `{"cypher": str, "params": dict, "rows": int, "time_ms": float}`

| Function | Rows look like |
|---|---|
| `blast_radius_script(url)` | `{client, site, page, script, chain: [urls], runtime_only: bool}` |
| `blast_radius_domain(domain)` | same as above |
| `load_chain(page, script)` | `{chain: [urls]}` (shortest path) |
| `single_points_of_failure(limit=10)` | `{domain, sites_reached}` |
| `scripts_changed_since(iso_time)` | `{script, old_hash, new_hash, changed_at}` |
| `owners(site)` | `{developer}` |

Run `python graph/queries.py` to check: it prints PASS twice.

Also: `mocks/ask.json` shows the exact output shape the dashboard expects from the agent.

## His task: build `agent/`

**Tech:** Python, the `google-genai` package (Google Gen AI SDK), a Gemini **Flash-Lite** model on the free tier. Before writing code, check the current SDK docs and the current Flash-Lite model name (search the web, or ask him to check https://aistudio.google.com), because names change. Do not guess. Put the model name in `.env` as `GEMINI_MODEL` so it is easy to change.

**Important:** this is the *product's* agent, which runs on the free Gemini API key. It is separate from you, the Antigravity coding agent. Keep its Gemini calls minimal.

**Golden rule: Gemini never writes Cypher and never invents facts.** Gemini only (1) picks which tool to call with what inputs and (2) explains the rows that our code returns.

### Deliverables

1. **`agent/tools.py`**: tool wrappers around `graph/queries.py`:
   - `blast_radius(target)`: if target looks like a URL ending in `.js`, call `blast_radius_script`, else `blast_radius_domain`
   - `load_chain(page, script)`
   - `single_points_of_failure()`
   - `scripts_changed_since(iso_time)`
   - `owners(site)`
   - Each has a clear docstring (Gemini reads it to choose) and returns `{rows, trace}`.
   - Also make **name matching friendly**: if the user types just `chat-widget.js`, find the full URL in the graph first (a small helper query: `MATCH (s:Script) WHERE s.url ENDS WITH $name RETURN s.url`). Do not use regex (`=~`); FalkorDB does not support it. Use `ENDS WITH` / `CONTAINS`.

2. **`agent/agent.py`**: `ask(question: str) -> dict` returning
   `{"question", "answer", "trace": [ {step, tool, inputs, cypher, rows, time_ms} ], "used_ai": bool}`
   - Send question + tool declarations to Gemini, run the tool it picks, send rows back, get a short plain-English answer.
   - **Max 3 Gemini calls per question** (free quota is small: maybe 20 to 1,500 requests/day depending on model).
   - If a tool returns 0 rows, the answer must say "not found", never invent sites.
   - Off-topic question: polite "I can only answer questions about scripts on our client sites."

3. **Safety nets** (important for a live demo):
   - **Cache**: same question → saved answer from a JSON file, no Gemini call.
   - **Fallback**: if Gemini errors (quota, network), build the answer from a fixed template using the rows, e.g. "3 pages on 3 sites load chat-widget.js: ...".
   - **`AI_OFF=true`** in `.env` → no Gemini at all. Use simple keyword rules to pick the tool, plus the template answer.

4. **`agent/test_agent.py`**: 10 test questions, printed with answers. Include:
   - "Which websites use chat-widget.js?" → 3 pages (bakery home, clinic home, coaching home)
   - "How does the bakery home page load helper.js?" → chain bakery home → tag-loader.js → chat-widget.js → helper.js
   - "What happens if cdn-demo.netlify.app is hacked?" → 4 pages
   - "Which domains are riskiest?"
   - "Who maintains the bakery site?"
   - an unknown script → "not found"
   - a typo → "not found" or best match, clearly stated
   - an off-topic question
   - run all of them again with `AI_OFF=true`

5. **Later, only if everything above works:** `agent/mcp_server.py` using the official MCP Python SDK, exposing the same tools so Claude Desktop can call them (Track 01 bonus).

### Setup steps for him (Windows)

1. FalkorDB must be running (`docker run -p 6379:6379 -p 3000:3000 -it --rm falkordb/falkordb:latest`, keep that window open), and the map built (`python seed/seed_graph.py`).
2. Free Gemini key from https://aistudio.google.com → put `GEMINI_API_KEY=...` in a file named `.env` in the project root (copy `.env.example`). **Never commit `.env`.**
3. `pip install falkordb google-genai python-dotenv`

### Done when

- `python agent/test_agent.py` gives correct answers for all 10 questions, with AI on and with `AI_OFF=true`.
- Each answer comes with a trace showing the Cypher that ran.
- Target: working by Saturday 10 PM IST.

### Rules
- Only change files inside `agent/`. If `graph/queries.py` seems wrong, tell him to message the teammate who owns it instead of changing it.
- Keep code short and readable. No frameworks like LangChain unless truly needed.
- Push to GitHub on his own branch `feat/agent`, small commits.
