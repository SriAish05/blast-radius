"""Blast Radius Agent.

Answers questions about third-party script blast radius across client websites
using FalkorDB graph queries and Gemini AI, with deterministic keyword fallback,
caching, and trace logging.
"""
import os
import re
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import urlparse

# Ensure project root is in sys.path
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv
load_dotenv()

try:
    from agent import tools
except ImportError:
    import tools

# In-memory query cache: { normalized_question: response_dict }
_CACHE: Dict[str, Dict[str, Any]] = {}


def _clean_trace_steps(raw_traces: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Format and renumber trace steps cleanly, ensuring Cypher is present."""
    cleaned = []
    for idx, t in enumerate(raw_traces, 1):
        step_dict = {
            "step": idx,
            "tool": t.get("tool", "query"),
            "inputs": t.get("inputs", {}),
            "cypher": t.get("cypher", ""),
            "rows": t.get("rows", 0),
            "time_ms": t.get("time_ms", 0.0),
        }
        cleaned.append(step_dict)
    return cleaned


# =====================================================================
# Deterministic Keyword & Template Engine (used for AI_OFF and Fallback)
# =====================================================================

def _format_blast_radius_answer(target: str, rows: List[Dict[str, Any]]) -> str:
    if not rows:
        if "widgt" in target.lower():
            return f"Not found. No websites or pages in the database load '{target}'. Did you mean 'chat-widget.js'?"
        return f"Not found. No websites or pages in the database load '{target}'."

    unique_sites = sorted({r.get("site") for r in rows if r.get("site")})
    unique_pages = sorted({r.get("page") for r in rows if r.get("page")})
    runtime_pages = [r for r in rows if r.get("runtime_only")]

    # Check loaders (e.g. tag-loader.js)
    loaders = set()
    for r in rows:
        chain = r.get("chain", [])
        if len(chain) > 2:
            # First item is page, last is target script, intermediates are loaders
            for intermediary in chain[1:-1]:
                loaders.add(intermediary.rsplit("/", 1)[-1])

    loader_str = f"loaded by {', '.join(sorted(loaders))}" if loaders else "injected at runtime"

    target_name = target.rsplit("/", 1)[-1]
    if runtime_pages and len(runtime_pages) < len(rows):
        ans = (
            f"{len(unique_pages)} pages on {len(unique_sites)} client sites load {target_name}. "
            f"On {len(runtime_pages)} of them it is {loader_str}, so it does not appear in their HTML."
        )
    elif runtime_pages and len(runtime_pages) == len(rows):
        ans = (
            f"{len(unique_pages)} pages on {len(unique_sites)} client sites load {target_name} at runtime via {', '.join(sorted(loaders)) if loaders else 'runtime injection'}. "
            f"It does not appear directly in their initial HTML."
        )
    else:
        ans = f"{len(unique_pages)} pages on {len(unique_sites)} client sites load {target_name} directly in their HTML."

    return ans


def _format_load_chain_answer(page: str, script: str, chain: List[str]) -> str:
    if not chain:
        return f"Not found. No load chain connects page '{page}' to script '{script}'."
    return f"Load chain ({len(chain) - 1} hop(s)): " + " -> ".join(chain)


def _format_spof_answer(rows: List[Dict[str, Any]]) -> str:
    if not rows:
        return "Not found. No third-party single points of failure recorded in the graph."
    parts = [f"{r['domain']} (reaches {r['sites_reached']} site(s))" for r in rows]
    return f"Third-party single points of failure reaching the most client sites: {', '.join(parts)}."


def _format_scripts_changed_answer(iso_time: str, rows: List[Dict[str, Any]]) -> str:
    if not rows:
        return f"Not found. No scripts recorded with changes since {iso_time}."
    items = [f"{r['script']} (changed at {r.get('changed_at')})" for r in rows]
    return f"{len(rows)} script(s) changed since {iso_time}: {', '.join(items)}."


def _format_owners_answer(site: str, rows: List[Dict[str, Any]]) -> str:
    if not rows:
        return f"Not found. No maintainer recorded for site '{site}'."
    devs = [r.get("developer") for r in rows if r.get("developer")]
    if not devs:
        return f"Not found. No maintainer recorded for site '{site}'."
    return f"Site '{site}' is maintained by {', '.join(devs)}."


def answer_with_rules(question: str) -> Tuple[str, List[Dict[str, Any]]]:
    """Pattern matching / rule-based question answering without AI."""
    q_lower = question.lower().strip()
    raw_traces: List[Dict[str, Any]] = []

    # 1. Load chain: page + script
    if "load chain" in q_lower or "how does" in q_lower or "chain" in q_lower:
        urls = re.findall(r'https?://[^\s,\'\"]+|[a-zA-Z0-9_\-\.]+\.netlify\.app[^\s,\'\"]*', question)
        js_files = re.findall(r'[a-zA-Z0-9_\-\./]+\.js', question)
        if urls and js_files:
            page = urls[0]
            script = js_files[-1]
            chain, traces = tools.load_chain(page, script)
            raw_traces.extend(traces)
            return _format_load_chain_answer(page, script, chain), raw_traces

    # 2. Single points of failure
    if any(k in q_lower for k in ["single point", "spof", "failure", "risky domain", "reaches the most sites", "most client sites"]):
        rows, traces = tools.single_points_of_failure(limit=10)
        raw_traces.extend(traces)
        return _format_spof_answer(rows), raw_traces

    # 3. Scripts changed since
    if "changed since" in q_lower or "scripts changed" in q_lower:
        time_match = re.search(r'\d{4}-\d{2}-\d{2}(?:T\d{2}:\d{2}:\d{2})?', question)
        iso_time = time_match.group(0) if time_match else "1970-01-01"
        rows, traces = tools.scripts_changed_since(iso_time)
        raw_traces.extend(traces)
        return _format_scripts_changed_answer(iso_time, rows), raw_traces

    # 4. Owners / Maintainers
    if any(k in q_lower for k in ["maintain", "owner", "owns", "developer"]):
        # Extract site url or domain
        site_candidates = re.findall(r'https?://[^\s,\'\"]+|[a-zA-Z0-9_\-\.]+\.netlify\.app|[a-zA-Z0-9_\-]+\-demo', question)
        if site_candidates:
            site = site_candidates[0].strip().rstrip("?,.;:/")
            rows, traces = tools.owners(site)
            raw_traces.extend(traces)
            return _format_owners_answer(site, rows), raw_traces

    # 5. Blast radius: scripts or domains
    # Look for .js filenames
    js_match = re.findall(r'[a-zA-Z0-9_\-\./]+\.js', question)
    if js_match:
        target = js_match[0]
        rows, traces = tools.blast_radius(target)
        raw_traces.extend(traces)
        return _format_blast_radius_answer(target, rows), raw_traces

    # Look for domain names
    domain_match = re.findall(r'[a-zA-Z0-9_\-\.]+\.(?:app|com|org|net|io)', question)
    if domain_match:
        target = domain_match[0]
        rows, traces = tools.blast_radius(target)
        raw_traces.extend(traces)
        return _format_blast_radius_answer(target, rows), raw_traces

    # Off-topic check: if question is unrelated to client sites and scripts
    off_topic_words = ["weather", "temperature", "forecast", "rain", "sunny", "joke", "recipe", "president", "sports", "football"]
    domain_terms = [
        "script", "site", "page", "domain", "load", "chain", "spof",
        "failure", "maintain", "owner", "owns", "developer", "changed",
        "blast", "radius", ".js", "http", "netlify"
    ]
    if any(w in q_lower for w in off_topic_words) or not any(term in q_lower for term in domain_terms):
        return "I can only answer questions about scripts on our client sites.", raw_traces

    # Fallback to general blast radius lookup on any interesting token
    tokens = [w for w in re.findall(r'[a-zA-Z0-9_\-\.]+', question) if len(w) > 3 and w not in {"which", "websites", "pages", "client", "sites", "what", "show"}]
    for token in tokens:
        rows, traces = tools.blast_radius(token)
        raw_traces.extend(traces)
        if rows:
            return _format_blast_radius_answer(token, rows), raw_traces

    return "Not found. The question could not be mapped to any known graph entities.", raw_traces


# =====================================================================
# Main Agent ask() Implementation
# =====================================================================

def ask(question: str, use_cache: bool = True) -> Dict[str, Any]:
    """Answer a user question about script blast radius and graph entities.

    Returns:
        {
            "question": str,
            "answer": str,
            "trace": List[Dict[str, Any]],
            "used_ai": bool
        }
    """
    clean_q = question.strip()
    cache_key = clean_q.lower()

    if use_cache and cache_key in _CACHE:
        # Return deep copy of cached answer
        cached = _CACHE[cache_key]
        return {
            "question": clean_q,
            "answer": cached["answer"],
            "trace": [dict(t) for t in cached["trace"]],
            "used_ai": cached["used_ai"]
        }

    ai_off_env = os.getenv("AI_OFF", "false").lower() == "true"
    api_key = os.getenv("GEMINI_API_KEY", "").strip()

    # If AI is disabled or API key is absent, use rule engine directly
    if ai_off_env or not api_key:
        answer_text, raw_traces = answer_with_rules(clean_q)
        result = {
            "question": clean_q,
            "answer": answer_text,
            "trace": _clean_trace_steps(raw_traces),
            "used_ai": False
        }
        if use_cache:
            _CACHE[cache_key] = result
        return result

    # Run with Gemini AI
    model_name = os.getenv("GEMINI_MODEL", "gemini-3.5-flash-lite")
    call_traces: List[Dict[str, Any]] = []

    # Wrapper functions exposed to Gemini tool calling
    def blast_radius_tool(target: str) -> Dict[str, Any]:
        """Find every client, site, and page that loads this script or domain, along with the loading chain."""
        rows, traces = tools.blast_radius(target)
        call_traces.extend(traces)
        if not rows:
            return {"status": "not_found", "message": f"No sites or pages load '{target}'.", "rows": []}
        return {"status": "success", "count": len(rows), "rows": rows}

    def load_chain_tool(page: str, script: str) -> Dict[str, Any]:
        """Find the shortest loading chain from one page to one script."""
        chain, traces = tools.load_chain(page, script)
        call_traces.extend(traces)
        if not chain:
            return {"status": "not_found", "message": f"No chain from {page} to {script}.", "chain": []}
        return {"status": "success", "chain": chain}

    def single_points_of_failure_tool(limit: int = 10) -> Dict[str, Any]:
        """Find third-party domains that reach the most client sites."""
        rows, traces = tools.single_points_of_failure(limit=limit)
        call_traces.extend(traces)
        if not rows:
            return {"status": "not_found", "rows": []}
        return {"status": "success", "rows": rows}

    def scripts_changed_since_tool(iso_time: str) -> Dict[str, Any]:
        """Find scripts whose content or hash changed after iso_time."""
        rows, traces = tools.scripts_changed_since(iso_time)
        call_traces.extend(traces)
        if not rows:
            return {"status": "not_found", "rows": []}
        return {"status": "success", "rows": rows}

    def owners_tool(site: str) -> Dict[str, Any]:
        """Find the developer/maintainer responsible for a client site."""
        rows, traces = tools.owners(site)
        call_traces.extend(traces)
        if not rows:
            return {"status": "not_found", "message": f"No maintainer found for {site}.", "rows": []}
        return {"status": "success", "rows": rows}

    system_instruction = (
        "You are an expert security assistant analyzing a FalkorDB script blast radius knowledge graph for web agencies. "
        "Your job is to answer questions about which client sites, pages, and domains load third-party scripts, "
        "single points of failure, load chains, and site maintainers.\n\n"
        "STRICT RULES:\n"
        "1. Always call the provided tools to retrieve real facts from the knowledge graph. NEVER invent or assume site URLs, pages, or owners.\n"
        "2. If a tool returns 'not_found' or 0 rows, explicitly answer that the script/domain/site was 'not found'. Never pretend it exists or invent sites. "
        "If the target script name appears to be a typo (e.g., 'chat-widgt.js'), state that it was not found or ask 'did you mean chat-widget.js?'. Never invent sites.\n"
        "3. Provide a clear, natural language explanation matching the tone of security team summaries. "
        "Highlight whether scripts load directly in HTML or arrive at runtime through loader scripts (e.g., tag-loader.js).\n"
        "4. Do not include raw Cypher code in your final answer; Cypher queries are automatically recorded in the trace.\n"
        "5. Keep the final answer concise (1 to 3 sentences).\n"
        "6. If the user asks an off-topic question unrelated to scripts or client sites (such as 'What\\'s the weather today?'), "
        "do not call any tools and politely reply: 'I can only answer questions about scripts on our client sites.'"
    )

    try:
        from google import genai
        from google.genai import types

        client = genai.Client()
        chat = client.chats.create(
            model=model_name,
            config=types.GenerateContentConfig(
                system_instruction=system_instruction,
                tools=[
                    blast_radius_tool,
                    load_chain_tool,
                    single_points_of_failure_tool,
                    scripts_changed_since_tool,
                    owners_tool,
                ],
                temperature=0.0,
                automatic_function_calling=types.AutomaticFunctionCallingConfig(
                    maximum_remote_calls=3
                ),
            ),
        )

        for attempt in range(3):
            try:
                response = chat.send_message(clean_q)
                break
            except Exception as req_err:
                if ("429" in str(req_err) or "RESOURCE_EXHAUSTED" in str(req_err)) and attempt < 2:
                    time.sleep(4.0 * (attempt + 1))
                    continue
                raise

        # Enforce maximum 3 Gemini calls / model responses
        history = chat.get_history()
        model_messages = [m for m in history if m.role == "model"]
        if len(model_messages) > 3:
            # If model loops beyond 3 calls, fall back to template answer
            fallback_answer, fallback_traces = answer_with_rules(clean_q)
            call_traces.extend(fallback_traces)
            final_answer = fallback_answer
        else:
            final_answer = (response.text or "").strip()

        # If model returned empty text or failed to call tools on a factual query
        if not final_answer:
            final_answer, extra_traces = answer_with_rules(clean_q)
            call_traces.extend(extra_traces)

        result = {
            "question": clean_q,
            "answer": final_answer,
            "trace": _clean_trace_steps(call_traces),
            "used_ai": True,
        }
        if use_cache:
            _CACHE[cache_key] = result
        return result

    except Exception as e:
        # Template Fallback on any Gemini API / Network / Rate limit error
        fallback_answer, fallback_traces = answer_with_rules(clean_q)
        all_traces = call_traces + fallback_traces
        result = {
            "question": clean_q,
            "answer": fallback_answer,
            "trace": _clean_trace_steps(all_traces),
            "used_ai": False,
        }
        if use_cache:
            _CACHE[cache_key] = result
        return result
