# Rules sheet: API (the dashboard only calls these)

Base URL for now: `/mocks` (fake data). Later: the real API.

| Method | Path | Returns | Mock file |
|---|---|---|---|
| GET | /api/graph | nodes + edges for the graph picture | mocks/graph.json |
| GET | /api/incidents | list of alarms | mocks/incidents.json |
| GET | /api/incidents/{id} | affected pages, chains, trace, fix, client message | mocks/incident.json |
| POST | /api/incidents/{id}/approve | { "pr_url": "..." } | mocks/approve.json |
| POST | /api/ask  body { "question": "..." } | { answer, trace } | mocks/ask.json |
| GET | /api/spof | risky domains, most sites first | mocks/spof.json |
