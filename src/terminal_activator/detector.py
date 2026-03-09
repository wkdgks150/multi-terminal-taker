"""Detect whether a terminal is waiting for user input.

Detection strategy (in priority order):
1. Hook marker: /tmp/terminal-activator/{tty}.idle exists → idle.
   Created by Claude Code Stop hook, removed by UserPromptSubmit hook.
2. Shell foreground (zsh/bash/fish) → always waiting for input.
3. Content stasis: foreground is an interactive app (claude, node, etc.)
   and terminal content hasn't changed for STASIS_SECONDS → idle.
   Catches mid-turn waiting states like AskUserQuestion.
"""

import os

from terminal_activator.monitor import TerminalTab

SHELL_NAMES = {
    "zsh", "-zsh",
    "bash", "-bash",
    "fish", "-fish",
    "sh", "-sh",
}

INTERACTIVE_APPS = {
    "claude", "node",
}

MARKER_DIR = "/tmp/terminal-activator"
STASIS_POLLS = 8  # consecutive unchanged polls → idle (8s at 1s interval)


def is_shell_foreground(tab: TerminalTab) -> bool:
    """Check if a shell is the foreground process."""
    process = tab.fg_process.strip()
    if not process:
        return False
    basename = process.rsplit("/", 1)[-1] if "/" in process else process
    return basename in SHELL_NAMES


def is_interactive_app(tab: TerminalTab) -> bool:
    """Check if an interactive app is the foreground process."""
    process = tab.fg_process.strip()
    if not process:
        return False
    basename = process.rsplit("/", 1)[-1] if "/" in process else process
    return basename in INTERACTIVE_APPS


def has_idle_marker(tty: str) -> bool:
    """Check if the Claude Code idle marker file exists for this TTY."""
    tty_name = os.path.basename(tty)
    return os.path.exists(os.path.join(MARKER_DIR, f"{tty_name}.idle"))


class ContentStasisTracker:
    """Track terminal content stability per TTY.

    If content_len hasn't changed for STASIS_POLLS consecutive polls,
    the terminal is considered stale (waiting for input).
    """

    def __init__(self):
        self._state: dict[str, tuple[int, int]] = {}  # tty → (content_len, unchanged_count)

    def update(self, tty: str, content_len: int) -> bool:
        """Update content tracking. Returns True if content is stale."""
        prev_len, count = self._state.get(tty, (None, 0))
        if content_len == prev_len:
            count += 1
        else:
            count = 0
        self._state[tty] = (content_len, count)
        return count >= STASIS_POLLS

    def remove(self, tty: str) -> None:
        """Stop tracking a TTY."""
        self._state.pop(tty, None)
