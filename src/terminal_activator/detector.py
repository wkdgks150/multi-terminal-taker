"""Detect whether a terminal is waiting for user input."""

from terminal_activator.monitor import TerminalTab

SHELL_NAMES = {
    "zsh", "-zsh",
    "bash", "-bash",
    "fish", "-fish",
    "sh", "-sh",
}


def is_shell_foreground(tab: TerminalTab) -> bool:
    """Check if a shell is the foreground process."""
    process = tab.fg_process.strip()
    if not process:
        return False
    basename = process.rsplit("/", 1)[-1] if "/" in process else process
    return basename in SHELL_NAMES


class ContentTracker:
    """Track terminal content changes to detect idle state.

    TUI apps (claude, vim, etc.) constantly update TTY mtime even when idle.
    But their visible text content stays the same when waiting for input.

    Logic: if content hash hasn't changed for N consecutive polls → idle.
    """

    # Consecutive polls with same content = idle (waiting for input)
    STATIC_POLLS_THRESHOLD = 5  # 5 × 2s = 10 seconds of no content change

    def __init__(self):
        self._hashes: dict[str, str] = {}       # tty → last content hash
        self._static_counts: dict[str, int] = {} # tty → consecutive static polls

    def update(self, tty: str, content_hash: str) -> bool:
        """Update tracker and return True if terminal is idle (content static)."""
        last_hash = self._hashes.get(tty, "")

        if content_hash and last_hash and content_hash == last_hash:
            self._static_counts[tty] = self._static_counts.get(tty, 0) + 1
        else:
            self._static_counts[tty] = 0

        self._hashes[tty] = content_hash
        return self._static_counts.get(tty, 0) >= self.STATIC_POLLS_THRESHOLD

    def is_content_idle(self, tty: str) -> bool:
        return self._static_counts.get(tty, 0) >= self.STATIC_POLLS_THRESHOLD
