"""Control terminal window order via AppleScript.

Supports Terminal.app and iTerm2. Tries both apps to find the target TTY.
"""

import subprocess


def popup(tty: str) -> bool:
    """Bring a single terminal window/tab to the front.

    Finds the window containing the given TTY across Terminal.app and iTerm2,
    selects its tab, and sets the window to index 1 (frontmost).
    Does NOT activate the app — just reorders windows quietly.
    """
    if not tty:
        return False

    script = f'''\
set found to false
tell application "System Events"
    set procNames to name of every application process
end tell

if procNames contains "Terminal" then
    tell application "Terminal"
        repeat with w in windows
            repeat with t in tabs of w
                if tty of t is "{tty}" then
                    set selected tab of w to t
                    set index of w to 1
                    set found to true
                    exit repeat
                end if
            end repeat
            if found then exit repeat
        end repeat
    end tell
end if

if not found and procNames contains "iTerm2" then
    tell application "iTerm2"
        repeat with w in windows
            repeat with t in tabs of w
                repeat with s in sessions of t
                    if tty of s is "{tty}" then
                        select s
                        set index of w to 1
                        return
                    end if
                end repeat
            end repeat
        end repeat
    end tell
end if'''

    try:
        result = subprocess.run(
            ["osascript", "-e", script],
            capture_output=True, text=True, timeout=3,
        )
        return result.returncode == 0
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return False
