# Script Blast Radius Agent

When a third-party script on a client website goes bad, this agent shows every affected site and page,
the exact chain that loads the script, and a fix ready for human approval. Built on FalkorDB.

Track: Graph Hacks 2026, Track 01: Agents That Act on Connected Data

## Run it (5 minutes)

1. Start FalkorDB: `docker compose up -d` (Browser at http://localhost:3000)
2. Install Python packages: `pip install -r requirements.txt`
3. Copy settings: `cp .env.example .env`
4. Build the starting map: `python seed/seed_graph.py`
5. Check the map answers: `python graph/queries.py` (every line should say PASS)

## Folders

| Folder | What is in it |
|---|---|
| contracts/ | The rules sheet: names, crawl format, API, answer key |
| mocks/ | Fake API answers so the dashboard can be built early |
| seed/ | Builds a small map from the answer key |
| graph/ | The questions we ask the map (Cypher) |

Note: `contracts/answer_key.json` uses dummy demo URLs for now. They get replaced with the real demo sites.

## AI assistance
Built with help from Claude (Claude Code) and Antigravity. Gemini powers the agent's explanations.
