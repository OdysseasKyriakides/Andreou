"""
Minimal client for the two LLMs used in the project. Both run locally with Ollama
(http://localhost:11434), so there are no API keys, quotas or money costs.

    Gemma   bpm-gemma4   Google Gemma 4 12B          built from models/gemma.Modelfile
    Qwen    bpm-qwen     Alibaba Qwen 2.5 Coder 14B  built from models/qwen.Modelfile

Build once:  ollama create bpm-gemma4 -f models/gemma.Modelfile
             ollama create bpm-qwen   -f models/qwen.Modelfile

Every call returns the text plus time and token usage, and is appended to
output/llm_usage.csv (needed for the Step 7 time/cost comparison).
"""
import csv
import os
import time
from datetime import datetime
from pathlib import Path

import requests

PROVIDERS = {
    "Gemma": {"default_model": "bpm-gemma4"},
    "Qwen": {"default_model": "bpm-qwen"},
}
OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://localhost:11434")
USAGE_LOG = Path("output/llm_usage.csv")


def _ollama(model, system, messages):
    body = {"model": model, "stream": False, "options": {"temperature": 0},
            "messages": [{"role": "system", "content": system}] + messages}
    if "gemma" in model:
        # Gemma 4 "thinking" ran for ~15k tokens / 220 s and returned an empty answer; turn it off
        body["think"] = False
    r = requests.post(f"{OLLAMA_URL}/api/chat", json=body, timeout=900)
    r.raise_for_status()
    data = r.json()
    load_s = data.get("load_duration", 0) / 1e9  # time to load the model into the GPU (not inference)
    return data["message"]["content"], data.get("prompt_eval_count", 0), data.get("eval_count", 0), load_s


def chat(provider, model, system, messages, step=""):
    """messages: list of {"role": "user"|"assistant", "content": str}"""
    t0 = time.perf_counter()
    text, tok_in, tok_out, load_s = _ollama(model, system, messages)
    seconds = time.perf_counter() - t0 - load_s  # response time without model loading (fair for Step 7)

    USAGE_LOG.parent.mkdir(exist_ok=True)
    new = not USAGE_LOG.exists()
    with USAGE_LOG.open("a", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        if new:
            w.writerow(["time", "step", "provider", "model", "seconds", "load_seconds", "input_tokens",
                        "output_tokens"])
        w.writerow([datetime.now().isoformat(timespec="seconds"), step, provider, model,
                    round(seconds, 2), round(load_s, 2), tok_in, tok_out])
    return {"text": text, "seconds": seconds, "input_tokens": tok_in, "output_tokens": tok_out}


def unload(model):
    """Free the GPU memory of a model (two ~10 GB models do not fit in 16 GB VRAM together)."""
    try:
        requests.post(f"{OLLAMA_URL}/api/generate", json={"model": model, "keep_alive": 0}, timeout=60)
    except requests.RequestException:
        pass
