"""CLI entry point for terminal-activator."""

import os
import sys
import signal

from terminal_activator.daemon import run, PID_FILE

USAGE = """\
Usage: terminal-activator <command>

Commands:
  start    Start the activator daemon (foreground)
  stop     Stop the running daemon
  status   Show daemon status
"""


def _read_pid() -> int | None:
    try:
        with open(PID_FILE) as f:
            return int(f.read().strip())
    except (FileNotFoundError, ValueError):
        return None


def _is_running(pid: int) -> bool:
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False


def cmd_start():
    pid = _read_pid()
    if pid and _is_running(pid):
        print(f"Already running (PID: {pid}). Use 'terminal-activator stop' first.")
        sys.exit(1)
    run()


def cmd_stop():
    pid = _read_pid()
    if not pid or not _is_running(pid):
        print("Not running.")
        return
    os.kill(pid, signal.SIGTERM)
    print(f"Stopped (PID: {pid}).")


def cmd_status():
    pid = _read_pid()
    if pid and _is_running(pid):
        print(f"Running (PID: {pid})")
    else:
        print("Not running.")


def main():
    if len(sys.argv) < 2:
        print(USAGE)
        sys.exit(1)

    command = sys.argv[1]
    commands = {
        "start": cmd_start,
        "stop": cmd_stop,
        "status": cmd_status,
    }

    if command in commands:
        commands[command]()
    else:
        print(f"Unknown command: {command}")
        print(USAGE)
        sys.exit(1)
