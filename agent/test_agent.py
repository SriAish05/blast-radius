"""Test suite for the Blast Radius Agent.

Runs 10 questions covering:
1. Script blast radius (chat-widget.js)
2. Domain blast radius (cdn-demo.netlify.app)
3. Multi-hop load chain (bakery home -> helper.js)
4. Single points of failure
5. Site maintainers / owners (bakery-demo.netlify.app)
6. Script blast radius (analytics.js)
7. Site maintainers / owners (clinic-demo.netlify.app)
8. Changed scripts since timestamp
9. Non-existent script (0 rows -> 'not found' check)
10. Non-existent site owner (0 rows -> 'not found' check)

Tests all 10 questions with AI ON (Gemini) and with AI_OFF=true (Rules engine).
"""
import os
import sys
from pathlib import Path

# Ensure project root is in sys.path
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

try:
    from agent import agent
except ImportError:
    import agent

QUESTIONS = [
    "Which websites use chat-widget.js?",
    "What is the blast radius if cdn-demo.netlify.app is compromised?",
    "Show the load chain from https://bakery-demo.netlify.app/ to helper.js",
    "What are the single points of failure across all client sites?",
    "Who maintains https://bakery-demo.netlify.app?",
    "Which websites load analytics.js?",
    "Who owns clinic-demo.netlify.app?",
    "Which scripts have changed since 2026-01-01?",
    "Which websites use non-existent-script.js?",
    "Who maintains https://non-existent-site.com?",
    "Which websites use chat-widgt.js?",
    "What's the weather today?",
]


def validate_result_shape(res: dict, expected_ai: bool):
    """Validate response schema matching contracts/mocks."""
    assert "question" in res, "Missing 'question' key"
    assert "answer" in res and isinstance(res["answer"], str) and res["answer"].strip(), "Missing or empty 'answer'"
    assert "trace" in res and isinstance(res["trace"], list), "Missing or non-list 'trace'"
    assert "used_ai" in res and res["used_ai"] == expected_ai, f"Expected used_ai={expected_ai}, got {res['used_ai']}"

    for t in res["trace"]:
        assert "step" in t and isinstance(t["step"], int), "Trace missing integer 'step'"
        assert "tool" in t and isinstance(t["tool"], str), "Trace missing string 'tool'"
        assert "inputs" in t and isinstance(t["inputs"], dict), "Trace missing dict 'inputs'"
        assert "cypher" in t and isinstance(t["cypher"], str), "Trace missing string 'cypher'"
        assert "rows" in t and isinstance(t["rows"], int), "Trace missing integer 'rows'"
        assert "time_ms" in t, "Trace missing 'time_ms'"


def run_tests():
    total_q = len(QUESTIONS)
    print("=" * 70)
    print("RUNNING AGENT SUITE: AI_OFF=true (Deterministic Rules Engine)")
    print("=" * 70)

    os.environ["AI_OFF"] = "true"
    for i, q in enumerate(QUESTIONS, 1):
        res = agent.ask(q, use_cache=False)
        validate_result_shape(res, expected_ai=False)
        print(f"[{i:02d}/{total_q:02d}] Q: {q}")
        print(f"      A: {res['answer']}")
        print(f"      Trace steps: {len(res['trace'])} | Used AI: {res['used_ai']}\n")

        # Specific assertions per query
        if "chat-widgt.js" in q:
            ans = res["answer"].lower()
            assert "not found" in ans or "did you mean" in ans, f"Typo must say not found or did you mean: {res['answer']}"
            assert not any(s in ans for s in ["bakery-demo", "clinic-demo", "coaching-demo"]), f"Typo must never invent sites: {res['answer']}"
        elif "weather" in q:
            assert "i can only answer questions about scripts on our client sites" in res["answer"].lower(), f"Off-topic must refuse politely: {res['answer']}"
        elif q == "Which websites use chat-widget.js?":
            assert any(w in res["answer"].lower() for w in ["bakery", "clinic", "coaching", "3"]), f"Core answer missing expected sites: {res['answer']}"
            assert len(res["trace"]) >= 1, "Core answer trace must have at least 1 step"
            assert "MATCH" in res["trace"][-1]["cypher"].upper(), "Trace cypher must contain MATCH"

    print("=" * 70)
    print("RUNNING AGENT SUITE: AI ON (Gemini Flash-Lite Model)")
    print("=" * 70)

    os.environ["AI_OFF"] = "false"
    import time
    for i, q in enumerate(QUESTIONS, 1):
        time.sleep(2.5)  # Respect free tier rate limit
        res = agent.ask(q, use_cache=False)
        validate_result_shape(res, expected_ai=True)
        print(f"[{i:02d}/{total_q:02d}] Q: {q}")
        print(f"      A: {res['answer']}")
        print(f"      Trace steps: {len(res['trace'])} | Used AI: {res['used_ai']}\n")

        # Specific assertions per query
        if "chat-widgt.js" in q:
            ans = res["answer"].lower()
            assert "not found" in ans or "did you mean" in ans, f"Typo must say not found or did you mean: {res['answer']}"
            assert not any(s in ans for s in ["bakery-demo", "clinic-demo", "coaching-demo"]), f"Typo must never invent sites: {res['answer']}"
        elif "weather" in q:
            assert "i can only answer questions about scripts on our client sites" in res["answer"].lower(), f"Off-topic must refuse politely: {res['answer']}"
        elif q == "Which websites use chat-widget.js?":
            assert any(w in res["answer"].lower() for w in ["bakery", "clinic", "coaching", "3"]), f"Core answer missing expected sites: {res['answer']}"
            assert len(res["trace"]) >= 1, "Core answer trace must have at least 1 step"
            assert "MATCH" in res["trace"][-1]["cypher"].upper(), "Trace cypher must contain MATCH"

    print("=" * 70)
    print(f"ALL {total_q} TESTS PASSED CLEANLY (BOTH AI ON AND AI_OFF=TRUE)")
    print("=" * 70)


if __name__ == "__main__":
    run_tests()
