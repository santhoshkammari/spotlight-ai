import subprocess
import json
import shutil
from typing import Iterator
from spotlight_ai.slash import get_current_model


def _opencode_bin() -> str:
    # prefer system PATH, fall back to default install location
    found = shutil.which("opencode")
    if found:
        return found
    return "/home/ntlpt24/.opencode/bin/opencode"


def opencode_stream(prompt: str, model: str = None) -> Iterator[str]:
    if model is None:
        model = get_current_model()
    cmd = [_opencode_bin(), "run", "--format", "json", "-m", model, prompt]

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
