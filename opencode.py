import subprocess
import json
from typing import Iterator
from slash import get_current_model

OPENCODE_BIN = "/home/ntlpt24/.opencode/bin/opencode"


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

    full_text = ""
    try:
        for line in proc.stdout:
            line = line.strip()
            if not line:
                continue
            try:
                event = json.loads(line)
            except json.JSONDecodeError:
                continue

            if event.get("type") == "text":
                full_text = event.get("part", {}).get("text", "")
    finally:
        proc.stdout.close()
        proc.wait()

    yield full_text


if __name__ == "__main__":
    print("Testing opencode streamer...")
    for token in opencode_stream("Explain Linux in 3 sentences."):
        print(token, end="", flush=True)
    print()
