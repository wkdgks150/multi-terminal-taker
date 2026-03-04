"""Control Terminal.app window order via AppleScript."""

import subprocess


def popup(tty: str) -> bool:
    """Bring a single terminal window/tab to the front.

    Finds the window containing the given TTY, selects its tab,
    and sets the window to index 1 (frontmost).
    Does NOT activate Terminal.app — just reorders windows quietly.
    """
    if not tty:
        return False

    script = f'''\
tell application "Terminal"
    repeat with w in windows
        repeat with t in tabs of w
            if tty of t is "{tty}" then
                set selected tab of w to t
                set index of w to 1
                return
            end if
        end repeat
    end repeat
end tell'''

    try:
        result = subprocess.run(
            ["osascript", "-e", script],
            capture_output=True, text=True, timeout=3,
        )
        return result.returncode == 0
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return False
