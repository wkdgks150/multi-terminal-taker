# Service Design Document (SDD)

> **Project**: Terminal Activator
> **Last modified**: 2026-02-16
> **Version**: v0.1
> **Author**: 장한

---

## 1. Service Overview

Terminal Activator는 macOS에서 동작하는 백그라운드 데몬이다. Terminal.app의 모든 윈도우/탭을 모니터링하고, 사용자 입력을 기다리는 터미널을 감지하면 해당 윈도우를 최상단으로 팝업한다. 여러 터미널이 동시에 입력을 기다릴 경우 대기열로 관리하여, 하나씩 순서대로 서빙한다.

---

## 2. Architecture

### System Components

```
terminal-activator (Python daemon)
├── Monitor        # 주기적으로 Terminal.app 상태 수집
├── Detector       # 각 터미널의 "입력 대기" 여부 판정
├── Queue          # 입력 대기 터미널의 팝업 대기열 관리
└── WindowController  # AppleScript로 윈도우 최상단 팝업
```

### Data Flow

```
[Terminal.app tabs]
    → Monitor (polling, 1~2초 간격)
    → Detector (입력 대기 여부 판정)
    → Queue (대기열에 추가/제거)
    → WindowController (최상단 팝업 실행)
    → [사용자 입력]
    → Monitor (입력 완료 감지)
    → Queue (다음 터미널 서빙)
```

---

## 3. Core Mechanisms

### 3.1 터미널 상태 수집 (Monitor)

**AppleScript를 통한 Terminal.app 접근:**
- `tty of tab` → TTY 디바이스 경로 (예: `/dev/ttys005`)
- `busy of tab` → 프로세스 실행 중 여부
- `processes of tab` → 실행 중인 프로세스 목록
- `window id`, `frontmost`, `miniaturized` → 윈도우 상태

**ps 명령을 통한 프로세스 상태:**
- `ps -e -o pid,ppid,pgid,tpgid,stat,tty,comm` → 각 TTY의 포그라운드 프로세스 그룹 식별
- `PGID == TPGID` 이면 해당 프로세스가 TTY의 포그라운드

### 3.2 입력 대기 감지 (Detector)

**판정 신호 (우선순위 순):**

| # | Signal | Method | Meaning |
|---|--------|--------|---------|
| 1 | 포그라운드 프로세스 타입 | ps TPGID 비교 | 셸(zsh/bash)이 포그라운드면 → 프롬프트 대기 (확정) |
| 2 | TTY 디바이스 mtime | `stat /dev/ttysXXX` | 마지막 출력 시각. 오래되면 idle 가능성 높음 |
| 3 | 터미널 콘텐츠 | AppleScript `contents of tab` | 프롬프트 패턴 감지 (❯, $, ⏵⏵ 등) |

**판정 로직:**

```
IF 포그라운드 프로세스가 셸 (zsh/bash/fish)
    → WAITING_FOR_INPUT (확정)

ELSE IF 포그라운드 프로세스가 인터랙티브 프로그램 (claude, vim, node 등)
    → TTY mtime 확인 + 터미널 콘텐츠 분석으로 추가 판정
    → 예: claude가 "esc to interrupt" 없이 프롬프트 표시 중이면 입력 대기

ELSE
    → ACTIVE (개입 불필요)
```

**MVP에서는 Signal 1 (셸 포그라운드)만으로 시작.** 나머지는 Phase 2에서 추가.

### 3.3 대기열 관리 (Queue)

```
State Machine:
  IDLE        → 입력 대기 터미널 없음, 모니터링만
  SERVING     → 현재 하나의 터미널이 팝업되어 사용자 입력 대기 중
  QUEUED(n)   → n개의 터미널이 추가로 입력 대기 중 (FIFO)
```

**규칙:**
- 현재 팝업된 터미널이 없을 때 → 첫 번째 입력 대기 터미널 즉시 팝업
- 이미 팝업된 터미널이 있을 때 → 대기열에 추가, 순서 대기
- 팝업된 터미널에서 입력 완료 감지 시 → 대기열에서 다음 터미널 팝업
- 대기열 비면 → IDLE 상태로 복귀

**"입력 완료" 감지:**
- 셸 프롬프트에서 커맨드 입력 → 포그라운드 프로세스가 셸에서 다른 프로세스로 변경됨
- 이 전환을 감지하면 "입력 완료"로 판정

### 3.4 윈도우 팝업 (WindowController)

