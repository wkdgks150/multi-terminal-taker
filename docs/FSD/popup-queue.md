# Feature Spec: Popup Queue

> **Filename**: popup-queue.md
> **Last modified**: 2026-02-16
> **Version**: v0.1
> **Status**: Pending

---

## 1. Feature Overview

여러 터미널이 동시에 입력을 대기할 때, 한 번에 하나씩 순서대로 서빙하는 대기열 시스템. 현재 팝업된 터미널에서 입력이 완료되면 다음 대기 터미널을 팝업한다.

핵심 원칙: **사용자는 한 번에 하나의 터미널에만 집중한다.**

---

## 2. User Stories

- As a user, I want terminals to queue up when multiple need my input, so that I can handle them one at a time without being overwhelmed.
- As a user, I want the next terminal to appear automatically after I finish with the current one, so that the workflow is seamless.

---

## 3. State Machine

```
         감지 없음          첫 번째 감지
  IDLE ◄──────────── IDLE ──────────────► SERVING
   ▲                                        │ ▲
   │ 대기열 빔                    추가 감지  │ │ 입력 완료 + 대기열 있음
   │                                        ▼ │
   └────────────────────────────────── QUEUED(n)
         입력 완료 + 대기열 빔
```

### States

| State | Description |
|-------|-------------|
| IDLE | 입력 대기 터미널 없음. 모니터링만 수행. |
| SERVING | 하나의 터미널이 팝업되어 사용자 입력 대기 중. |
| QUEUED(n) | SERVING 상태에서 추가로 n개 터미널이 입력 대기 중. FIFO. |

---

## 4. Business Logic

### 4.1 SERVING 해제 규칙

**두 가지 해제 조건:**
1. **fg_process 변경**: 셸에서 커맨드 실행, 또는 앱 종료 → 즉시 해제
2. **콘텐츠 사이클 완료**: 콘텐츠가 한 번이라도 바뀐 후, 6초간 정지 → 해제

**절대 규칙:**
- SERVING 중에는 다른 터미널을 팝업하지 않는다. 큐에만 쌓는다.
- Terminal.app이 최상단 앱이 아니면 팝업하지 않는다.

### 4.2 스캔 결과 반영 (queue.update)

매 폴링 주기마다 호출:

```python
def update(self, tabs: list[TerminalTab]):
    waiting_ttys = {t.tty for t in tabs if t.waiting_for_input}

    # 1. SERVING 해제 판정 (fg 변경 또는 콘텐츠 사이클 완료)

    # 2. 대기열에서 이미 입력 완료된 터미널 제거
    self.waiting = [t for t in self.waiting if t.tty in waiting_ttys]

    # 3. 새로 입력 대기가 된 터미널을 대기열에 추가
    known_ttys = set()
    if self.serving:
        known_ttys.add(self.serving.tty)
    known_ttys.update(t.tty for t in self.waiting)

    for tab in tabs:
        if tab.waiting_for_input and tab.tty not in known_ttys:
            self.waiting.append(tab)

    # 4. serving이 비었고 대기열에 있으면 → 다음 터미널 팝업
    if not self.serving and self.waiting:
        next_tab = self.waiting.pop(0)
        self.serving = next_tab
        window_controller.popup(next_tab)
```

### 4.3 "입력 완료" 판정

**셸 (fg = zsh/bash):**
- fg_process가 셸에서 다른 프로세스로 변경 → 커맨드 실행 → 입력 완료

**인터랙티브 프로그램 (fg = claude 등):**
- 터미널 콘텐츠가 한 번이라도 변경 (사용자 상호작용 발생)
- 이후 콘텐츠 6초 정지 (3회 연속 동일 해시) → 응답 완료 → 입력 완료

### 4.3 자기 터미널 제외

데몬이 실행 중인 터미널은 항상 셸 프롬프트 대기 상태로 보인다. 시작 시 자신의 TTY를 기록하고 스캔 대상에서 제외한다.

```python
import os
self.own_tty = os.ttyname(0)  # 데몬 자신의 TTY
```

### 4.4 중복 팝업 방지

같은 터미널을 연속으로 팝업하지 않는다:
- serving 중인 터미널이 여전히 입력 대기 → 상태 유지, 재팝업 안 함
- 대기열에 이미 있는 터미널 → 중복 추가 안 함

---

## 5. Error Handling

| Scenario | Handling |
|----------|----------|
| serving 터미널의 윈도우가 닫힘 | serving을 None으로 리셋, 다음 대기 터미널 팝업 |
| 대기열의 터미널 윈도우가 닫힘 | 대기열에서 제거 |
| 팝업 실패 | 해당 터미널 대기열에서 제거, 다음 터미널 시도 |
| Terminal.app 전체 종료 | 모든 상태 초기화, IDLE로 복귀, 재시작 대기 |

---

## 6. Development Notes

- Queue는 순수 인메모리. 데몬 재시작 시 초기화되며 이는 의도된 동작.
- FIFO 순서가 기본. 우선순위 규칙은 Phase 2.
- `status` 커맨드에서 현재 상태 출력: `IDLE`, `SERVING: /dev/ttys005`, `QUEUED: 3 terminals`.
- 폴링 주기(기본 2초)가 곧 반응 속도의 상한. 사용자 체감상 2초 이내면 충분.
