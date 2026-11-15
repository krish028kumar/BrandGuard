"""Run this on your laptop to see the REAL OpenRouter response.
Usage (PowerShell, inside the BrandGuard folder):
    python openrouter_test.py                      # uses key/model from .streamlit/secrets.toml
    python openrouter_test.py openai/gpt-4o-mini   # or pass a model name
Your key is never printed. Paste the output back (it contains no key)."""
import json, os, sys, urllib.request, urllib.error

def read_secrets():
    try:
        import tomllib
        with open(os.path.join(".streamlit", "secrets.toml"), "rb") as f:
            return tomllib.load(f)
    except Exception:
        return {}

sec = read_secrets()
key = os.environ.get("OPENROUTER_API_KEY") or next((sec[k] for k in ("OPENROUTER_API_KEY", "OPENROUTER_KEY", "API_KEY") if k in sec), "")
model = (sys.argv[1] if len(sys.argv) > 1 else os.environ.get("MODEL") or sec.get("MODEL") or sec.get("OPENROUTER_MODEL") or "openai/gpt-4o-mini")
if not key:
    sys.exit("No key found. Set $env:OPENROUTER_API_KEY or add OPENROUTER_API_KEY to .streamlit/secrets.toml")
print("Model:", model, "| key length:", len(key), "| key starts with:", key[:6] + "...")

def call(extra):
    body = {"model": model, "temperature": 0, "max_tokens": 800,
            "messages": [{"role": "user", "content": 'Reply with ONLY this JSON: {"verdict":"SAFE","note":"ok"}'}]}
    body.update(extra)
    req = urllib.request.Request("https://openrouter.ai/api/v1/chat/completions", data=json.dumps(body).encode(),
        headers={"Authorization": "Bearer " + key, "Content-Type": "application/json", "X-Title": "BrandGuard"})
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return r.status, r.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", "replace")
    except Exception as e:
        return 0, "NETWORK ERROR: %r" % e

for label, extra in (("A) plain request", {}), ("B) with response_format=json_object", {"response_format": {"type": "json_object"}})):
    status, raw = call(extra)
    print("\n=====", label, "=====")
    print("HTTP status:", status)
    print("Raw body (first 1200 chars):\n", raw[:1200])
    try:
        j = json.loads(raw)
        print("\nTop-level keys:", list(j.keys()))
        if "error" in j:
            print("ERROR OBJECT:", j["error"])
        ch = (j.get("choices") or [None])[0]
        if ch:
            m = ch.get("message") or {}
            print("finish_reason:", ch.get("finish_reason"), "| message keys:", list(m.keys()))
            c = m.get("content")
            print("content type:", type(c).__name__, "| content:", repr(c)[:300])
    except Exception as e:
        print("Body is not valid JSON:", repr(e))
