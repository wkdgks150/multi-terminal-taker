"""Detect whether a terminal is waiting for user input.

Detection strategy:
- Shell foreground (zsh/bash/fish) → always waiting for input.
- Claude Code → hook-based: checks /tmp/terminal-activator/{tty}.idle marker file.
  Marker is created by Claude Code's Stop hook (idle) and removed by
  UserPromptSubmit hook (busy).
"""

import os

from terminal_activator.monitor import TerminalTab

SHELL_NAMES = {
    "zsh", "-zsh",
    "bash", "-bash",
    "fish", "-fish",
    "sh", "-sh",
}

MARKER_DIR = "/tmp/terminal-activator"


def is_shell_foreground(tab: TerminalTab) -> bool:
    """Check if a shell is the foreground process."""
    process = tab.fg_process.strip()
    if not process:
        return False
    basename = process.rsplit("/", 1)[-1] if "/" in process else process
    return basename in SHELL_NAMES


def has_idle_marker(tty: str) -> bool:
    """Check if the Claude Code idle marker file exists for this TTY."""
    tty_name = os.path.basename(tty)  # /dev/ttys001 → ttys001
    return os.path.exists(os.path.join(MARKER_DIR, f"{tty_name}.idle"))
