"""Main daemon loop."""

import os
import time
import signal

from terminal_activator.monitor import (
    scan_terminals, scan_foreground_processes,
    get_content_hash,
)
from terminal_activator.detector import is_shell_foreground, ContentTracker
from terminal_activator.queue import PopupQueue

POLL_INTERVAL = 2.0  # seconds
PID_FILE = "/tmp/terminal-activator.pid"


def get_own_tty() -> str:
    try:
        return os.ttyname(0)
    except OSError:
        return ""


def run():
    own_tty = get_own_tty()
    queue = PopupQueue(own_tty)
    tracker = ContentTracker()
    running = True

    def handle_signal(signum, frame):
        nonlocal running
        running = False

    signal.signal(signal.SIGTERM, handle_signal)
    signal.signal(signal.SIGINT, handle_signal)

    with open(PID_FILE, "w") as f:
        f.write(str(os.getpid()))

    print(f"Terminal Activator started (PID: {os.getpid()})")
    print(f"Polling every {POLL_INTERVAL}s. Press Ctrl+C to stop.")

    try:
        while running:
            tabs = scan_terminals()
            if not tabs:
                time.sleep(POLL_INTERVAL)
                continue

            fg_map = scan_foreground_processes()

            # Enrich tabs and detect waiting state
            for tab in tabs:
                tab.fg_process = fg_map.get(tab.tty, "")

                if is_shell_foreground(tab):
                    # Shell in foreground = definitely waiting
                    tab.waiting_for_input = True
                else:
                    # Non-shell: use content hash to detect idle
                    content_hash = get_content_hash(tab.tty)
                    content_idle = tracker.update(tab.tty, content_hash)
                    tab.waiting_for_input = content_idle

            # Update queue and reorder windows
            queue.update(tabs)

            # Status
            print(f"\r[{time.strftime('%H:%M:%S')}] {queue.status_line}  ", end="", flush=True)

            time.sleep(POLL_INTERVAL)
    finally:
        try:
            os.remove(PID_FILE)
        except OSError:
            pass
        print("\nTerminal Activator stopped.")