**AppleScript로 구현:**
1. TTY 경로로 대상 윈도우/탭 식별
2. 최소화 상태면 해제 (`set miniaturized to false`)
3. 해당 탭을 선택 (`set selected tab`)
4. 윈도우를 최상단으로 (`set frontmost to true`)
5. Terminal.app 활성화 (`activate`)

---

## 4. Tech Stack

| Area | Technology | Rationale |
|------|------------|-----------|
| Language | Python 3.12+ | 빠른 프로토타이핑, subprocess/ctypes 통합 용이, macOS 기본 탑재 |
| Window Control | AppleScript (osascript) | Terminal.app의 TTY/탭/윈도우 직접 접근 가능, 권한 추가 불필요 |
| Process Monitoring | ps + subprocess | 포그라운드 프로세스 그룹 식별, 추가 의존성 없음 |
| TTY Inspection | os.stat | 디바이스 mtime으로 idle 감지 |
| Packaging | pip / uv | 단일 패키지 배포 |

**의존성:** 없음 (Python 표준 라이브러리만 사용). MVP에서는 외부 패키지 0개.

---

## 5. User Interface

### CLI Commands

```bash
# 데몬 시작
terminal-activator start

# 데몬 중지
terminal-activator stop

# 상태 확인 (현재 모니터링 중인 터미널 수, 대기열 상태)
terminal-activator status
```

### 동작 흐름 (사용자 시점)

```
1. terminal-activator start 실행
2. 터미널 여러 개 열고 각각 작업 실행 (빌드, 테스트, AI 에이전트 등)
3. 다른 작업 하면서 대기
4. 어떤 터미널이 입력을 기다리면 → 해당 터미널이 앞으로 뜸
5. 입력 완료하면 → 다음 대기 터미널이 뜸
6. 반복
```

---

## 6. Data Model

### TerminalTab (in-memory)

| Field | Type | Description |
|-------|------|-------------|
| tty | str | TTY 디바이스 경로 (예: `/dev/ttys005`) |
| window_id | int | Terminal.app 윈도우 ID |
| tab_index | int | 윈도우 내 탭 인덱스 |
| state | enum | ACTIVE / WAITING / SERVING |
| fg_process | str | 현재 포그라운드 프로세스명 |
| last_state_change | datetime | 마지막 상태 변경 시각 |

### Queue (in-memory)

| Field | Type | Description |
|-------|------|-------------|
| serving | TerminalTab? | 현재 팝업 서빙 중인 터미널 |
| waiting | list[TerminalTab] | FIFO 대기열 |

DB 없음. 모든 상태는 메모리에만 존재. 데몬 재시작 시 초기화.

---

## 7. Project Structure

```
terminal-activator/
├── src/
│   └── terminal_activator/
│       ├── __init__.py
│       ├── cli.py              # CLI 엔트리포인트 (start/stop/status)
│       ├── daemon.py           # 메인 데몬 루프
│       ├── monitor.py          # Terminal.app 상태 수집
│       ├── detector.py         # 입력 대기 판정
│       ├── queue.py            # 대기열 관리
│       └── window_controller.py # AppleScript 윈도우 제어
├── tests/
├── docs/
├── pyproject.toml
└── CLAUDE.md
```

---

## 8. Constraints & Risks

| Risk | Impact | Mitigation |
|------|--------|------------|
| AppleScript 호출 지연 | 팝업 반응 속도 저하 | JXA(osascript -l JavaScript) 사용으로 최적화, 폴링 주기 조절 |
| macOS 보안 권한 | 접근성 권한 요구 가능 | 먼저 AppleScript만으로 동작 확인, 필요시 권한 안내 |
| 셸 외 프로세스 입력 대기 감지 | MVP에서 미지원 | Phase 1은 셸 프롬프트만. Phase 2에서 확장 |
| 폴링 방식의 CPU 사용량 | 리소스 낭비 | 폴링 주기 조절 (기본 2초), 변화 없으면 주기 늘림 |

---

## 9. Architecture Principles

1. **외부 의존성 제로** — Python 표준 라이브러리만. pip install 시 추가 다운로드 없음.
2. **단일 프로세스** — 데몬 하나가 모든 역할 수행. IPC 불필요.
3. **폴링 기반** — 이벤트 드리븐보다 단순. 정확도보다 단순성 우선.
4. **AppleScript 퍼스트** — Terminal.app 접근은 AppleScript가 유일하게 안정적인 방법.
