"""
Minimal clients for the two LLMs used in the project, via their REST APIs.

    Gemini (Google)      https://aistudio.google.com/apikey
    Groq (open models)   https://console.groq.com/keys

Every call returns the text plus time and token usage, and is appended to
output/llm_usage.csv (needed for the Step 7 time/cost comparison).
"""
import csv
import time
from datetime import datetime
from pathlib import Path

import requests

PROVIDERS = {
    "Gemini": {"default_model": "gemini-3.5-flash", "key_name": "GEMINI_API_KEY"},
    "Groq": {"default_model": "openai/gpt-oss-120b", "key_name": "GROQ_API_KEY"},
}
USAGE_LOG = Path("output/llm_usage.csv")


def _gemini(model, api_key, system, messages):
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
    body = {
        "system_instruction": {"parts": [{"text": system}]},
        "contents": [{"role": "model" if m["role"] == "assistant" else "user", "parts": [{"text": m["content"]}]}
                     for m in messages],
        "generationConfig": {"temperature": 0},
    }
    r = requests.post(url, json=body, headers={"x-goog-api-key": api_key}, timeout=120)
    r.raise_for_status()
    data = r.json()
    text = "".join(p.get("text", "") for p in data["candidates"][0]["content"]["parts"])
    usage = data.get("usageMetadata", {})
    tok_in = usage.get("promptTokenCount", 0)
    # output = answer + "thinking" tokens (both are billed); Gemini reports them separately
    tok_out = usage.get("totalTokenCount", 0) - tok_in
    return text, tok_in, tok_out


def _groq(model, api_key, system, messages):
    r = requests.post(
        "https://api.groq.com/openai/v1/chat/completions",
        json={"model": model, "temperature": 0,
              "messages": [{"role": "system", "content": system}] + messages},
        headers={"Authorization": f"Bearer {api_key}"}, timeout=120)
    r.raise_for_status()
    data = r.json()
    usage = data.get("usage", {})
    return data["choices"][0]["message"]["content"], usage.get("prompt_tokens", 0), usage.get("completion_tokens", 0)


def chat(provider, model, api_key, system, messages, step=""):
    """messages: list of {"role": "user"|"assistant", "content": str}"""
    t0 = time.perf_counter()
    fn = _gemini if provider == "Gemini" else _groq
    for attempt in range(4):  # free tiers often return 429 (rate limit) / 503 (overloaded) for a moment
        try:
            text, tok_in, tok_out = fn(model, api_key, system, messages)
            break
        except requests.HTTPError as e:
            if e.response is None or e.response.status_code not in (429, 500, 503) or attempt == 3:
                raise
            time.sleep(5 * (attempt + 1))
    seconds = time.perf_counter() - t0

    USAGE_LOG.parent.mkdir(exist_ok=True)
    new = not USAGE_LOG.exists()
    with USAGE_LOG.open("a", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        if new:
            w.writerow(["time", "step", "provider", "model", "seconds", "input_tokens", "output_tokens"])
        w.writerow([datetime.now().isoformat(timespec="seconds"), step, provider, model,
                    round(seconds, 2), tok_in, tok_out])
    return {"text": text, "seconds": seconds, "input_tokens": tok_in, "output_tokens": tok_out}
