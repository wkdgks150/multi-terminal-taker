# MTT (Multi-Terminal Taker)

[![Tests](https://github.com/wkdgks150/multi-terminal-taker/actions/workflows/test.yml/badge.svg)](https://github.com/wkdgks150/multi-terminal-taker/actions/workflows/test.yml)

**Auto-popup terminals waiting for your input — like a poker MTT client, but for your terminal.**

<!-- Record a 15-second demo: 3+ terminals with Claude Code, one goes idle, window pops up automatically -->
<!-- ![Demo](docs/assets/demo.gif) -->

> Running 5 Claude Code sessions at once? MTT watches all of them and
> automatically brings each terminal to the front the moment it needs your input.
> When you respond, the next waiting terminal pops up. Zero dependencies. Pure Python.

## The Problem

You have multiple terminals open — builds, tests, AI agents, servers. Most run on their own,
but occasionally one needs your input. You waste time hunting through windows to find which one.

## The Solution

MTT monitors all your terminal windows. When one starts waiting for input,
it pops up automatically. You deal with it, and the next one pops up — like a poker
multi-table tournament client that shows you whichever table needs your action.

## How It Works

```
Terminal.app / iTerm2           MTT
┌──────────────┐
│ Tab 1: build │ ──running──┐
│ Tab 2: test  │ ──running──┤
│ Tab 3: claude│ ──idle────┐│   ┌─────────┐   ┌────────┐
│ Tab 4: claude│ ──busy────┤├──▶│  Queue   │──▶│ Pop up │
│ Tab 5: zsh   │ ──idle────┘│   │ (FIFO)  │   │ window │
│ Tab 6: server│ ──running──┘   └─────────┘   └────────┘
└──────────────┘
```

1. **Scan** — AppleScript reads all terminal windows/tabs every second
2. **Detect** — Checks if each terminal is waiting for input (3 methods)
3. **Queue** — Waiting terminals enter a FIFO queue
4. **Pop up** — The next terminal gets its window raised; when you respond, the next one pops up

### Detection Methods

| Method | Trigger | Speed |
|--------|---------|-------|
| **Hook marker** | Claude Code idle/busy hooks create/remove marker files | Instant |
| **Shell prompt** | Foreground process is zsh/bash/fish | Instant |
| **Content stasis** | Interactive app (claude, node) + content unchanged for 8s + no new child processes | 8s delay |

Content stasis catches mid-turn waiting states like Claude Code's `AskUserQuestion` prompts,
where the Stop hook hasn't fired yet. Child process tracking prevents false positives during
long tool calls.

## Supported Terminals

- **Terminal.app** — Full support
- **iTerm2** — Full support
- Auto-detects which apps are running; works with both simultaneously

## Claude Code Integration

MTT integrates with [Claude Code](https://docs.anthropic.com/en/docs/claude-code) hooks
for instant idle/busy detection:

Add to `~/.claude/settings.json`:
```json
{
  "hooks": {
    "Stop": [
      {
        "matcher": "",
        "hooks": [
          {
            "type": "command",
            "command": "/path/to/mtt/scripts/hook-idle.sh"
          }
        ]
      }
    ],
    "UserPromptSubmit": [
      {
        "matcher": "",
        "hooks": [
          {
            "type": "command",
            "command": "/path/to/mtt/scripts/hook-busy.sh"
          }
        ]
      }
    ]
  }
}
```

Without hooks, MTT still works via shell prompt detection and content stasis — hooks just make it faster.

## Requirements

- macOS (uses AppleScript)
- Python 3.12+
- Accessibility permission (System Settings → Privacy & Security → Accessibility)

## Install

```bash
pip install multi-terminal-taker
```

Or from source:
```bash
git clone https://github.com/wkdgks150/multi-terminal-taker.git
cd multi-terminal-taker
pip install -e .
```

Zero external dependencies — Python standard library only.

## Usage

```bash
mtt start    # Start daemon (foreground)
mtt status   # Check if running
mtt stop     # Stop daemon
```

Output while running:
```
[12:34:56] IDLE
[12:34:57] QUEUE: 2 | SERVING: /dev/ttys003
[12:34:58] QUEUE: 1 | SERVING: /dev/ttys007
[12:34:59] IDLE
```

## Project Structure

```
src/mtt/
├── cli.py                # CLI (start/stop/status)
├── daemon.py             # Main polling loop (1s interval)
├── monitor.py            # Terminal scanner (Terminal.app + iTerm2)
├── detector.py           # Idle detection (hooks + shell + content stasis)
├── queue.py              # FIFO popup queue
└── window_controller.py  # Window popup (Terminal.app + iTerm2)
scripts/
├── hook-idle.sh          # Claude Code Stop hook
└── hook-busy.sh          # Claude Code UserPromptSubmit hook
```

## Tests

```bash
pip install pytest
pytest
```

## Roadmap

- [x] Terminal scan + auto-popup + FIFO queue
- [x] Claude Code hook integration
- [x] Content stasis detection (AskUserQuestion, etc.)
- [x] iTerm2 support
- [ ] Menu bar status indicator
- [ ] Priority rules (pin important terminals)
- [ ] Configurable polling interval and stasis threshold

## License

[MIT](LICENSE)

---

[한국어](README.ko.md)
