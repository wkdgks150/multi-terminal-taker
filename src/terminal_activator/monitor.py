"""Scan Terminal.app windows/tabs and process states."""

import subprocess
from dataclasses import dataclass


@dataclass
class TerminalTab:
    tty: str
    window_id: int
    tab_index: int
    fg_process: str = ""
    content_len: int = 0
    waiting_for_input: bool = False


APPLESCRIPT_SCAN = """\
set appName to ""
tell application "System Events"
    set appName to name of first application process whose frontmost is true
end tell
set frontTTY to ""
tell application "Terminal"
    set output to ""
    repeat with w in windows
        set wid to id of w
        set tabIdx to 0
        repeat with t in tabs of w
            set tabIdx to tabIdx + 1
            set ttyPath to tty of t
            set hLen to length of history of t
            set output to output & wid & "\\t" & tabIdx & "\\t" & ttyPath & "\\t" & hLen & linefeed
        end repeat
    end repeat
    if appName is "Terminal" and (count of windows) > 0 then
        set frontTTY to tty of selected tab of window 1
    end if
    return output & "FRONT\\t" & frontTTY
end tell
"""


def scan_terminals() -> tuple[list[TerminalTab], str]:
    """Scan all Terminal.app windows/tabs and frontmost TTY in one call.

    Returns (tabs, frontmost_tty). frontmost_tty is "" if Terminal.app
    is not the active app.
    """
    try:
        result = subprocess.run(
            ["osascript", "-e", APPLESCRIPT_SCAN],
            capture_output=True, text=True, timeout=5,
        )
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return [], ""

    if result.returncode != 0:
        return [], ""

    tabs = []
    frontmost_tty = ""
    for line in result.stdout.strip().split("\n"):
        if not line.strip():
            continue
        parts = line.split("\t")
        if len(parts) >= 2 and parts[0] == "FRONT":
            frontmost_tty = parts[1].strip()
            continue
        if len(parts) < 4:
            continue
        try:
            tabs.append(TerminalTab(
                window_id=int(parts[0]),
                tab_index=int(parts[1]),
                tty=parts[2].strip(),
                content_len=int(parts[3]),
            ))
        except (ValueError, IndexError):
            continue

    return tabs, frontmost_tty


def scan_foreground_processes() -> dict[str, str]:
    """Return {tty: fg_process_name} by parsing ps output."""
    try:
        result = subprocess.run(
            ["ps", "-e", "-o", "pid,pgid,tpgid,tty,comm"],
            capture_output=True, text=True, timeout=5,
        )
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return {}

    if result.returncode != 0:
        return {}

    tpgid_map: dict[str, int] = {}
    pgid_procs: dict[tuple[str, int], str] = {}

    for line in result.stdout.strip().split("\n")[1:]:
        parts = line.split()
        if len(parts) < 5:
            continue
        try:
            pid = int(parts[0])
            pgid = int(parts[1])
            tpgid = int(parts[2])
            tty = parts[3]
            comm = parts[4]
        except (ValueError, IndexError):
            continue

        if tty == "??" or tpgid <= 0:
            continue

        tty_path = f"/dev/{tty}" if not tty.startswith("/dev/") else tty
        tpgid_map[tty_path] = tpgid

        if pid == pgid:
            pgid_procs[(tty_path, pgid)] = comm

    fg_map: dict[str, str] = {}
    for tty_path, tpgid in tpgid_map.items():
        key = (tty_path, tpgid)
        if key in pgid_procs:
            fg_map[tty_path] = pgid_procs[key]

    return fg_map
