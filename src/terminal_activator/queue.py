"""Popup queue management — serve one terminal at a time."""

from datetime import datetime
from terminal_activator.monitor import TerminalTab
from terminal_activator import window_controller


class PopupQueue:
    def __init__(self, own_tty: str):
        self.own_tty = own_tty
        self.serving: TerminalTab | None = None
        self.waiting: list[TerminalTab] = []

    def update(self, tabs: list[TerminalTab]) -> None:
        """Process scan results and manage the queue."""
        # Filter out own terminal
        tabs = [t for t in tabs if t.tty != self.own_tty]

        waiting_ttys = {t.tty for t in tabs if t.waiting_for_input}

        # 1. If serving terminal is no longer waiting → input completed
        if self.serving and self.serving.tty not in waiting_ttys:
            self.serving = None

        # 2. Remove from queue if no longer waiting
        self.waiting = [t for t in self.waiting if t.tty in waiting_ttys]

        # 3. Add newly waiting terminals to queue
        known_ttys: set[str] = set()
        if self.serving:
            known_ttys.add(self.serving.tty)
        known_ttys.update(t.tty for t in self.waiting)

        for tab in tabs:
            if tab.waiting_for_input and tab.tty not in known_ttys:
                self.waiting.append(tab)

        # 4. If nothing is serving and queue has items → popup next
        if not self.serving and self.waiting:
            next_tab = self.waiting.pop(0)
            success = window_controller.popup(next_tab.tty)
            if success:
                self.serving = next_tab
            # If popup failed, it's dropped; next cycle will re-detect if still waiting

    @property
    def status_line(self) -> str:
        if self.serving:
            queued = len(self.waiting)
            msg = f"SERVING: {self.serving.tty} (fg: {self.serving.fg_process})"
            if queued > 0:
                msg += f" | QUEUED: {queued}"
            return msg
        return "IDLE"
