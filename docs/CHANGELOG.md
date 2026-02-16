# Change Log (CHANGELOG)

> Records deviations from the plan that occur during development.
> During sync time, use this log to update SDD.md and FSD files.
> **Newest entries on top.**

---

## Rules

- Format: `- [YYYY-MM-DD] Description (related FSD: filename)`
- When sync is complete: mark the entry with `[synced]`

---

## Log

- [2026-02-16] TTY mtime 기반 idle 감지 → 콘텐츠 해시 기반으로 전환. TUI 앱이 idle 중에도 mtime 갱신하는 문제 해결 (related FSD: terminal-scan.md) [synced]
- [2026-02-16] SERVING 해제 조건: fg_process 변경 + 콘텐츠 사이클 완료(변화 후 6초 정지). Terminal.app 최상단일 때만 팝업 (related FSD: popup-queue.md) [synced]
