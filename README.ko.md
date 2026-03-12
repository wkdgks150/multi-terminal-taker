# MTT (Multi-Terminal Taker)

[English](README.md)

사용자 입력이 필요한 터미널을 자동으로 팝업시키는 macOS 데몬.
포커 멀티테이블 토너먼트(MTT) 클라이언트에서 영감을 받았습니다.

## 왜 만들었나

개발할 때 터미널을 여러 개 동시에 열어놓는 경우가 많습니다 — 빌드, 테스트, 서버, AI 에이전트 등.
대부분의 터미널은 알아서 돌아가지만, 가끔 사용자 입력이 필요합니다.

**문제**: 어떤 터미널이 입력을 기다리는지 하나하나 확인하기 번거롭다.

**해결**: 입력 대기 중인 터미널을 자동으로 앞으로 꺼내서, 순서대로 처리할 수 있게 해줍니다.

## 주요 기능

- **터미널 스캔** — Terminal.app / iTerm2의 모든 윈도우/탭을 1초마다 폴링
- **입력 대기 감지** — 훅 마커 + 쉘 프롬프트 + 콘텐츠 정체(8초) 3단계 감지
- **자동 팝업** — 입력이 필요한 터미널의 윈도우를 자동으로 맨 앞으로 이동
- **FIFO 대기열** — 여러 터미널이 동시에 입력 대기 시 선입선출 순서로 서빙
- **자기 자신 제외** — 데몬이 실행 중인 터미널은 자동으로 모니터링에서 제외

## 동작 원리

```
Terminal.app / iTerm2           MTT
┌──────────────┐
│ Tab 1: build │ ──running──┐
│ Tab 2: test  │ ──running──┤
│ Tab 3: claude│ ──idle────┐│   ┌─────────┐   ┌────────┐
│ Tab 4: claude│ ──busy────┤├──▶│  Queue   │──▶│ Pop up │
│ Tab 5: zsh   │ ──idle────┘│   │ (FIFO)  │   │ window │
│ Tab 6: server│ ──running──┘   └─────────┘   └────────┘
└──────────────┘
```

### 감지 방식

| 방식 | 트리거 | 속도 |
|------|--------|------|
| **훅 마커** | Claude Code idle/busy 훅이 마커 파일 생성/삭제 | 즉시 |
| **쉘 프롬프트** | 포어그라운드 프로세스가 zsh/bash/fish | 즉시 |
| **콘텐츠 정체** | interactive 앱(claude, node) + 콘텐츠 8초 불변 + 새 자식 프로세스 없음 | 8초 |

콘텐츠 정체 감지는 Claude Code의 `AskUserQuestion` 같은 mid-turn 대기 상태를 잡습니다.
busy 마커로 API 호출(자식 프로세스 없음) 중 오탐을 방지하고,
자식 프로세스 추적으로 긴 tool call 실행 중 오탐을 방지합니다.

## 지원 터미널

- **Terminal.app** — 완전 지원
- **iTerm2** — 완전 지원
- 실행 중인 앱을 자동 감지하며, 두 앱을 동시에 사용해도 동작합니다

## Claude Code 연동

[Claude Code](https://docs.anthropic.com/en/docs/claude-code) 훅과 연동하면 즉시 idle/busy 감지가 가능합니다.

`~/.claude/settings.json`에 추가:
```json
{
  "hooks": {
    "Stop": [
      {
        "matcher": "",
        "hooks": [{"type": "command", "command": "/path/to/mtt/scripts/hook-idle.sh"}]
      }
    ],
    "UserPromptSubmit": [
      {
        "matcher": "",
        "hooks": [{"type": "command", "command": "/path/to/mtt/scripts/hook-busy.sh"}]
      }
    ]
  }
}
```

훅 없이도 쉘 프롬프트 감지와 콘텐츠 정체로 동작합니다 — 훅은 반응 속도를 높여줄 뿐입니다.

## 사전 요구사항

- macOS (AppleScript 사용)
- Python 3.12+
- 접근성 권한 (시스템 설정 → 개인정보 보호 및 보안 → 접근성)

## 설치

```bash
pip install multi-terminal-taker
```

또는 소스에서:
```bash
git clone https://github.com/wkdgks150/multi-terminal-taker.git
cd multi-terminal-taker
pip install -e .
```

외부 의존성 없음 — Python 표준 라이브러리만 사용합니다.

## 사용법

```bash
mtt start    # 데몬 시작 (포어그라운드)
mtt status   # 실행 상태 확인
mtt stop     # 데몬 종료
```

```
[12:34:56] IDLE
[12:34:57] QUEUE: 2 | SERVING: /dev/ttys003
[12:34:58] QUEUE: 1 | SERVING: /dev/ttys007
[12:34:59] IDLE
```

## 파일 구조

```
src/mtt/
├── cli.py                # CLI (start/stop/status)
├── daemon.py             # 메인 폴링 루프 (1초 주기)
├── monitor.py            # 터미널 스캐너 (Terminal.app + iTerm2)
├── detector.py           # idle 감지 (훅 + 쉘 + 콘텐츠 정체)
├── queue.py              # FIFO 팝업 큐
└── window_controller.py  # 윈도우 팝업 (Terminal.app + iTerm2)
scripts/
├── hook-idle.sh          # Claude Code Stop 훅
└── hook-busy.sh          # Claude Code UserPromptSubmit 훅
```

## 테스트

```bash
pip install pytest
pytest
```

## 로드맵

- [x] 터미널 스캔 + 자동 팝업 + FIFO 대기열
- [x] Claude Code 훅 연동
- [x] 콘텐츠 정체 감지 (AskUserQuestion 등)
- [x] iTerm2 지원
- [ ] 메뉴바 상태 표시
- [ ] 우선순위 규칙

## 라이선스

[MIT](LICENSE)
