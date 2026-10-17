# Blast Radius MCP Server

This MCP (Model Context Protocol) server allows AI assistants such as **Google Antigravity** and **Claude Desktop** to safely query the FalkorDB script blast radius knowledge graph using read-only, structured tools.

No raw or arbitrary Cypher queries are permitted; only the 5 curated domain tools are exposed.

---

## Exposed Tools

| Tool | Description | Arguments | Example Output |
| :--- | :--- | :--- | :--- |
| `blast_radius` | Finds every client, site, and page loading a script or domain, with the full loading chain. | `target`: script name/URL or domain (e.g. `chat-widget.js`) | List of affected sites/pages and runtime loader chains |
| `load_chain` | Finds the shortest dependency loading chain from a web page to a script. | `page`: URL, `script`: name or URL | Ordered list of URLs representing the hop chain |
| `single_points_of_failure` | Identifies 3rd-party domains reaching the most client sites. | `limit`: integer (default: 10) | Top risky domains sorted by site count |
| `scripts_changed_since` | Finds scripts whose content/hash changed after a given timestamp. | `iso_time`: ISO 8601 string (e.g. `2026-01-01`) | Changed scripts with timestamps |
| `owners` | Finds the maintainer/developer responsible for a client website. | `site`: URL or domain | List of developer names |

---

## Connecting to Google Antigravity

### 1. Open MCP Configuration
In Antigravity:
1. Click **Additional Options (...)** or **Settings / Manage MCP Servers**.
2. Click **Edit `mcp_config.json`** (or open `~/.gemini/config/mcp_config.json` directly).

### 2. Add the `blast-radius` Server

Add `blast-radius` under `mcpServers`:

```json
{
  "mcpServers": {
    "blast-radius": {
      "command": "python",
      "args": [
        "D:\\blast-radius\\agent\\mcp_server.py"
      ],
      "env": {
        "FALKORDB_HOST": "localhost",
        "FALKORDB_PORT": "6379"
      }
    }
  }
}
```

### 3. Verify in Antigravity Chat
Start a new chat and ask:
> "Using the blast-radius tools, which client sites are affected if chat-widget.js is hacked?"

Antigravity will automatically discover and call the `blast_radius` tool and list the 3 affected client pages.

---

## Connecting to Claude Desktop

### 1. Locate Claude Desktop Configuration

Open your Claude Desktop configuration file:
- **macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`
- **Windows**: `%APPDATA%\Claude\claude_desktop_config.json`

### 2. Add the MCP Server Configuration

Add `blast-radius` under `mcpServers`:

```json
{
  "mcpServers": {
    "blast-radius": {
      "command": "python",
      "args": [
        "D:\\blast-radius\\agent\\mcp_server.py"
      ],
      "env": {
        "FALKORDB_HOST": "localhost",
        "FALKORDB_PORT": "6379"
      }
    }
  }
}
```

> **Note**: Update the Python command or script path if using a virtual environment (e.g. `"C:\\path\\to\\venv\\Scripts\\python.exe"`).

### 3. Restart Claude Desktop

Restart Claude Desktop. You will see a hammer icon 🔨 indicating that the 5 tools (`blast_radius`, `load_chain`, `single_points_of_failure`, `scripts_changed_since`, `owners`) are available for Claude to call during conversations.

---

## Testing Directly

You can test the MCP server locally using Python:

```bash
python agent/mcp_server.py
```
