"""Popup queue — pop up waiting terminals in FIFO order."""

from mtt.monitor import TerminalTab
from mtt import window_controller


class PopupQueue:
    """Maintains an ordered list of waiting terminals and pops up the next one.

    Core rule: NEVER interrupt the terminal the user is currently looking at.
    Only switch when the frontmost terminal transitions from IDLE to BUSY
    (user submitted a prompt, Claude started processing).
    """

    def __init__(self, own_tty: str):
        self.own_tty = own_tty
        self.queue: list[str] = []  # idle TTYs, FIFO order
        self.serving: str | None = None
        self.serving_reason: str = ""  # "marker" or "stasis"

    def update(self, tabs: list[TerminalTab], frontmost_tty: str) -> None:
        tabs = [t for t in tabs if t.tty != self.own_tty]
        # Only queue terminals with Claude-related idle signals (marker/stasis).
        # Plain shell prompts ("shell") are excluded — they're regular terminals
        # that shouldn't trigger popup behaviour.
        waiting_ttys = {t.tty for t in tabs if t.waiting_for_input and t.idle_reason != "shell"}
        reason_map = {t.tty: t.idle_reason for t in tabs if t.tty in waiting_ttys}

        # Update queue: remove non-waiting, add new waiting (FIFO)
        self.queue = [tty for tty in self.queue if tty in waiting_ttys]
        known = set(self.queue)
        for t in tabs:
            if t.tty in waiting_ttys and t.tty not in known:
                self.queue.append(t.tty)
                known.add(t.tty)

        need_popup = False

        # Sync serving with frontmost: if user is looking at an idle terminal,
        # that's the one being served (regardless of queue order).
        if frontmost_tty and frontmost_tty in waiting_ttys:
            self.serving = frontmost_tty
            self.serving_reason = reason_map.get(frontmost_tty, "")

        # Keep serving_reason up to date while serving terminal stays idle.
        if self.serving and self.serving in waiting_ttys:
            self.serving_reason = reason_map.get(self.serving, self.serving_reason)

        if self.serving and self.serving not in waiting_ttys:
            if self.serving_reason == "stasis" and frontmost_tty == self.serving:
                # Stasis-based idle + user is looking at it → content change
                # is likely from user typing, not submission. Hold off until
                # user looks away or terminal becomes idle again.
                pass
            else:
                # Marker-based (definitive submit signal) or user isn't
                # looking → safe to switch.
                self.serving = None
                self.serving_reason = ""
                need_popup = True

        if not self.serving and self.queue:
            self.serving = self.queue[0]
            self.serving_reason = reason_map.get(self.serving, "")
            need_popup = True

        if need_popup and self.serving:
            window_controller.popup(self.serving)

    @property
    def status_line(self) -> str:
        if self.serving:
            return f"QUEUE: {len(self.queue)} | SERVING: {self.serving}"
        return "IDLE"
