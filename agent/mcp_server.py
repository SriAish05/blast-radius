"""Model Context Protocol (MCP) server for Blast Radius graph queries.

Exposes read-only tools to AI assistants (like Claude Desktop) to query
the FalkorDB script blast radius knowledge graph without exposing raw Cypher.
"""
import sys
from pathlib import Path
from typing import Any, Dict, List

# Ensure project root is in sys.path
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv
load_dotenv(ROOT / ".env")

try:
    from agent import tools
except ImportError:
    import tools

try:
    from mcp.server.mcpserver import MCPServer
    server = MCPServer(name="blast-radius-agent")
except ImportError:
    # Support mcp < 2.0 if FastMCP was used
    from mcp.server.fastmcp import FastMCP
    server = FastMCP("blast-radius-agent")


@server.tool()
def blast_radius(target: str) -> List[Dict[str, Any]]:
    """Find every client, site, and page that loads a target script or domain, along with the loading chain.

    Args:
        target: Full script URL, script filename (e.g. 'chat-widget.js'), or domain (e.g. 'cdn-demo.netlify.app').
    """
    rows, _ = tools.blast_radius(target)
    return rows


@server.tool()
def load_chain(page: str, script: str) -> List[str]:
    """Find the shortest dependency loading chain connecting a web page to a script.

    Args:
        page: Full or partial page URL (e.g. 'https://bakery-demo.netlify.app/').
        script: Full URL or script filename (e.g. 'helper.js').
    """
    chain, _ = tools.load_chain(page, script)
    return chain


@server.tool()
def single_points_of_failure(limit: int = 10) -> List[Dict[str, Any]]:
    """Find third-party domains that reach the largest number of client sites.

    Args:
        limit: Maximum number of risky domains to return (default: 10).
    """
    rows, _ = tools.single_points_of_failure(limit=limit)
    return rows


@server.tool()
def scripts_changed_since(iso_time: str) -> List[Dict[str, Any]]:
    """Find third-party scripts whose content or hash has changed after a given timestamp.

    Args:
        iso_time: ISO 8601 timestamp string (e.g. '2026-01-01' or '2026-01-01T00:00:00').
    """
    rows, _ = tools.scripts_changed_since(iso_time)
    return rows


@server.tool()
def owners(site: str) -> List[Dict[str, Any]]:
    """Find the developer or maintainer responsible for a client website.

    Args:
        site: Client website URL or domain name (e.g. 'https://bakery-demo.netlify.app' or 'clinic-demo').
    """
    rows, _ = tools.owners(site)
    return rows


def main():
    """Run the MCP server over stdio transport."""
    server.run()


if __name__ == "__main__":
    main()
