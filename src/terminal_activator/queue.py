"""Popup queue management — serve one terminal at a time."""

from terminal_activator.monitor import TerminalTab, get_content_hash
from terminal_activator import window_controller

# After content changed at least once, this many consecutive static polls = done.
STATIC_POLLS_TO_CLEAR = 3  # 3 × 2s = 6 seconds of no content change


class PopupQueue:
    """Manages the popup queue.

    Clearing logic for interactive programs (fg unchanged):
      1. Content changes at any point → user interacted or program responded
      2. Content stops changing for 6s → interaction cycle done → clear → pop next

    Also clears instantly on fg_process change (shell ran a command).
    Terminal.app must be frontmost to popup.
    """

    def __init__(self, own_tty: str):
        self.own_tty = own_tty
        self.serving: TerminalTab | None = None
        self.waiting: list[TerminalTab] = []
        self._serving_fg: str = ""
        self._last_hash: str = ""
        self._ever_changed: bool = False
        self._static_count: int = 0

    def _clear_serving(self) -> None:
        self.serving = None
        self._serving_fg = ""
        self._last_hash = ""
        self._ever_changed = False
        self._static_count = 0

    def update(self, tabs: list[TerminalTab], terminal_is_frontmost: bool = True) -> None:
        tabs = [t for t in tabs if t.tty != self.own_tty]
        waiting_ttys = {t.tty for t in tabs if t.waiting_for_input}

        # --- Handle serving terminal ---
        if self.serving:
            current_fg = None
            for tab in tabs:
                if tab.tty == self.serving.tty:
                    current_fg = tab.fg_process
                    break

            if current_fg is None:
                self._clear_serving()
            elif current_fg != self._serving_fg:
                self._clear_serving()
            else:
                current_hash = get_content_hash(self.serving.tty)
                content_changed = current_hash != self._last_hash and self._last_hash != ""

                if content_changed:
                    self._ever_changed = True
                    self._static_count = 0
                else:
                    if self._ever_changed:
                        self._static_count += 1
                        if self._static_count >= STATIC_POLLS_TO_CLEAR:
                            self._clear_serving()

                if self.serving:
                    self._last_hash = current_hash

        # --- Maintain queue ---
        self.waiting = [t for t in self.waiting if t.tty in waiting_ttys]

        known_ttys: set[str] = set()
        if self.serving:
            known_ttys.add(self.serving.tty)
        known_ttys.update(t.tty for t in self.waiting)

        for tab in tabs:
            if tab.waiting_for_input and tab.tty not in known_ttys:
                self.waiting.append(tab)

        # --- Pop next only when nothing serving AND Terminal.app is frontmost ---
        if not self.serving and self.waiting and terminal_is_frontmost:
            next_tab = self.waiting.pop(0)
            success = window_controller.popup(next_tab.tty)
            if success:
                self.serving = next_tab
                self._serving_fg = next_tab.fg_process
                self._last_hash = get_content_hash(next_tab.tty)
                self._ever_changed = False
                self._static_count = 0

    @property
    def status_line(self) -> str:
        if self.serving:
            queued = len(self.waiting)
            phase = "INTERACTED" if self._ever_changed else "AWAITING"
            msg = f"SERVING: {self.serving.tty} [{phase}]"
            if queued > 0:
                msg += f" | QUEUED: {queued}"
            return msg
        if self.waiting:
            return f"IDLE | QUEUED: {len(self.waiting)}"
        return "IDLE"
