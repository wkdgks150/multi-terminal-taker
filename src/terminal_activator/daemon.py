"""Main daemon loop."""

import os
import sys
import time
import signal

from terminal_activator.monitor import scan_terminals, scan_foreground_processes
from terminal_activator.detector import is_waiting_for_input
from terminal_activator.queue import PopupQueue

POLL_INTERVAL = 2.0  # seconds
PID_FILE = "/tmp/terminal-activator.pid"


def get_own_tty() -> str:
    """Get the TTY of the terminal running this daemon."""
    try:
        return os.ttyname(0)
    except OSError:
        return ""


def run():
    """Main daemon loop."""
    own_tty = get_own_tty()
    queue = PopupQueue(own_tty)
    running = True

    def handle_signal(signum, frame):
        nonlocal running
        running = False

    signal.signal(signal.SIGTERM, handle_signal)
    signal.signal(signal.SIGINT, handle_signal)

    # Write PID file
    with open(PID_FILE, "w") as f:
        f.write(str(os.getpid()))

    if own_tty:
        print(f"Terminal Activator started (PID: {os.getpid()}, own TTY: {own_tty})")
    else:
        print(f"Terminal Activator started (PID: {os.getpid()}, no TTY detected)")
    print(f"Polling every {POLL_INTERVAL}s. Press Ctrl+C to stop.")

    try:
        while running:
            # 1. Scan terminals
            tabs = scan_terminals()
            if not tabs:
                time.sleep(POLL_INTERVAL)
                continue

            # 2. Get foreground processes
            fg_map = scan_foreground_processes()

            # 3. Enrich tabs with fg process and detect waiting
            for tab in tabs:
                tab.fg_process = fg_map.get(tab.tty, "")
                tab.waiting_for_input = is_waiting_for_input(tab)

            # 4. Update queue
            queue.update(tabs)

            # 5. Print status
            print(f"\r[{time.strftime('%H:%M:%S')}] {queue.status_line}  ", end="", flush=True)

            time.sleep(POLL_INTERVAL)
    finally:
        # Cleanup PID file
        try:
            os.remove(PID_FILE)
        except OSError:
            pass
        print("\nTerminal Activator stopped.")
