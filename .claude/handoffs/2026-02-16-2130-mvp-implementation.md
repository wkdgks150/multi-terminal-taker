# Session Handoff — 2026-02-16 MVP Implementation Complete

## Status
Terminal Activator MVP 구현 완료. BPD→SDD→FSD→구현→디버깅→문서 sync까지 한 세션에 완료.

핵심 성과:
- 프로젝트 생성 (from template) + GitHub repo (wkdgks150/terminal-activator, private)
- 문서 작성: BPD.md, SDD.md, FSD 3개 (terminal-scan.md, auto-popup.md, popup-queue.md)
- MVP 코드 구현: monitor.py, detector.py, queue.py, window_controller.py, daemon.py, cli.py
- 다수 버그 수정 후 콘텐츠 해시 기반 감지 시스템으로 안정화
- FSD/CHANGELOG sync 완료

## Key Decisions
1. **TTY mtime 폐기 → 콘텐츠 해시 채택**: TUI 앱(claude 등)이 idle 중에도 TTY mtime을 ~0.5초마다 갱신하므로 mtime은 idle 감지에 사용 불가. `contents of tab` AppleScript → MD5 해시 비교가 유일하게 신뢰할 수 있는 신호.
2. **SERVING 해제 규칙 2가지**: (1) fg_process 변경 → 즉시 해제, (2) 콘텐츠가 한 번이라도 바뀐 후 6초(3폴) 정지 → 해제. 시간 기반 자동 해제 없음 — 사용자가 명시적으로 거부.
3. **Terminal.app 최상단일 때만 팝업**: 다른 앱 사용 중 팝업 금지. `System Events`로 frontmost app 확인.
4. **엄격한 FIFO 큐**: 서빙 중일 때 절대 다른 터미널 팝업 안 함. 큐에만 쌓음.

## Open Issues
1. **E2E 테스트 미완료**: 데몬이 idle 터미널 5개 감지 + 1개 서빙 + 4개 큐 상태까지 확인됨. 하지만 전체 사이클(채팅 → 응답 → 콘텐츠 정지 → 다음 터미널 팝업)은 사용자가 직접 검증하지 않음.
2. **초기 워밍업**: ContentTracker가 기준 해시를 쌓으려면 최소 10초(5폴) 필요. 데몬 시작 직후에는 감지가 안 될 수 있음.
3. **CLAUDE.md 태스크 백로그 미갱신**: 3개 feature 모두 `Pending` 상태로 남아있음. 실제로는 구현 완료.
4. **단위 테스트 없음**: 테스트 코드 미작성.

## Next Steps
1. **E2E 테스트**: 데몬 실행 후 실제로 claude 터미널에서 채팅 → 응답 완료 → 다음 터미널 자동 팝업 확인
2. **CLAUDE.md 백로그 업데이트**: 3개 feature 상태를 `Done`으로 변경
3. **단위 테스트 작성**: detector.py의 ContentTracker, queue.py의 PopupQueue 로직
4. **Phase 2 기능 검토**: 우선순위 큐, 알림음, 상태 표시 바 등

## Files Modified
```
# 생성
pyproject.toml
src/terminal_activator/__init__.py
src/terminal_activator/cli.py
src/terminal_activator/daemon.py
src/terminal_activator/detector.py
src/terminal_activator/monitor.py
src/terminal_activator/queue.py
src/terminal_activator/window_controller.py
docs/BPD.md
docs/SDD.md
docs/FSD/terminal-scan.md
docs/FSD/auto-popup.md
docs/FSD/popup-queue.md
docs/CHANGELOG.md
.gitignore

# 수정 (여러 차례 버그 수정)
src/terminal_activator/detector.py  — mtime → content hash 전환
src/terminal_activator/queue.py     — 서빙 해제 규칙 다수 변경
src/terminal_activator/daemon.py    — ContentTracker 통합
src/terminal_activator/monitor.py   — get_content_hash(), is_terminal_frontmost() 추가
docs/FSD/terminal-scan.md           — content hash 반영
docs/FSD/popup-queue.md             — SERVING 해제 규칙 반영
docs/CHANGELOG.md                   — 변경 기록 추가
```

## Context
- 사용자(장한)는 20개+ 터미널에서 claude를 동시 실행하는 환경. 분할 화면 물리적 한계(4개)를 넘기 위한 도구.
- 사용자 성격: 시간 기반 휴리스틱/자동 규칙 극도로 싫어함. "내가 정하겠다"는 철학. 기다림에 대한 관용은 높되, 오동작에 대한 관용은 매우 낮음.
- uv로 Python 환경 관리 중. venv 경로: `/Applications/GitHub/terminal-activator/.venv` (Python 3.14.3)
- 데몬 실행 명령: `cd /Applications/GitHub/terminal-activator && source .venv/bin/activate && terminal-activator start`
- 로그 위치: `/tmp/terminal-activator.log`, PID 파일: `/tmp/terminal-activator.pid`
- 미래 비전: "openclaw" AI 통합 — 터미널별 메신저 스타일 Q&A
