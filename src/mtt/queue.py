"""Popup queue — pop up waiting terminals in FIFO order."""

from mtt.monitor import TerminalTab
from mtt import window_controller


class PopupQueue:
    """Maintains an ordered list of waiting terminals and pops up the next one.

    Core rules:
    - NEVER interrupt the terminal the user is currently looking at.
    - Marker-based idle → auto-switch on submission (definitive signal).
    - Stasis-based idle → NEVER auto-switch (can't distinguish typing
      from submission).  Switch only via frontmost sync or terminal
      re-entering idle.
    """

    def __init__(self, own_tty: str):
        self.own_tty = own_tty
        self.queue: list[str] = []  # idle TTYs, FIFO order
        self.serving: str | None = None
        self.serving_reason: str = ""  # "marker" or "stasis"

    def update(self, tabs: list[TerminalTab], frontmost_tty: str) -> None:
        tabs = [t for t in tabs if t.tty != self.own_tty]
        waiting = {
            t.tty: t.idle_reason
            for t in tabs
            if t.waiting_for_input and t.idle_reason != "shell"
        }
        visible = {t.tty for t in tabs}

        self._maintain_queue(tabs, waiting)
        self._resolve_serving(waiting, visible, frontmost_tty)

    # -- internals --------------------------------------------------

    def _maintain_queue(self, tabs: list[TerminalTab],
                        waiting: dict[str, str]) -> None:
        """Update FIFO queue: drop non-waiting, append new arrivals."""
        self.queue = [tty for tty in self.queue if tty in waiting]
        known = set(self.queue)
        for t in tabs:
            if t.tty in waiting and t.tty not in known:
                self.queue.append(t.tty)
                known.add(t.tty)

    def _resolve_serving(self, waiting: dict[str, str],
                         visible: set[str], frontmost_tty: str) -> None:
        """Decide which terminal to serve and whether to trigger a popup."""
        need_popup = False

        # Terminal closed/disappeared → clear immediately.
        if self.serving and self.serving not in visible:
            self.serving = None
            self.serving_reason = ""

        # Frontmost sync: if user is looking at an idle terminal,
        # that's the one being served (regardless of queue order).
        if frontmost_tty and frontmost_tty in waiting:
            self.serving = frontmost_tty
            self.serving_reason = waiting[frontmost_tty]

        # Keep serving_reason up to date while terminal stays idle.
        if self.serving and self.serving in waiting:
            self.serving_reason = waiting[self.serving]

        # Serving terminal left idle state → decide whether to switch.
        if self.serving and self.serving not in waiting:
            if self.serving_reason == "marker":
                # Marker removal = user submitted prompt → safe to switch.
                self.serving = None
                self.serving_reason = ""
                need_popup = True
            # else (stasis): content change could be typing OR submission.
            # Cannot distinguish → do NOT auto-switch.  Serving stays
            # until frontmost sync re-assigns or terminal re-enters idle.

        # No serving terminal → pop next from queue.
        if not self.serving and self.queue:
            self.serving = self.queue[0]
            self.serving_reason = waiting.get(self.serving, "")
            need_popup = True

        if need_popup and self.serving:
            window_controller.popup(self.serving)

    @property
    def status_line(self) -> str:
        if self.serving:
            return f"QUEUE: {len(self.queue)} | SERVING: {self.serving}"
        return "IDLE"
