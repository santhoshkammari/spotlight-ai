"""opencode streaming backend for Spotlight.

Runs one `opencode serve` process for the life of the app and streams real
token deltas over its SSE `/event` feed (message.part.delta), instead of
shelling out to `opencode run` per query and faking a per-word reveal after
the full reply lands.
"""
import asyncio
import json
import shutil
import threading
from typing import Iterator

import httpx

from spotlight_ai.slash import get_current_model


def _opencode_bin() -> str:
    found = shutil.which("opencode")
    if found:
        return found
    return "/home/ntlpt24/.opencode/bin/opencode"


class _OpencodeServer:
    """Lazily-started `opencode serve` + one persistent session.

    Owns a background asyncio event loop thread so the sync `opencode_stream`
    generator (called from a plain threading.Thread by ui.py) can drive async
    httpx/SSE calls without the caller needing to know about asyncio.
    """

    def __init__(self):
        self._loop = None
        self._loop_thread = None
        self._client: httpx.AsyncClient | None = None
        self._base_url = None
        self._session_id = None
        self._proc = None
        self._lock = threading.Lock()

    def _ensure_loop(self):
        if self._loop is not None:
            return
        self._loop = asyncio.new_event_loop()
        self._loop_thread = threading.Thread(target=self._loop.run_forever, daemon=True)
        self._loop_thread.start()

    def _run(self, coro):
        self._ensure_loop()
        return asyncio.run_coroutine_threadsafe(coro, self._loop).result()

    async def _start(self):
        proc = await asyncio.create_subprocess_exec(
            _opencode_bin(), "serve", "--port", "0",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        import re
        url = None
        for _ in range(20):
            line = (await proc.stdout.readline()).decode(errors="replace").strip()
            if not line:
                break
            m = re.search(r"https?://[^\s]+", line)
            if m:
                url = m.group(0)
                break
        if not url:
            proc.terminate()
            raise RuntimeError("opencode serve did not report a listen address")

        self._proc = proc
        self._base_url = url
        self._client = httpx.AsyncClient(timeout=120.0)
        r = await self._client.post(f"{self._base_url}/session")
        r.raise_for_status()
        self._session_id = r.json()["id"]

    def ensure_started(self):
        with self._lock:
            if self._client is not None:
                return
            self._run(self._start())

    def stop(self):
        with self._lock:
            if self._loop is None:
                return
            if self._client is not None:
                self._run(self._client.aclose())
            if self._proc is not None:
                self._proc.terminate()
            self._loop.call_soon_threadsafe(self._loop.stop)

    async def _stream_query(self, prompt: str, model: str, cancel_event, out_queue: asyncio.Queue):
        provider, _, model_id = model.partition("/")
        body = {
            "parts": [{"type": "text", "text": prompt}],
            "model": {"providerID": provider, "modelID": model_id},
        }

        seen_message_id = None
        text = ""
        done = asyncio.Event()

        async def listen_events():
            nonlocal seen_message_id, text
            async with self._client.stream(
                "GET", f"{self._base_url}/event", timeout=None
            ) as resp:
                resp.raise_for_status()
                async for raw_line in resp.aiter_lines():
                    if cancel_event and cancel_event.is_set():
                        return
                    if not raw_line.startswith("data:"):
                        continue
                    payload = raw_line[len("data:"):].strip()
                    if not payload:
                        continue
                    try:
                        ev = json.loads(payload)
                    except json.JSONDecodeError:
                        continue

                    etype = ev.get("type")
                    props = ev.get("properties", {})
                    if props.get("sessionID") != self._session_id:
                        continue

                    if etype == "message.part.delta" and props.get("field") == "text":
                        text += props.get("delta", "")
                        await out_queue.put(text)
                    elif etype == "session.idle":
                        done.set()
                        return
                    elif etype == "session.error":
                        await out_queue.put(f"\n[error: {props}]")
                        done.set()
                        return

        listener = asyncio.create_task(listen_events())
        try:
            r = await self._client.post(
                f"{self._base_url}/session/{self._session_id}/message", json=body
            )
            r.raise_for_status()
            await asyncio.wait_for(done.wait(), timeout=120)
        except Exception as e:
            await out_queue.put(f"\n[stream error: {e}]")
        finally:
            listener.cancel()
            await out_queue.put(None)  # sentinel: stream finished

    def stream(self, prompt: str, model: str, cancel_event) -> "Iterator[str]":
        self.ensure_started()
        out_queue: asyncio.Queue = asyncio.Queue()
        asyncio.run_coroutine_threadsafe(
            self._stream_query(prompt, model, cancel_event, out_queue), self._loop
        )

        while True:
            if cancel_event and cancel_event.is_set():
                return
            item = asyncio.run_coroutine_threadsafe(out_queue.get(), self._loop).result()
            if item is None:
                return
            yield item


_server = _OpencodeServer()


def opencode_stream(prompt: str, model: str = None, cancel_event: threading.Event = None) -> Iterator[str]:
    if model is None:
        model = get_current_model()
    yield from _server.stream(prompt, model, cancel_event)


def shutdown():
    """Stop the background opencode serve process. Call on app exit."""
    _server.stop()
