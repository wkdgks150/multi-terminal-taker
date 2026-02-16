# Feature Spec: Terminal Scan

> **Filename**: terminal-scan.md
> **Last modified**: 2026-02-16
> **Version**: v0.1
> **Status**: Pending

---

## 1. Feature Overview

Terminal.app의 모든 윈도우/탭을 주기적으로 스캔하여, 각 터미널의 현재 상태를 수집하고 "사용자 입력 대기" 여부를 판정한다. 이것이 전체 시스템의 기반 데이터를 생산하는 컴포넌트다.

---

## 2. User Stories

- As a user, I want the system to automatically detect which terminals are waiting for my input, so that I don't have to manually check each one.

---

## 3. Input / Output

### Input
없음. 시스템이 자동으로 Terminal.app을 폴링한다.

### Output (per scan cycle)
| Field | Type | Description |
|-------|------|-------------|
| tty | str | TTY 디바이스 경로 (예: `/dev/ttys005`) |
| window_id | int | Terminal.app 윈도우 ID |
| tab_index | int | 윈도우 내 탭 인덱스 |
| fg_process | str | 포그라운드 프로세스명 |
| is_shell_foreground | bool | 셸이 포그라운드인지 여부 |
| waiting_for_input | bool | 입력 대기 판정 결과 |

---

## 4. Business Logic

### 4.1 Terminal.app 상태 수집 (monitor.py)

AppleScript로 Terminal.app의 모든 윈도우/탭 정보를 한 번에 수집한다.

```applescript
tell application "Terminal"
    set result to ""
    repeat with w in windows
        set wid to id of w
        set tabIdx to 0
        repeat with t in tabs of w
            set tabIdx to tabIdx + 1
            set ttyPath to tty of t
            set isBusy to busy of t
            set result to result & wid & "," & tabIdx & "," & ttyPath & "," & isBusy & linefeed
        end repeat
    end repeat
    return result
end tell
```

결과를 파싱하여 TerminalTab 객체 리스트로 변환.

### 4.2 포그라운드 프로세스 식별

`ps -e -o pid,pgid,tpgid,tty,comm` 실행 후 파싱:
1. 각 TTY의 TPGID(터미널 포그라운드 프로세스 그룹 ID) 추출
2. PGID == TPGID인 프로세스를 찾으면 그것이 포그라운드 프로세스
3. 포그라운드 프로세스의 comm(명령어명) 확인

### 4.3 입력 대기 판정 (detector.py)

**판정 규칙:**
```
1. 포그라운드 프로세스가 셸 (zsh, bash, fish, sh) → waiting_for_input = True
2. 비-셸 프로세스 (claude 등 TUI 앱):
   → 터미널 콘텐츠 해시를 매 폴링마다 비교
   → 5회 연속 동일 (10초) → waiting_for_input = True
```

셸 프로세스 식별: comm이 `-zsh`, `zsh`, `-bash`, `bash`, `fish`, `sh` 중 하나.

**참고**: TTY mtime은 TUI 앱이 idle 중에도 갱신하므로 사용하지 않음. 콘텐츠 해시가 유일하게 정확한 신호.

### 4.4 폴링 루프

```python
while running:
    tabs = monitor.scan_terminals()      # AppleScript
    ps_info = monitor.scan_processes()   # ps 명령
    for tab in tabs:
        tab.fg_process = ps_info.get(tab.tty)
        tab.waiting_for_input = detector.is_waiting(tab)
    queue.update(tabs)                   # 대기열에 반영
    sleep(POLL_INTERVAL)                 # 기본 2초
```

---

## 5. Error Handling

| Scenario | Handling |
|----------|----------|
| Terminal.app 미실행 | 스캔 스킵, 다음 주기에 재시도 |
| AppleScript 타임아웃 | 해당 주기 스킵, 로그 출력 |
| ps 명령 실패 | 해당 주기 스킵, 로그 출력 |
| TTY 매핑 실패 (AppleScript TTY ↔ ps TTY 불일치) | 해당 탭 스킵 |

---

## 6. Development Notes

- AppleScript 호출은 subprocess로 `osascript -e` 실행. 한 번의 AppleScript 호출로 모든 탭 정보를 수집하여 호출 횟수 최소화.
- ps도 한 번 호출로 전체 프로세스 목록을 가져와서 메모리에서 필터링.
- 데몬 자체의 터미널(terminal-activator를 실행한 터미널)은 감지 대상에서 제외해야 한다. 자신의 TTY를 기억하고 필터링.
- `busy of tab`은 "탭에서 프로세스가 실행 중"을 의미. 셸만 있으면 false. 참고 신호로 활용 가능하나 MVP에서는 ps TPGID 방식이 더 정확.
