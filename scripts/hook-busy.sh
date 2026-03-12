#!/bin/sh
# Claude Code UserPromptSubmit hook: mark terminal as BUSY
# Walks up process tree to find the controlling TTY.
MARKER_DIR="/tmp/mtt"
PID=$$
while [ "$PID" -gt 1 ]; do
    TTY=$(ps -o tty= -p "$PID" 2>/dev/null | tr -d ' ')
    if [ -n "$TTY" ] && [ "$TTY" != "??" ]; then
        rm -f "$MARKER_DIR/${TTY}.idle"
        exit 0
    fi
    PID=$(ps -o ppid= -p "$PID" 2>/dev/null | tr -d ' ')
done
