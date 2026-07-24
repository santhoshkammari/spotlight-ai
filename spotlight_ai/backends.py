"""Local vLLM and Claude Code streaming backends for Spotlight.

Both are plain "run process / hit http, yield growing text" generators —
same shape as opencode_stream in opencode.py — so ui.py can swap between
them without caring which backend is active.
"""
import json
import os
import shutil
import subprocess
import threading
from typing import Iterator

import httpx

LOCAL_URL = os.environ.get("SPOTLIGHT_LOCAL_URL", "http://192.168.170.49:8000")


def _claude_bin() -> str:
    found = shutil.which("claude")
    return found or "claude"


def claude_stream(prompt: str, model: str = None, cancel_event: threading.Event = None) -> Iterator[str]:
    """Stream text deltas from `claude -p --dangerously-skip-permissions`."""
    cmd = [
        _claude_bin(), "-p", prompt,
        "--dangerously-skip-permissions",
        "--output-format", "stream-json",
        "--include-partial-messages",
        "--verbose",
    ]
    if model:
        cmd += ["--model", model]

    proc = subprocess.Popen(
        cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
        bufsize=1,
    )
    text = ""
    try:
        for line in proc.stdout:
            if cancel_event and cancel_event.is_set():
                return
            line = line.strip()
            if not line:
                continue
            try:
                ev = json.loads(line)
            except json.JSONDecodeError:
                continue

            if ev.get("type") == "stream_event":
                inner = ev.get("event", {})
                if inner.get("type") == "content_block_delta":
                    delta = inner.get("delta", {})
                    if delta.get("type") == "text_delta":
                        text += delta.get("text", "")
                        yield text
            elif ev.get("type") == "result":
                if ev.get("subtype") != "success" and ev.get("result"):
                    text += f"\n[error: {ev.get('result')}]"
                    yield text
    finally:
        if proc.poll() is None:
            proc.terminate()


def local_stream(prompt: str, model: str = None, cancel_event: threading.Event = None) -> Iterator[str]:
    """Stream text deltas from a local OpenAI-compatible vLLM server."""
    base_url = LOCAL_URL.rstrip("/")
    if not base_url.endswith("/v1"):
        base_url += "/v1"

    body = {
        "model": model or "auto",
        "messages": [{"role": "user", "content": prompt}],
        "stream": True,
    }

    text = ""
    try:
        with httpx.stream(
            "POST", f"{base_url}/chat/completions", json=body, timeout=120.0
        ) as resp:
            resp.raise_for_status()
            for raw_line in resp.iter_lines():
                if cancel_event and cancel_event.is_set():
                    return
                if not raw_line.startswith("data:"):
                    continue
                payload = raw_line[len("data:"):].strip()
                if not payload or payload == "[DONE]":
                    continue
                try:
                    chunk = json.loads(payload)
                except json.JSONDecodeError:
                    continue
                choices = chunk.get("choices") or []
                if not choices:
                    continue
                delta = choices[0].get("delta", {})
                piece = delta.get("content")
                if piece:
                    text += piece
                    yield text
    except Exception as e:
        yield f"[local error: {e}]"
