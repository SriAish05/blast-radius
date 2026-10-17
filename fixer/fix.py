"""Fix maker: turns a bad script into a ready-to-approve fix.

For one bad script it builds, per affected client site:
  - an SRI hash of the KNOWN-GOOD copy (never of the live file, which may be the hacked one)
  - a Content-Security-Policy line built from the site's own script domains in the graph
  - a patch preview (HTML before -> after)
  - a short message for the client
Nothing is changed here. A human approves first.

Try it:  python fixer/fix.py
"""
import base64
import hashlib
import sys
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from graph import queries as q  # noqa: E402

KNOWN_GOOD_DIR = ROOT / "fixer" / "known_good"


def sri_hash(content: bytes) -> str:
    """Browser integrity value: the browser refuses the file if even one byte changes."""
    return "sha384-" + base64.b64encode(hashlib.sha384(content).digest()).decode()


def known_good_copy(script_url):
    """Clean copy saved earlier as fixer/known_good/<file name>. None if we don't have it."""
    path = KNOWN_GOOD_DIR / script_url.rsplit("/", 1)[-1]
    return path.read_bytes() if path.exists() else None


def site_domains(site):
    """Every domain this site loads scripts from (directly or through other scripts)."""
    return q.run(
        """
        MATCH (s:Site {url: $site})-[:HAS_PAGE]->(:Page)-[:LOADS*1..5]->(:Script)-[:SERVED_FROM]->(d:Domain)
        RETURN DISTINCT d.name AS domain, d.first_party AS first_party
        ORDER BY domain
        """,
        {"site": site},
    )


def propose_fix(script_url, clean_content=None):
    trace = []
    affected, t = q.blast_radius_script(script_url)
    trace.append({"tool": "blast_radius_script", "inputs": {"url": script_url}, **t})
    if not affected:
        return {"script": script_url, "found": False, "sites": [], "trace": trace,
                "summary": "No client page loads this script. Nothing to fix."}

    name = script_url.rsplit("/", 1)[-1]
    bad_domain = urlparse(script_url).netloc
    clean = clean_content if clean_content is not None else known_good_copy(script_url)
    sri = sri_hash(clean) if clean else None
    sri_note = ("SRI computed from the known-good copy." if sri else
                f"No known-good copy of {name} saved, so no SRI hash yet. "
                f"Save the clean file as fixer/known_good/{name}.")

    sites = {}
    for row in affected:
        s = sites.setdefault(row["site"], {"client": row["client"], "site": row["site"], "pages": []})
        s["pages"].append(row)

    out_sites = []
    for site, info in sites.items():
        doms, t = site_domains(site)
        trace.append({"tool": "site_domains", "inputs": {"site": site}, **t})
        owners, t = q.owners(site)
        trace.append({"tool": "owners", "inputs": {"site": site}, **t})

        allowed = sorted(d["domain"] for d in doms if not d["first_party"] and d["domain"] != bad_domain)
        csp = "Content-Security-Policy: script-src 'self'" + "".join(f" https://{d}" for d in allowed)

        patch_lines = []
        for row in info["pages"]:
            entry = row["chain"][1]  # the script the page HTML itself loads
            if not row["runtime_only"]:
                new_tag = (f'<script src="/vendor/{name}" integrity="{sri}" crossorigin="anonymous"></script>'
                           if sri else f'<script src="/vendor/{name}"></script>  <!-- add SRI once known-good copy is saved -->')
                patch_lines += [f"# {row['page']}  (loads {name} directly)",
                                f'- <script src="{script_url}"></script>',
                                f"+ {new_tag}"]
            else:
                entry_name = entry.rsplit("/", 1)[-1]
                patch_lines += [f"# {row['page']}  (loads {name} at runtime through {entry_name})",
                                f'- <script src="{entry}"></script>',
                                f"+ <!-- {entry_name} paused: it injects {name} at runtime, which SRI cannot protect. "
                                f"Re-enable after the vendor confirms a clean version. -->"]

        owner = owners[0]["developer"] if owners else "the site maintainer"
        n = len(info["pages"])
        message = (f"Hi {info['client']} team, a third-party script used on your website ({name}) changed "
                   f"unexpectedly. It affects {n} page{'s' if n != 1 else ''}. We have prepared a fix that "
                   f"{'pins the safe version and ' if sri else ''}blocks the affected source until it is confirmed safe. "
                   f"We will apply it once you reply OK. - {owner}")

        out_sites.append({"client": info["client"], "site": site, "owner": owner,
                          "pages": [r["page"] for r in info["pages"]],
                          "csp": csp, "patch": "\n".join(patch_lines), "message": message})

    runtime = sum(1 for r in affected if r["runtime_only"])
    return {
        "script": script_url, "found": True, "bad_domain": bad_domain,
        "sri": sri, "sri_note": sri_note,
        "summary": (f"{name} is loaded on {len(affected)} page(s) across {len(out_sites)} client site(s); "
                    f"{runtime} of them only at runtime through another script, so they do not appear in the site's HTML."),
        "sites": out_sites, "trace": trace,
    }


if __name__ == "__main__":
    import json
    print(json.dumps(propose_fix("https://cdn-demo.netlify.app/chat-widget.js"), indent=2)[:3000])
