# Spotlight AI

[![PyPI version](https://img.shields.io/pypi/v/spotlight-ai?style=flat-square&color=blue)](https://pypi.org/project/spotlight-ai/)
[![GitHub stars](https://img.shields.io/github/stars/santhoshkammari/spotlight-ai?style=flat-square&color=yellow)](https://github.com/santhoshkammari/spotlight-ai/stargazers)
[![GitHub forks](https://img.shields.io/github/forks/santhoshkammari/spotlight-ai?style=flat-square&color=green)](https://github.com/santhoshkammari/spotlight-ai/network)
[![PyPI downloads](https://img.shields.io/pypi/dm/spotlight-ai?style=flat-square&color=orange)](https://pypi.org/project/spotlight-ai/)
[![License: MIT](https://img.shields.io/badge/License-MIT-lightgrey?style=flat-square)](LICENSE)

> ⭐ **If this saves you time, drop a star — it helps others find it!**

A macOS Spotlight-style AI bar for Linux. Press a hotkey, ask anything, get answers inline — without leaving your workflow.

Powered by [OpenCode](https://opencode.ai) with **200+ free and paid models** (DeepSeek, Gemini, Claude, Qwen, Kimi, GLM and more) — plus a radio-button switch for a local vLLM server or Claude Code directly.

---

## Screenshots

**Type your question:**

![search](assets/1-search.png)

**Thinking...**

![thinking](assets/2-thinking.png)

**Answer inline:**

![result](assets/3-result.png)

---

## Install

```bash
pip install spotlight-ai
spotlight-setup
```

That's it. `spotlight-setup` will:
- Install [OpenCode CLI](https://opencode.ai) automatically
- Install PyQt5 if missing
- Register your hotkey (default `Ctrl+Space`, or pick your own)

---

## Usage

| Command | What it does |
|---|---|
| `spotlight` | Launch the bar |
| `spotlight --help` | Show help |
| `spotlight-setup` | First-time setup (install deps + hotkey) |
| `spotlight-keybind` | Register `Ctrl+Space` hotkey |
| `spotlight-keybind "<Super>space"` | Register a custom hotkey |
| `spotlight-help` | Show all commands |

### Custom hotkeys

```bash
spotlight-keybind                        # Ctrl+Space  (default)
spotlight-keybind "<Super>space"         # Win+Space
spotlight-keybind "<Alt>space"           # Alt+Space
spotlight-keybind "<Control><Shift>s"    # Ctrl+Shift+S
```

---

## Slash commands (inside the bar)

| Command | What it does |
|---|---|
| `/help` | Show slash command menu |
| `/model` | Show current active model |
| `/models` | List all available models (fetched live) |
| `/<alias>` | Switch model — e.g. `/gemini-2.5-flash` |
| `/<alias> <prompt>` | Switch + ask in one shot |

Model aliases are auto-derived from model IDs (last segment, lowercase). No hardcoded list — when OpenCode adds new models, they appear automatically.

**Examples:**
```
/deepseek-v4-flash-free
/gemini-2.5-flash what is a monad?
/claude-sonnet-4.6 write a regex for email
/kimi-k2-instruct explain async/await in 3 lines
```

Active model persists in `~/.spotlight/config.json`.

---

## Backend selector

Three radio buttons above the result area (not a dropdown — one click to switch):

| Backend | What it hits |
|---|---|
| **OpenCode** (default) | persistent `opencode serve` + SSE, 200+ models |
| **Local** | your own vLLM server (`SPOTLIGHT_LOCAL_URL`, default `http://192.168.170.49:8000`) |
| **Claude** | `claude -p --dangerously-skip-permissions --output-format stream-json` |

Selection persists in `~/.spotlight/config.json` under `backend`.

---

## How it works

```
hotkey pressed
  └─▶ PyQt5 frameless dark overlay appears (center of screen)
        └─▶ you type, press Enter
              └─▶ active backend streams tokens as they're generated
                    (opencode serve SSE / vLLM SSE / claude stream-json)
                          └─▶ answer appears in the bar, token by token
                                └─▶ press Esc to close
```

Slash commands are parsed before sending to OpenCode. Model switches are instant and persistent.

---

## Requirements

- Linux (GNOME for hotkey auto-registration; other DEs work manually)
- Python 3.10+
- [OpenCode CLI](https://opencode.ai) — installed automatically by `spotlight-setup`
- PyQt5 — installed automatically by `spotlight-setup`

---

## Files

```
spotlight_ai/
  cli.py        entry points: spotlight, spotlight-setup, spotlight-keybind, spotlight-help
  ui.py         PyQt5 frameless window — search bar + backend radios + result area + animations
  opencode.py   persistent `opencode serve` + SSE streaming backend
  backends.py   local vLLM + Claude Code streaming backends
  slash.py      slash command parser — live model list, persistent config (model + backend)
```

---

## Why not just use the terminal?

`hotkey → type → read` beats switching windows, typing a long command, and scrolling output. Spotlight stays on top, answers inline, and disappears with `Esc`. Works from anywhere — full-screen apps, browsers, anything.

---

Built with [OpenCode](https://opencode.ai) + PyQt5. Inspired by macOS Spotlight.

**PyPI:** [spotlight-ai](https://pypi.org/project/spotlight-ai/) · **GitHub:** [santhoshkammari/spotlight-ai](https://github.com/santhoshkammari/spotlight-ai)
