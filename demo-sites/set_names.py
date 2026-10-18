"""If a Netlify name was taken, run this to switch every link in one go.

Example (only list the ones that changed):
    python demo-sites/set_names.py cdn-demo=br26-cdn bakery-demo=br26-bakery

It updates the demo site HTML and contracts/answer_key.json.
Then rebuild the map once:  python seed/seed_graph.py
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
files = list((ROOT / "demo-sites").rglob("*.html")) + [ROOT / "contracts" / "answer_key.json"]
pairs = [a.split("=", 1) for a in sys.argv[1:]]
if not pairs:
    sys.exit(__doc__)
for f in files:
    text = f.read_text(encoding="utf-8")
    new = text
    for old, name in pairs:
        new = new.replace(f"https://{old}.netlify.app", f"https://{name}.netlify.app")
    if new != text:
        f.write_text(new, encoding="utf-8")
        print("updated", f.relative_to(ROOT))
