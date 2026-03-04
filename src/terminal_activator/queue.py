"""Window ordering queue — arrange waiting terminals by FIFO order."""

from terminal_activator.monitor import TerminalTab
from terminal_activator import window_controller


class PopupQueue:
    """Maintains an ordered list of waiting terminals and arranges windows.

    Core rule: NEVER interrupt the terminal the user is currently looking at.
    Only switch when the frontmost terminal transitions from IDLE to BUSY
    (user submitted a prompt, Claude started processing).
    """

    def __init__(self, own_tty: str):
        self.own_tty = own_tty
        self.queue: list[str] = []  # idle TTYs, FIFO order
        self.serving: str | None = None

    def update(self, tabs: list[TerminalTab], frontmost_tty: str) -> None:
        tabs = [t for t in tabs if t.tty != self.own_tty]
        waiting_ttys = {t.tty for t in tabs if t.waiting_for_input}

        # Update queue: remove non-waiting, add new waiting (FIFO)
        self.queue = [tty for tty in self.queue if tty in waiting_ttys]
        known = set(self.queue)
        for t in tabs:
            if t.waiting_for_input and t.tty not in known:
                self.queue.append(t.tty)
                known.add(t.tty)

        need_arrange = False

        # Sync serving with frontmost: if user is looking at an idle terminal,
        # that's the one being served (regardless of queue order).
        if frontmost_tty and frontmost_tty in waiting_ttys:
            self.serving = frontmost_tty

        if self.serving and self.serving not in waiting_ttys:
            # SERVING terminal became BUSY → user submitted prompt → switch
            self.serving = None
            need_arrange = True

        if not self.serving and self.queue:
            self.serving = self.queue[0]
            need_arrange = True

        if need_arrange and self.serving:
            window_controller.popup(self.serving)

    @property
    def status_line(self) -> str:
        if self.serving:
            return f"QUEUE: {len(self.queue)} | SERVING: {self.serving}"
        return "IDLE"
