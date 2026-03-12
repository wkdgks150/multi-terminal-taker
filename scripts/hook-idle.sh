#!/bin/sh
# Claude Code Stop hook: mark terminal as IDLE
# Walks up process tree to find the controlling TTY.
MARKER_DIR="/tmp/mtt"
PID=$$
while [ "$PID" -gt 1 ]; do
    TTY=$(ps -o tty= -p "$PID" 2>/dev/null | tr -d ' ')
    if [ -n "$TTY" ] && [ "$TTY" != "??" ]; then
        mkdir -p "$MARKER_DIR"
        touch "$MARKER_DIR/${TTY}.idle"
        exit 0
    fi
    PID=$(ps -o ppid= -p "$PID" 2>/dev/null | tr -d ' ')
done
