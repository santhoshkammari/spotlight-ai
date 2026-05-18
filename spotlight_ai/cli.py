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
  spotlight-keybind [KEY]  register hotkey (default: Ctrl+Space)
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


PID_FILE = os.path.expanduser("~/.spotlight/spotlight.pid")


def _pid_alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False


def _read_pid():
    try:
        with open(PID_FILE) as f:
            pid = int(f.read().strip())
        return pid if _pid_alive(pid) else None
    except Exception:
        return None


def _write_pid():
    os.makedirs(os.path.dirname(PID_FILE), exist_ok=True)
    with open(PID_FILE, "w") as f:
        f.write(str(os.getpid()))


def run():
    """spotlight — toggle the AI bar (single-instance via SIGUSR1)."""
    if "--help" in sys.argv or "-h" in sys.argv:
        print(HELP_TEXT)
        return

    # If a daemon is already running, signal it to toggle and exit.
    existing = _read_pid()
    if existing:
        import signal as _sig
        try:
            os.kill(existing, _sig.SIGUSR1)
            return
        except OSError:
            pass  # stale, fall through and become the daemon

    import signal
    from PyQt5.QtWidgets import QApplication
    from spotlight_ai.ui import Spotlight
    from spotlight_ai.opencode import opencode_stream

    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)

    win = Spotlight(streamer=opencode_stream)

    # SIGUSR1 from subsequent `spotlight` invocations → toggle window.
    # Use emitter signal so toggle runs on the Qt main thread.
    signal.signal(signal.SIGUSR1, lambda *_: win.emitter.toggle.emit())
    signal.signal(signal.SIGINT, lambda *_: app.quit())
    signal.signal(signal.SIGTERM, lambda *_: app.quit())

    # Heartbeat so Python can deliver signals while Qt event loop runs.
    from PyQt5.QtCore import QTimer
    _hb = QTimer()
    _hb.start(200)
    _hb.timeout.connect(lambda: None)

    _write_pid()
    try:
        win.toggle()  # first launch shows it
        sys.exit(app.exec_())
    finally:
        try:
            if _read_pid() == os.getpid():
                os.remove(PID_FILE)
        except Exception:
            pass


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
    ans = input("\n  Register hotkey? [Y/n]: ").strip().lower()
    if ans in ("", "y"):
        custom = input("  Key binding [default: <Control>space]: ").strip()
        if custom:
            sys.argv = [sys.argv[0], custom]
        keybind()
    else:
        print("  skipped — run `spotlight-keybind [BINDING]` anytime")

    print("\n  Done! Press Ctrl+Space to launch Spotlight.\n")


KEYBIND_HELP = """usage: spotlight-keybind [BINDING]

Register a global hotkey for Spotlight AI (GNOME only).

  BINDING   GNOME key string (default: <Control>space)

examples:
  spotlight-keybind                      → Ctrl+Space  (default)
  spotlight-keybind "<Super>space"       → Win+Space
  spotlight-keybind "<Alt>space"         → Alt+Space
  spotlight-keybind "<Control><Alt>s"    → Ctrl+Alt+S

GNOME key format:
  <Control>   Ctrl
  <Super>     Windows/Meta key
  <Alt>       Alt
  <Shift>     Shift
  combine: "<Control><Shift>space"
"""


def keybind():
    """spotlight-keybind [BINDING] — register global hotkey."""
    args = sys.argv[1:]

    if "--help" in args or "-h" in args:
        print(KEYBIND_HELP)
        return

    # pick binding from first non-flag arg, else default
    binding = next((a for a in args if not a.startswith("-")), "<Control>space")

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
        subprocess.run(["gsettings", "set", schema, "name",    "Spotlight AI"], check=True)
        subprocess.run(["gsettings", "set", schema, "command", cmd],          check=True)
        subprocess.run(["gsettings", "set", schema, "binding", binding],      check=True)
        print(f"  ✓ {binding} registered → {cmd}")
    except Exception as e:
        print(f"  ✗ gsettings failed: {e}")
        print("    Are you on GNOME? For KDE/i3/others, add the shortcut manually.")


def help_cmd():
    """spotlight-help — show help text."""
    print(HELP_TEXT)
