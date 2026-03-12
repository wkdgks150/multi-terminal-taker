"""Main daemon loop."""

import os
import time
import signal

from mtt.monitor import scan_terminals, scan_foreground_processes
from mtt.detector import (
    has_idle_marker, is_shell_foreground, is_interactive_app,
    ContentStasisTracker,
)
from mtt.queue import PopupQueue

POLL_INTERVAL = 1.0  # seconds
PID_FILE = "/tmp/mtt.pid"


def get_own_tty() -> str:
    try:
        return os.ttyname(0)
    except OSError:
        return ""


def run():
    own_tty = get_own_tty()
    queue = PopupQueue(own_tty)
    stasis = ContentStasisTracker()
    running = True

    def handle_signal(signum, frame):
        nonlocal running
        running = False

    signal.signal(signal.SIGTERM, handle_signal)
    signal.signal(signal.SIGINT, handle_signal)

    with open(PID_FILE, "w") as f:
        f.write(str(os.getpid()))

    print(f"MTT started (PID: {os.getpid()})")
    print(f"Polling every {POLL_INTERVAL}s. Press Ctrl+C to stop.")

    try:
        while running:
            tabs, frontmost_tty = scan_terminals()
            if not tabs:
                time.sleep(POLL_INTERVAL)
                continue

            fg_map = scan_foreground_processes()

            for tab in tabs:
                fg_info = fg_map.get(tab.tty)
                tab.fg_process = fg_info[0] if fg_info else ""
                child_pids = fg_info[1] if fg_info else frozenset()

                if has_idle_marker(tab.tty):
                    tab.waiting_for_input = True
                    tab.idle_reason = "marker"
                elif is_shell_foreground(tab):
                    tab.waiting_for_input = True
                    tab.idle_reason = "shell"
                elif is_interactive_app(tab):
                    if stasis.update(tab.tty, tab.content_len, child_pids):
                        tab.waiting_for_input = True
                        tab.idle_reason = "stasis"
                    else:
                        tab.waiting_for_input = False
                        tab.idle_reason = ""
                else:
                    stasis.update(tab.tty, tab.content_len, child_pids)
                    tab.waiting_for_input = False
                    tab.idle_reason = ""

            queue.update(tabs, frontmost_tty)

            print(f"\r[{time.strftime('%H:%M:%S')}] {queue.status_line}  ", end="", flush=True)

            time.sleep(POLL_INTERVAL)
    finally:
        try:
            os.remove(PID_FILE)
        except OSError:
            pass
        print("\nMTT stopped.")
