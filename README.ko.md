# Terminal Activator

사용자 입력이 필요한 터미널을 자동으로 팝업시키는 macOS 데몬.
포커 멀티테이블 소프트웨어에서 영감을 받았습니다.

## 왜 만들었나

개발할 때 터미널을 10~20개 동시에 열어놓는 경우가 많습니다 — 빌드, 테스트, 서버, AI 에이전트 등.
화면 분할은 4개가 한계이고, 대부분의 터미널은 알아서 돌아가지만 가끔 사용자 입력이 필요합니다.

**문제**: 어떤 터미널이 입력을 기다리는지 하나하나 확인하기 번거롭다.

**해결**: 입력 대기 중인 터미널을 자동으로 앞으로 꺼내서, 순서대로 처리할 수 있게 해줍니다.

## 주요 기능

- **터미널 스캔** — Terminal.app의 모든 윈도우/탭을 2초마다 폴링
- **입력 대기 감지** — 쉘 프롬프트 상태이거나 TUI 앱이 10초 이상 멈춰 있으면 감지
- **자동 팝업** — 입력이 필요한 터미널의 윈도우를 자동으로 맨 앞으로 이동
- **FIFO 대기열** — 여러 터미널이 동시에 입력 대기 시 선입선출 순서로 서빙
- **자기 자신 제외** — 데몬이 실행 중인 터미널은 자동으로 모니터링에서 제외

## 동작 원리

```
┌─────────────┐     ┌──────────────┐     ┌───────────┐     ┌────────────────────┐
│   Monitor   │────▶│   Detector   │────▶│   Queue   │────▶│ Window Controller  │
│ (AppleScript│     │ (쉘 감지 +   │     │ (FIFO     │     │ (윈도우 z-order    │
│  + ps 명령) │     │  콘텐츠 해시)│     │  대기열)  │     │  재정렬)           │
└─────────────┘     └──────────────┘     └───────────┘     └────────────────────┘
     ▲                                                              │
     └──────────────────── 2초마다 반복 ────────────────────────────┘
```

1. **Monitor**: AppleScript로 Terminal.app 윈도우/탭 목록 수집 + `ps`로 포어그라운드 프로세스 식별
2. **Detector**: 포어그라운드가 쉘(zsh/bash/fish)이면 즉시 감지. TUI 앱이면 콘텐츠 해시로 10초간 변화 없을 때 감지
3. **Queue**: 입력 대기 터미널을 FIFO 순서로 관리. 상태 변화 시에만 윈도우 재정렬 트리거
4. **Window Controller**: AppleScript로 대기열 순서대로 윈도우 z-order 재정렬 (index 1 = 맨 앞)

## 사전 요구사항

- macOS (Terminal.app 필수)
- Python 3.12+
- 접근성 권한 (시스템 설정 → 개인정보 보호 및 보안 → 접근성)

## 설치

```bash
git clone https://github.com/ducat/terminal-activator.git
cd terminal-activator
pip install -e .
```

외부 의존성 없음 — Python 표준 라이브러리만 사용합니다.

## 사용법

```bash
# 데몬 시작 (포어그라운드)
terminal-activator start

# 실행 상태 확인
terminal-activator status

# 데몬 종료
terminal-activator stop
```

시작하면 2초 주기로 터미널을 감시하며, 상태를 한 줄로 출력합니다:

```
[12:34:56] IDLE
[12:34:58] QUEUE: 2 | FRONT: /dev/ttys003
[12:35:00] QUEUE: 1 | FRONT: /dev/ttys007
[12:35:02] IDLE
```

## 사용 시나리오

```
시간 0초:
  터미널 1: 빌드 완료 → 쉘 프롬프트 대기 중 ✅ 감지됨
  터미널 2: 테스트 완료 → 쉘 프롬프트 대기 중 ✅ 감지됨
  터미널 3: 서버 실행 중 → 로그 계속 출력 중 ❌ 감지 안 됨

  → 대기열: [터미널1, 터미널2]
  → 터미널 1이 자동으로 맨 앞으로 올라옴

시간 5초:
  사용자가 터미널 1에서 명령어 입력 → 포어그라운드가 쉘에서 다른 프로세스로 변경
  → 대기열: [터미널2]
  → 터미널 2가 자동으로 맨 앞으로 올라옴

시간 10초:
  터미널 2도 입력 완료
  → 대기열: []
  → IDLE 상태
```

## 파일 구조

```
terminal-activator/
├── src/terminal_activator/
│   ├── cli.py                # CLI 진입점 (start/stop/status)
│   ├── daemon.py             # 메인 이벤트 루프 (2초 주기)
│   ├── monitor.py            # Terminal.app 스캔 (AppleScript + ps)
│   ├── detector.py           # 입력 대기 판단 (쉘 감지 + 콘텐츠 해시)
│   ├── queue.py              # FIFO 대기열 관리
│   └── window_controller.py  # 윈도우 z-order 재정렬 (AppleScript)
├── tests/
│   ├── test_detector.py      # 감지기 테스트 (16개)
│   └── test_queue.py         # 대기열 테스트 (58개)
├── docs/
│   ├── BPD.md                # 비즈니스 계획서
│   ├── SDD.md                # 서비스 설계서
│   └── FSD/                  # 기능 명세서
│       ├── terminal-scan.md
│       ├── auto-popup.md
│       └── popup-queue.md
└── pyproject.toml            # 패키지 설정
```

## 기술 스택

| 구분 | 기술 | 이유 |
|------|------|------|
| 언어 | Python 3.12+ | 빠른 프로토타이핑, subprocess/ctypes 연동 |
| 윈도우 제어 | AppleScript (osascript) | Terminal.app TTY/탭/윈도우 접근의 유일한 안정적 방법 |
| 프로세스 모니터링 | ps + subprocess | 포어그라운드 프로세스 그룹 식별 |
| 의존성 | 없음 | 100% 표준 라이브러리, 설치 부담 제로 |

## 테스트

```bash
pytest
```

74개 테스트 — 감지기 상태 판단과 대기열 FIFO 로직을 집중 커버합니다.

## 개발 로드맵

- [x] **Phase 1 (MVP)**: 터미널 스캔 + 자동 팝업 + 대기열 관리
- [ ] **Phase 2 (UX)**: 메뉴바 상태 표시, 알림, 우선순위 규칙
- [ ] **Phase 3**: AI 에이전트 연동

## 라이선스

MIT
