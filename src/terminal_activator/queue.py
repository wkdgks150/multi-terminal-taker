"""Window ordering queue — arrange waiting terminals by FIFO order."""

from terminal_activator.monitor import TerminalTab
from terminal_activator import window_controller


class PopupQueue:
    """Maintains an ordered list of waiting terminals and arranges windows.

    - Waiting terminals are ordered FIFO (first to start waiting = front).
    - Window z-order is updated only when the queue changes.
    - Does NOT activate Terminal.app — just reorders windows.
    """

    def __init__(self, own_tty: str):
        self.own_tty = own_tty
        self.queue: list[str] = []  # ordered TTYs, FIFO

    def update(self, tabs: list[TerminalTab]) -> None:
        tabs = [t for t in tabs if t.tty != self.own_tty]
        waiting_ttys = {t.tty for t in tabs if t.waiting_for_input}

        prev_queue = list(self.queue)

        # Remove TTYs no longer waiting
        self.queue = [tty for tty in self.queue if tty in waiting_ttys]

        # Add new waiting TTYs to end (FIFO)
        known = set(self.queue)
        for t in tabs:
            if t.waiting_for_input and t.tty not in known:
                self.queue.append(t.tty)
                known.add(t.tty)

        # Reorder windows only when queue changes
        if self.queue != prev_queue and self.queue:
            window_controller.arrange(self.queue)

    @property
    def status_line(self) -> str:
        if self.queue:
            return f"QUEUE: {len(self.queue)} | FRONT: {self.queue[0]}"
        return "IDLE"
