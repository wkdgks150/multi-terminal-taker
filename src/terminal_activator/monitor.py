"""Scan terminal windows/tabs and process states.

Supports Terminal.app and iTerm2. Automatically detects which apps are running.
"""

import subprocess
from dataclasses import dataclass


@dataclass
class TerminalTab:
    tty: str
    window_id: int
    tab_index: int
    app: str = ""  # "Terminal" or "iTerm2"
    fg_process: str = ""
    content_len: int = 0
    waiting_for_input: bool = False


APPLESCRIPT_SCAN = """\
set appName to ""
set termRunning to false
set itermRunning to false
tell application "System Events"
    set appName to name of first application process whose frontmost is true
    set procNames to name of every application process
    set termRunning to procNames contains "Terminal"
    set itermRunning to procNames contains "iTerm2"
end tell
set frontTTY to ""
set output to ""

if termRunning then
    tell application "Terminal"
        repeat with w in windows
            set wid to id of w
            set tabIdx to 0
            repeat with t in tabs of w
                set tabIdx to tabIdx + 1
                set ttyPath to tty of t
                set hLen to length of history of t
                set output to output & "T" & "\\t" & wid & "\\t" & tabIdx & "\\t" & ttyPath & "\\t" & hLen & linefeed
            end repeat
        end repeat
        if appName is "Terminal" and (count of windows) > 0 then
            set frontTTY to tty of selected tab of window 1
        end if
    end tell
end if

if itermRunning then
    tell application "iTerm2"
        repeat with w in windows
            set wid to id of w
            set tabIdx to 0
            repeat with t in tabs of w
                set tabIdx to tabIdx + 1
                repeat with s in sessions of t
                    set ttyPath to tty of s
                    set cLen to length of contents of s
                    set output to output & "I" & "\\t" & wid & "\\t" & tabIdx & "\\t" & ttyPath & "\\t" & cLen & linefeed
                end repeat
            end repeat
        end repeat
        if appName is "iTerm2" and (count of windows) > 0 then
            set frontTTY to tty of current session of current tab of current window
        end if
    end tell
end if

return output & "FRONT\\t" & frontTTY
"""


def scan_terminals() -> tuple[list[TerminalTab], str]:
    """Scan all terminal windows/tabs and frontmost TTY in one call.

    Supports Terminal.app and iTerm2. Returns (tabs, frontmost_tty).
    frontmost_tty is "" if no supported terminal app is the active app.
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

    app_map = {"T": "Terminal", "I": "iTerm2"}
    tabs = []
    frontmost_tty = ""
    for line in result.stdout.strip().split("\n"):
        if not line.strip():
            continue
        parts = line.split("\t")
        if len(parts) >= 2 and parts[0] == "FRONT":
            frontmost_tty = parts[1].strip()
            continue
        if len(parts) < 5:
            continue
        try:
            tabs.append(TerminalTab(
                app=app_map.get(parts[0], ""),
                window_id=int(parts[1]),
                tab_index=int(parts[2]),
                tty=parts[3].strip(),
                content_len=int(parts[4]),
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
