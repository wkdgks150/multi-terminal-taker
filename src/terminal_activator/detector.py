"""Detect whether a terminal is waiting for user input."""

from terminal_activator.monitor import TerminalTab

SHELL_NAMES = {
    "zsh", "-zsh",
    "bash", "-bash",
    "fish", "-fish",
    "sh", "-sh",
}


def is_waiting_for_input(tab: TerminalTab) -> bool:
    """MVP: shell in foreground = waiting for input."""
    process = tab.fg_process.strip()
    # basename only (in case full path)
    basename = process.rsplit("/", 1)[-1] if "/" in process else process
    return basename in SHELL_NAMES
