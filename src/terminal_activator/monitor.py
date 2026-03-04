"""Scan Terminal.app windows/tabs and process states."""

import subprocess
import re
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class TerminalTab:
    tty: str
    window_id: int
    tab_index: int
    fg_process: str = ""
    tty_idle_seconds: float = 0.0
    waiting_for_input: bool = False
    state: str = "ACTIVE"  # ACTIVE / WAITING / SERVING
    last_state_change: datetime = field(default_factory=datetime.now)


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
            set output to output & wid & "\\t" & tabIdx & "\\t" & ttyPath & linefeed
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
        if len(parts) < 3:
            continue
        try:
            tabs.append(TerminalTab(
                window_id=int(parts[0]),
                tab_index=int(parts[1]),
                tty=parts[2].strip(),
            ))
        except (ValueError, IndexError):
            continue

    return tabs, frontmost_tty


def get_content_hash(tty: str) -> str:
    """Get a hash of the terminal tab's recent content for the given TTY.

    Uses 'history' instead of 'contents' because 'contents' returns a
    reference string (not actual text) for alternate-screen apps like
    Claude Code, vim, etc.  Only the last 1000 chars are hashed for speed.
    """
    script = f'''
    tell application "Terminal"
        repeat with w in windows
            repeat with t in tabs of w
                if tty of t is "{tty}" then
                    set h to history of t
                    if length of h > 1000 then
                        return text ((length of h) - 999) thru (length of h) of h
                    end if
                    return h
                end if
            end repeat
        end repeat
        return ""
    end tell
    '''
    try:
        result = subprocess.run(
            ["osascript", "-e", script],
            capture_output=True, text=True, timeout=3,
        )
        if result.returncode == 0:
            import hashlib
            return hashlib.md5(result.stdout.encode()).hexdigest()
    except (subprocess.TimeoutExpired, FileNotFoundError):
        pass
    return ""



def get_frontmost_tty() -> str:
    """Return the TTY of the currently frontmost Terminal.app tab.

    Returns "" if Terminal.app is not the active app or has no windows.
    """
    try:
        result = subprocess.run(
            ["osascript", "-e", APPLESCRIPT_FRONTMOST_TTY],
            capture_output=True, text=True, timeout=3,
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except (subprocess.TimeoutExpired, FileNotFoundError):
        pass
    return ""


def scan_foreground_processes() -> dict[str, str]:
    """Return {tty: fg_process_name} by parsing ps output.

    Uses TPGID to identify the foreground process group of each TTY,
    then finds the process whose PGID == TPGID.
    """
    try:
        result = subprocess.run(
            ["ps", "-e", "-o", "pid,pgid,tpgid,tty,comm"],
            capture_output=True, text=True, timeout=5,
        )
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return {}

    if result.returncode != 0:
        return {}

    # Parse ps output: find foreground process for each TTY
    # tpgid_map: {tty: tpgid}
    # pgid_procs: {(tty, pgid): process_name}
    tpgid_map: dict[str, int] = {}
    pgid_procs: dict[tuple[str, int], str] = {}

    for line in result.stdout.strip().split("\n")[1:]:  # skip header
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

        # Normalize TTY: "ttys005" -> "/dev/ttys005"
        tty_path = f"/dev/{tty}" if not tty.startswith("/dev/") else tty

        tpgid_map[tty_path] = tpgid

        # Track process where PID == PGID (group leader)
        if pid == pgid:
            pgid_procs[(tty_path, pgid)] = comm

    # Match: for each TTY, find the process whose PGID == TPGID
    fg_map: dict[str, str] = {}
    for tty_path, tpgid in tpgid_map.items():
        key = (tty_path, tpgid)
        if key in pgid_procs:
            fg_map[tty_path] = pgid_procs[key]

    return fg_map
