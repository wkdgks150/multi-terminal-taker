"""Detect whether a terminal is waiting for user input."""

import os
import time

from terminal_activator.monitor import TerminalTab

SHELL_NAMES = {
    "zsh", "-zsh",
    "bash", "-bash",
    "fish", "-fish",
    "sh", "-sh",
}

# If TTY has no output for this many seconds, consider it idle
TTY_IDLE_THRESHOLD = 10.0


def get_tty_idle_seconds(tty: str) -> float:
    """Get seconds since last output on a TTY device."""
    try:
        return time.time() - os.stat(tty).st_mtime
    except OSError:
        return 0.0


def is_waiting_for_input(tab: TerminalTab) -> bool:
    """Detect if terminal is waiting for user input.

    Signal 1: Shell (zsh/bash) in foreground → definitely waiting.
    Signal 2: Non-shell process in foreground + TTY idle → likely waiting.
    """
    process = tab.fg_process.strip()
    if not process:
        return False

    basename = process.rsplit("/", 1)[-1] if "/" in process else process

    # Signal 1: shell in foreground = prompt waiting
    if basename in SHELL_NAMES:
        return True

    # Signal 2: TTY idle (no output for N seconds) = process waiting for input
    if tab.tty_idle_seconds >= TTY_IDLE_THRESHOLD:
        return True

    return False
