import sys
import os
import subprocess
import shutil


def _python() -> str:
    return sys.executable


def _script_path() -> str:
    import spotlight_ai
    return os.path.join(os.path.dirname(spotlight_ai.__file__), "app.py")


def run():
    """spotlight — launch the AI search bar."""
    from PyQt5.QtWidgets import QApplication
    from spotlight_ai.ui import SpotlightLLM
    from spotlight_ai.opencode import opencode_stream
    app = QApplication(sys.argv)
    ex = SpotlightLLM(streamer=opencode_stream)
    ex.show()
    sys.exit(app.exec_())


def setup():
    """spotlight-setup — interactive first-time setup."""
    print("\n✦ Spotlight AI Setup\n")

    # check opencode
    oc = shutil.which("opencode")
    if oc:
        print(f"  ✓ opencode found at {oc}")
    else:
        print("  ✗ opencode not found")
        print("    install: curl -fsSL https://opencode.ai/install | bash")
        print("    then re-run: spotlight-setup")
        return

    # check PyQt5
    try:
        import PyQt5
        print("  ✓ PyQt5 found")
    except ImportError:
        print("  ✗ PyQt5 not found — run: pip install PyQt5")
        return

    # keybind
    ans = input("\n  Register Ctrl+Space hotkey now? [Y/n]: ").strip().lower()
    if ans in ("", "y"):
        keybind()
    else:
        print("  skipped — run `spotlight-keybind` anytime to register it")

    print("\n  ✓ Setup complete! Press Ctrl+Space to launch.\n")


def keybind():
    """spotlight-keybind — register Ctrl+Space GNOME shortcut."""
    python = _python()
    cmd = f"{python} -m spotlight_ai"

    base = "org.gnome.settings-daemon.plugins.media-keys"
    path = "/org/gnome/settings-daemon/plugins/media-keys/custom-keybindings/custom0/"
    schema = f"{base}.custom-keybinding:{path}"

    try:
        subprocess.run(["gsettings", "set", base, "custom-keybindings",
                        f"['{path}']"], check=True)
        subprocess.run(["gsettings", "set", schema, "name", "Spotlight AI"], check=True)
        subprocess.run(["gsettings", "set", schema, "command", cmd], check=True)
        subprocess.run(["gsettings", "set", schema, "binding", "<Control>space"], check=True)
        print(f"  ✓ Ctrl+Space → {cmd}")
    except Exception as e:
        print(f"  ✗ gsettings failed: {e}")
        print("    Are you on GNOME? For other DEs, add the shortcut manually.")


def help_cmd():
    """spotlight-help — show usage."""
    print("""
Spotlight AI — Ctrl+Space AI search bar for Linux

commands:
  spotlight           launch the bar
  spotlight-setup     first-time setup (checks deps, registers hotkey)
  spotlight-keybind   register Ctrl+Space GNOME shortcut
  spotlight-help      this message

slash commands (inside the bar):
  /help               show all slash commands
  /model              show current model
  /models             list all 200+ available models
  /<alias>            switch model  (e.g. /gemini-2.5-flash)
  /<alias> <prompt>   switch + run  (e.g. /claude-sonnet-4.6 explain monads)

model config persists in ~/.spotlight/config.json
""")
