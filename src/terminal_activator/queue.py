"""Popup queue management — serve one terminal at a time."""

from terminal_activator.monitor import TerminalTab
from terminal_activator import window_controller


class PopupQueue:
    """Manages the popup queue.

    Rules:
    1. SERVING clears ONLY when fg_process changes (user ran command / exited app).
    2. While SERVING, new waiting terminals go to queue only — never popup.
    3. Wait indefinitely. No time-based heuristics.
    """

    def __init__(self, own_tty: str):
        self.own_tty = own_tty
        self.serving: TerminalTab | None = None
        self.waiting: list[TerminalTab] = []
        self._serving_fg: str = ""  # fg_process at time of popup

    def update(self, tabs: list[TerminalTab], terminal_is_frontmost: bool = True) -> None:
        """Process scan results and manage the queue."""
        tabs = [t for t in tabs if t.tty != self.own_tty]

        waiting_ttys = {t.tty for t in tabs if t.waiting_for_input}

        # --- Handle serving terminal ---
        if self.serving:
            # Find current fg_process of serving terminal
            current_fg = None
            for tab in tabs:
                if tab.tty == self.serving.tty:
                    current_fg = tab.fg_process
                    break

            if current_fg is None:
                # Terminal was closed
                self.serving = None
                self._serving_fg = ""
            elif current_fg != self._serving_fg:
                # Foreground process changed = user took action
                self.serving = None
                self._serving_fg = ""

        # --- Maintain queue ---
        self.waiting = [t for t in self.waiting if t.tty in waiting_ttys]

        known_ttys: set[str] = set()
        if self.serving:
            known_ttys.add(self.serving.tty)
        known_ttys.update(t.tty for t in self.waiting)

        for tab in tabs:
            if tab.waiting_for_input and tab.tty not in known_ttys:
                self.waiting.append(tab)

        # --- Pop next only when nothing is serving AND Terminal.app is frontmost ---
        if not self.serving and self.waiting and terminal_is_frontmost:
            next_tab = self.waiting.pop(0)
            success = window_controller.popup(next_tab.tty)
            if success:
                self.serving = next_tab
                self._serving_fg = next_tab.fg_process

    @property
    def status_line(self) -> str:
        if self.serving:
            queued = len(self.waiting)
            msg = f"SERVING: {self.serving.tty} (fg: {self._serving_fg})"
            if queued > 0:
                msg += f" | QUEUED: {queued}"
            return msg
        if self.waiting:
            return f"IDLE | QUEUED: {len(self.waiting)}"
        return "IDLE"
