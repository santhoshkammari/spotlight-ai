import subprocess
import json
from typing import Iterator
from slash import get_current_model

OPENCODE_BIN = "/home/ntlpt24/.opencode/bin/opencode"


def _text_from_event(event: dict) -> str | None:
    """One NDJSON line from `opencode run --format json` -> text delta, if any.

    Line shapes (verified live, opencode v1.17.20):
      {"type":"text", "sessionID":..., "part":{"type":"text","text":...}}
    Each "text" event carries the full accumulated text for that part, not a
    delta — so we track per-part text and yield only the new suffix.
    """
    if event.get("type") != "text":
        return None
    part = event.get("part", {})
    return part.get("text", "")


def opencode_stream(prompt: str, model: str = None) -> Iterator[str]:
    if model is None:
        model = get_current_model()
    cmd = [
        OPENCODE_BIN, "run",
        "--format", "json",
        "-m", model,
        prompt,
    ]

    proc = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        text=True,
        bufsize=1,
    )

    last_text = ""
    try:
        for line in proc.stdout:
            line = line.strip()
            if not line:
                continue
            try:
                event = json.loads(line)
            except json.JSONDecodeError:
                continue

            text = _text_from_event(event)
            if text is not None and text != last_text:
                last_text = text
                yield last_text
    finally:
        proc.stdout.close()
        proc.wait()


if __name__ == "__main__":
    print("Testing opencode streamer...")
    for token in opencode_stream("Explain Linux in 3 sentences."):
        print(f"\r{token}", end="", flush=True)
    print()
