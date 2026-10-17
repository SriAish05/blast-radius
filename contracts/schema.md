# Rules sheet: graph names (do not change without telling the group)

Graph name: `agency_demo` (one graph per agency)

## Nodes (boxes)

| Label | Properties |
|---|---|
| Client | name |
| Site | url, domain |
| Page | url |
| Script | url, sha256, previous_sha256, has_sri, changed_at, first_seen, last_seen |
| Domain | name, first_party (true/false) |
| Developer | name |
| Advisory | source, reason, date |
| Incident | id, kind (hash_change / advisory), status (open / approved), created_at |

## Relationships (arrows)

| Arrow | Meaning |
|---|---|
| (Client)-[:OWNS]->(Site) | client owns the site |
| (Site)-[:HAS_PAGE]->(Page) | page belongs to site |
| (Page)-[:LOADS {via:'html'}]->(Script) | the page HTML loads the script |
| (Script)-[:LOADS {via:'runtime'}]->(Script) | a script injected another script |
| (Script)-[:SERVED_FROM]->(Domain) | where the script file lives |
| (Developer)-[:MAINTAINS]->(Site) | who to notify |
| (Advisory)-[:FLAGS]->(Domain) | someone reported this domain as bad |
| (Incident)-[:ABOUT]->(Script) | an alarm about this script |

## Rules
- URLs are stored exactly as the browser sees them (full https URL).
- Page URL for a home page ends with `/`.
- Always use parameters in queries, never build Cypher strings by hand.
