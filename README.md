# Spotlight AI

A macOS Spotlight-style AI search bar for Linux — press `Ctrl+Space`, ask anything, get answers inline. Powered by [OpenCode CLI](https://opencode.ai) with 200+ free and paid models.

![demo](https://raw.githubusercontent.com/santhoshkammari/spotlight/main/assets/demo.gif)

---

## What it looks like

- Frameless dark glass bar appears at the center of your screen
- Type your question, press Enter
- Answer streams in below — window expands smoothly
- Press `Esc` to dismiss

---

## Features

- **Global hotkey** `Ctrl+Space` — works system-wide via GNOME shortcut
- **200+ models** via OpenCode — DeepSeek, Gemini, Claude, Qwen, Kimi, GLM, and more
- **Slash commands** to switch models on the fly
- **Persistent model config** saved to `~/.spotlight/config.json`
- **Zero latency UI** — shows "thinking..." instantly, answer appears when ready
- **Draggable** — click and drag anywhere on the bar to reposition

---

## Slash Commands

```
/help                     show all commands
/model                    show currently active model
/models                   list all available models (fetched live from opencode)

/<model-alias>            switch model
/<model-alias> <prompt>   switch model AND run prompt immediately
```

### Examples

```
/gemini-2.5-flash
/deepseek-v4-flash-free explain async/await in 3 lines
/kimi-k2-instruct
/claude-sonnet-4.6 write a regex for email validation
```

Aliases are auto-generated from model IDs — the last path segment in lowercase. No hardcoded list. When OpenCode adds new models, they appear automatically.

---

## Setup

### 1. Install dependencies

```bash
# OpenCode CLI
curl -fsSL https://opencode.ai/install | bash

# Python deps
pip install PyQt5
```

### 2. Clone

```bash
git clone https://github.com/santhoshkammari/spotlight.git
cd spotlight
```

### 3. Register Ctrl+Space hotkey (GNOME)

```bash
# Creates a GNOME custom shortcut
SCRIPT_PATH="$(pwd)/app.py"
PYTHON_PATH="$(which python3)"

gsettings set org.gnome.settings-daemon.plugins.media-keys custom-keybindings \
  "['/org/gnome/settings-daemon/plugins/media-keys/custom-keybindings/custom0/']"

gsettings set org.gnome.settings-daemon.plugins.media-keys.custom-keybinding:/org/gnome/settings-daemon/plugins/media-keys/custom-keybindings/custom0/ \
  name 'Spotlight AI'
gsettings set org.gnome.settings-daemon.plugins.media-keys.custom-keybinding:/org/gnome/settings-daemon/plugins/media-keys/custom-keybindings/custom0/ \
  command "$PYTHON_PATH $SCRIPT_PATH"
gsettings set org.gnome.settings-daemon.plugins.media-keys.custom-keybinding:/org/gnome/settings-daemon/plugins/media-keys/custom-keybindings/custom0/ \
  binding '<Control>space'
```

### 4. Press `Ctrl+Space`

---

## How it works

```
Ctrl+Space
    └─▶ app.py launches PyQt5 window
            └─▶ on Enter: opencode run --format json -m <model> "<prompt>"
                    └─▶ streams JSON events → extracts text → displays in UI
```

Slash commands are parsed before sending to OpenCode. Model state persists in `~/.spotlight/config.json`.

---

## Files

```
app.py        entry point
ui.py         PyQt5 window — search bar + result area + animations
opencode.py   subprocess wrapper around opencode CLI
slash.py      slash command parser — dynamic model list, persistent config
```

---

## Requirements

- Linux with GNOME (or any WM — hotkey setup differs)
- Python 3.10+
- PyQt5
- [OpenCode CLI](https://opencode.ai)

---

## Why not just use the terminal?

Because `Ctrl+Space → type → read` is 5x faster than switching to a terminal, typing a long command, and scrolling through output. This stays on top, answers inline, and disappears with `Esc`.

---

Built with OpenCode + PyQt5. Inspired by macOS Spotlight and [Raycast](https://raycast.com).
