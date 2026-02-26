"""Control Terminal.app window order via AppleScript."""

import subprocess


def arrange(ordered_ttys: list[str]) -> bool:
    """Reorder Terminal.app windows so the given TTYs are in front, in order.

    First TTY = frontmost window (index 1), second = index 2, etc.
    Does NOT activate Terminal.app — just reorders windows quietly.
    Also selects the correct tab for each window.
    """
    if not ordered_ttys:
        return True

    # Process in reverse: each "set index to 1" pushes to front,
    # so the first TTY in the list ends up at index 1.
    blocks = []
    for tty in reversed(ordered_ttys):
        blocks.append(f'''\
        repeat with w in windows
            repeat with t in tabs of w
                if tty of t is "{tty}" then
                    set selected tab of w to t
                    set index of w to 1
                end if
            end repeat
        end repeat''')

    script = "tell application \"Terminal\"\n" + "\n".join(blocks) + "\nend tell"

    try:
        result = subprocess.run(
            ["osascript", "-e", script],
            capture_output=True, text=True, timeout=5,
        )
        return result.returncode == 0
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return False
