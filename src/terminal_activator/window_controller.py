"""Control Terminal.app windows via AppleScript."""

import subprocess


def popup(tty: str) -> bool:
    """Bring the Terminal.app window containing the given TTY to the front."""
    script = f"""\
tell application "Terminal"
    repeat with w in windows
        repeat with t in tabs of w
            if tty of t is "{tty}" then
                if miniaturized of w then
                    set miniaturized of w to false
                end if
                set selected tab of w to t
                set index of w to 1
            end if
        end repeat
    end repeat
    activate
end tell
"""
    try:
        result = subprocess.run(
            ["osascript", "-e", script],
            capture_output=True, text=True, timeout=5,
        )
        return result.returncode == 0
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return False
