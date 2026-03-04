"""Main daemon loop."""

import os
import time
import signal

from terminal_activator.monitor import scan_terminals
from terminal_activator.detector import has_idle_marker
from terminal_activator.queue import PopupQueue

POLL_INTERVAL = 1.0  # seconds
PID_FILE = "/tmp/terminal-activator.pid"


def get_own_tty() -> str:
    try:
        return os.ttyname(0)
    except OSError:
        return ""


def run():
    own_tty = get_own_tty()
    queue = PopupQueue(own_tty)
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
            tabs, frontmost_tty = scan_terminals()
            if not tabs:
                time.sleep(POLL_INTERVAL)
                continue

            for tab in tabs:
                tab.waiting_for_input = has_idle_marker(tab.tty)

            queue.update(tabs, frontmost_tty)

            print(f"\r[{time.strftime('%H:%M:%S')}] {queue.status_line}  ", end="", flush=True)

            time.sleep(POLL_INTERVAL)
    finally:
        try:
            os.remove(PID_FILE)
        except OSError:
            pass
        print("\nTerminal Activator stopped.")
