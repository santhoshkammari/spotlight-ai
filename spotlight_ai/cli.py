import sys
import os
import subprocess
import shutil

HELP_TEXT = """
Spotlight AI — Ctrl+Space AI search bar for Linux
powered by OpenCode (200+ free models)

usage:
  spotlight                launch the bar
  spotlight --help         show this help
  spotlight-setup          install deps + register Ctrl+Space hotkey
  spotlight-keybind        just register the Ctrl+Space hotkey
  spotlight-help           show this help

slash commands (inside the bar):
  /help                    show slash command menu
  /model                   show current active model
  /models                  list all available models (fetched live)
  /<alias>                 switch model   e.g. /gemini-2.5-flash
  /<alias> <prompt>        switch + ask   e.g. /deepseek what is rust?

model is persisted in ~/.spotlight/config.json
press Esc inside the bar to close it
"""


def run():
    """spotlight — launch the AI bar (or show help with --help)."""
    if "--help" in sys.argv or "-h" in sys.argv:
        print(HELP_TEXT)
        return

    from PyQt5.QtWidgets import QApplication
    from spotlight_ai.ui import SpotlightLLM
    from spotlight_ai.opencode import opencode_stream

    app = QApplication(sys.argv)
    ex = SpotlightLLM(streamer=opencode_stream)
    ex.show()
    sys.exit(app.exec_())


def setup():
    """spotlight-setup — install deps and register hotkey."""
    if "--help" in sys.argv or "-h" in sys.argv:
        print("usage: spotlight-setup\n\nInstalls opencode + PyQt5 and registers Ctrl+Space.")
        return

    print("\nSpotlight AI — Setup\n")

    # ── opencode ──────────────────────────────────────────────
    oc = shutil.which("opencode")
    if oc:
        print(f"  ✓ opencode  ({oc})")
    else:
        print("  • opencode not found — installing...")
        try:
            subprocess.run(
                'curl -fsSL https://opencode.ai/install | bash',
                shell=True, check=True
            )
            # reload PATH
            oc = shutil.which("opencode") or os.path.expanduser("~/.opencode/bin/opencode")
            if os.path.exists(oc):
                print(f"  ✓ opencode installed ({oc})")
            else:
                print("  ✗ opencode install may need a new shell — run: source ~/.bashrc")
                print("    then re-run: spotlight-setup")
        except subprocess.CalledProcessError as e:
            print(f"  ✗ opencode install failed: {e}")
            print("    try manually: curl -fsSL https://opencode.ai/install | bash")
            return

    # ── PyQt5 ─────────────────────────────────────────────────
    try:
        import PyQt5  # noqa
        print("  ✓ PyQt5")
    except ImportError:
        print("  • PyQt5 not found — installing...")
        try:
            subprocess.run([sys.executable, "-m", "pip", "install", "PyQt5"], check=True)
            print("  ✓ PyQt5 installed")
        except subprocess.CalledProcessError:
            # try sudo apt as fallback
            print("  • pip install failed, trying apt...")
            try:
                subprocess.run(
                    ["sudo", "apt-get", "install", "-y", "python3-pyqt5"],
                    check=True
                )
                print("  ✓ PyQt5 installed via apt")
            except subprocess.CalledProcessError as e:
                print(f"  ✗ could not install PyQt5: {e}")
                print("    try: pip install PyQt5  or  sudo apt install python3-pyqt5")
                return

    # ── keybind ───────────────────────────────────────────────
    ans = input("\n  Register Ctrl+Space hotkey? [Y/n]: ").strip().lower()
    if ans in ("", "y"):
        keybind()
    else:
        print("  skipped — run `spotlight-keybind` anytime")

    print("\n  Done! Press Ctrl+Space to launch Spotlight.\n")


def keybind():
    """spotlight-keybind — register Ctrl+Space GNOME shortcut."""
    if "--help" in sys.argv or "-h" in sys.argv:
        print("usage: spotlight-keybind\n\nRegisters Ctrl+Space as global hotkey (GNOME only).")
        return

    python = sys.executable
    cmd = f"{python} -m spotlight_ai"

    base = "org.gnome.settings-daemon.plugins.media-keys"
    path = "/org/gnome/settings-daemon/plugins/media-keys/custom-keybindings/custom0/"
    schema = f"{base}.custom-keybinding:{path}"

    # preserve any existing custom keybindings, just append/update custom0
    try:
        existing = subprocess.check_output(
            ["gsettings", "get", base, "custom-keybindings"], text=True
        ).strip()
        if path not in existing:
            if existing in ("@as []", "[]"):
                new_val = f"['{path}']"
            else:
                new_val = existing.rstrip("]") + f", '{path}']"
            subprocess.run(["gsettings", "set", base, "custom-keybindings", new_val], check=True)
    except Exception:
        subprocess.run(["gsettings", "set", base, "custom-keybindings", f"['{path}']"], check=True)

    try:
        subprocess.run(["gsettings", "set", schema, "name",    "Spotlight AI"],     check=True)
        subprocess.run(["gsettings", "set", schema, "command", cmd],                check=True)
        subprocess.run(["gsettings", "set", schema, "binding", "<Control>space"],   check=True)
        print(f"  ✓ Ctrl+Space registered → {cmd}")
    except Exception as e:
        print(f"  ✗ gsettings failed: {e}")
        print("    Are you on GNOME? For KDE/i3/others, add the shortcut manually.")


def help_cmd():
    """spotlight-help — show help text."""
    print(HELP_TEXT)
