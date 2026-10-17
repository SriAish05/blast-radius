"""Graph query tools for the Blast Radius agent.

These tools wrap graph/queries.py and add helper resolution (e.g. resolving
short script names like 'chat-widget.js' to full URLs using Cypher ENDS WITH).
Each tool returns (result, trace_dict).
"""
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# Ensure project root is in sys.path
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from graph import queries


def resolve_script_url(name_or_url: str) -> Tuple[Optional[str], Optional[Dict[str, Any]]]:
    """Resolve a full or partial script name to its stored full URL using ENDS WITH."""
    clean = name_or_url.strip()
    cypher = (
        "MATCH (sc:Script) "
        "WHERE sc.url = $target OR sc.url ENDS WITH $target "
        "RETURN sc.url AS url LIMIT 1"
    )
    rows, trace = queries.run(cypher, {"target": clean})
    trace["tool"] = "resolve_script_url"
    trace["inputs"] = {"name_or_url": name_or_url}
    if rows and rows[0].get("url"):
        return rows[0]["url"], trace
    return None, trace


def resolve_site_url(name_or_url: str) -> Tuple[Optional[str], Optional[Dict[str, Any]]]:
    """Resolve a full or partial site name/domain to its stored site URL."""
    clean = name_or_url.strip().rstrip("/")
    cypher = (
        "MATCH (s:Site) "
        "WHERE s.url = $target OR s.url = $target_slash OR s.domain = $target OR s.url ENDS WITH $target "
        "RETURN s.url AS url LIMIT 1"
    )
    rows, trace = queries.run(cypher, {"target": clean, "target_slash": clean + "/"})
    trace["tool"] = "resolve_site_url"
    trace["inputs"] = {"name_or_url": name_or_url}
    if rows and rows[0].get("url"):
        return rows[0]["url"], trace
    return None, trace


def resolve_page_url(name_or_url: str) -> Tuple[Optional[str], Optional[Dict[str, Any]]]:
    """Resolve a full or partial page URL."""
    clean = name_or_url.strip()
    cypher = (
        "MATCH (p:Page) "
        "WHERE p.url = $target OR p.url ENDS WITH $target "
        "RETURN p.url AS url LIMIT 1"
    )
    rows, trace = queries.run(cypher, {"target": clean})
    trace["tool"] = "resolve_page_url"
    trace["inputs"] = {"name_or_url": name_or_url}
    if rows and rows[0].get("url"):
        return rows[0]["url"], trace
    return None, trace


def blast_radius(target: str) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """Find affected clients, sites, pages and chains for a script or domain.

    Picks script lookup if target ends with .js or resolves as a script.
    Otherwise searches for domain.
    Returns (rows, list_of_traces).
    """
    traces: List[Dict[str, Any]] = []
    clean = target.strip()

    # If it ends with .js or contains .js, treat as script
    is_script_hint = clean.lower().endswith(".js") or ".js" in clean.lower()

    if is_script_hint or clean.startswith("http://") or clean.startswith("https://"):
        url, r_trace = resolve_script_url(clean)
        if r_trace:
            traces.append(r_trace)
        if url:
            rows, b_trace = queries.blast_radius_script(url)
            b_trace["tool"] = "blast_radius_script"
            b_trace["inputs"] = {"url": url}
            traces.append(b_trace)
            return rows, traces

    # Check if target is a domain or try domain blast radius
    # Clean domain string if passed as URL
    domain = clean
    if domain.startswith("http://") or domain.startswith("https://"):
        from urllib.parse import urlparse
        domain = urlparse(clean).netloc or domain

    rows, d_trace = queries.blast_radius_domain(domain)
    d_trace["tool"] = "blast_radius_domain"
    d_trace["inputs"] = {"domain": domain}
    traces.append(d_trace)

    if not rows and not is_script_hint:
        # Fallback: maybe it's a script without .js
        url, r_trace = resolve_script_url(clean)
        if r_trace:
            traces.append(r_trace)
        if url:
            rows, b_trace = queries.blast_radius_script(url)
            b_trace["tool"] = "blast_radius_script"
            b_trace["inputs"] = {"url": url}
            traces.append(b_trace)
            return rows, traces

    return rows, traces


def load_chain(page: str, script: str) -> Tuple[List[str], List[Dict[str, Any]]]:
    """Find the shortest loading chain from page to script."""
    traces: List[Dict[str, Any]] = []
    page_url, p_trace = resolve_page_url(page)
    if p_trace:
        traces.append(p_trace)
    script_url, s_trace = resolve_script_url(script)
    if s_trace:
        traces.append(s_trace)

    target_page = page_url or page
    target_script = script_url or script

    rows, c_trace = queries.load_chain(target_page, target_script)
    c_trace["tool"] = "load_chain"
    c_trace["inputs"] = {"page": target_page, "script": target_script}
    traces.append(c_trace)

    chain = rows[0]["chain"] if rows else []
    return chain, traces


def single_points_of_failure(limit: int = 10) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """Identify third-party domains reaching the most client sites."""
    rows, trace = queries.single_points_of_failure(limit=limit)
    trace["tool"] = "single_points_of_failure"
    trace["inputs"] = {"limit": limit}
    return rows, [trace]


def scripts_changed_since(iso_time: str) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """Return scripts whose hash changed after iso_time."""
    rows, trace = queries.scripts_changed_since(iso_time)
    trace["tool"] = "scripts_changed_since"
    trace["inputs"] = {"iso_time": iso_time}
    return rows, [trace]


def owners(site: str) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """Return the developers who maintain the given site."""
    traces: List[Dict[str, Any]] = []
    site_url, s_trace = resolve_site_url(site)
    if s_trace:
        traces.append(s_trace)
    target_site = site_url or site
    rows, o_trace = queries.owners(target_site)
    o_trace["tool"] = "owners"
    o_trace["inputs"] = {"site": target_site}
    traces.append(o_trace)
    return rows, traces
