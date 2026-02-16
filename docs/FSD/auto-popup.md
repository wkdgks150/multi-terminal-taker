# Feature Spec: Auto Popup

> **Filename**: auto-popup.md
> **Last modified**: 2026-02-16
> **Version**: v0.1
> **Status**: Pending

---

## 1. Feature Overview

입력 대기로 판정된 터미널 윈도우를 최상단으로 팝업하여 사용자의 즉각적인 응답을 유도한다. Terminal.app의 윈도우/탭을 AppleScript로 제어한다.

---

## 2. User Stories

- As a user, I want the terminal that needs my input to automatically appear in front, so that I can respond immediately without searching for it.

---

## 3. Input / Output

### Input
| Field | Type | Description |
|-------|------|-------------|
| tty | str | 팝업할 대상 터미널의 TTY 경로 |
| window_id | int | Terminal.app 윈도우 ID |
| tab_index | int | 윈도우 내 탭 인덱스 |

### Output
| Field | Type | Description |
|-------|------|-------------|
| success | bool | 팝업 성공 여부 |

---

## 4. Business Logic

### 4.1 윈도우 팝업 절차 (window_controller.py)

TTY 경로를 키로 대상 윈도우를 찾아 최상단으로 올린다:

```applescript
tell application "Terminal"
    repeat with w in windows
        repeat with t in tabs of w
            if tty of t is "{target_tty}" then
                -- 최소화 상태면 해제
                if miniaturized of w then
                    set miniaturized of w to false
                end if
                -- 해당 탭 선택 (멀티탭 윈도우일 경우)
                set selected tab of w to t
                -- 윈도우 최상단
                set index of w to 1
            end if
        end repeat
    end repeat
    activate
end tell
```

### 4.2 팝업 조건

팝업은 Queue 컴포넌트가 결정한다. WindowController는 "이 터미널을 팝업해라"는 지시만 수행:
- Queue가 `popup(tty)` 호출 → WindowController가 실행
- WindowController는 팝업 성공/실패만 반환

### 4.3 팝업 후 동작

팝업 후 추가 동작 없음. 사용자가 해당 터미널에서 입력하기를 기다린다. 입력 완료 감지는 terminal-scan의 다음 폴링 주기에서 처리.

---

## 5. Error Handling

| Scenario | Handling |
|----------|----------|
| 대상 윈도우가 닫혀있음 | 팝업 실패 반환, Queue에서 제거 |
| Terminal.app이 응답 없음 | 타임아웃 후 실패 반환, 다음 주기에 재시도 |
| 윈도우는 있으나 탭이 없음 (탭이 닫힘) | 팝업 실패 반환, Queue에서 제거 |

---

## 6. Development Notes

- `set index of w to 1`이 `set frontmost of w to true`보다 안정적일 수 있음. 테스트 필요.
- `activate`를 마지막에 한 번만 호출하여 Terminal.app을 전면으로 가져옴.
- 팝업 시 사운드/시각 알림은 MVP 이후. Nice-to-have.
- AppleScript 호출은 동기식. 팝업 한 번에 ~100ms 이내 예상.
