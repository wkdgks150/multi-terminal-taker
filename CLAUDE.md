# Project Agent Guide

## Project Overview

- **Project name**: Terminal Activator
- **Description**: Multi-terminal activator that pops up terminals requiring user input, inspired by poker multi-table software
- **Owner**: ducat
- **Current phase**: Phase 0 (Planning)
- **Tech stack**: (fill after SDD)

---

## Session Startup Checklist

On every new session:
1. `git fetch --dry-run` → inform user of remote changes.
2. `git status` → inform user of uncommitted local changes.
3. Check `docs/` to understand current project progress.
4. Verify entry in `/Applications/GitHub/projects.yaml`.

---

## Workflow

### Planning (main terminal)
```
BPD.md → SDD.md → FSD/*.md → CLAUDE.md task backlog → Development
```
1. Fill docs in order. After each doc, run `/planner` for review.
2. During planning, always ask clarifying questions until the user says to stop.

### Implementation (separate terminal)
1. Run `/implement` skill for the full workflow, or manually:
   - Read FSD → implement → `/reviewer` + `/tester` → commit → `/sync-time`
2. One feature at a time. Record spec deviations in `docs/CHANGELOG.md`.

### Available Skills
| Skill | Purpose |
|-------|---------|
| `/planner` | Review planning docs |
| `/reviewer` | Code review |
| `/tester` | Test review & execution |
| `/implement` | Full implementation workflow |
| `/sync-time` | Post-implementation doc sync |

---

## Document Structure

```
docs/
├── BPD.md              # Business Plan Document
├── SDD.md              # Service Design Document
├── FSD/
│   ├── _TEMPLATE.md    # Feature Spec template
│   └── [feature].md    # One per feature (kebab-case)
├── CHANGELOG.md        # Dev-time change log
└── DECISIONS.md        # Key decision records
```

### Document Rules
- Fixed names: `BPD.md`, `SDD.md`, `CHANGELOG.md`, `DECISIONS.md` — never rename.
- FSD: kebab-case English (e.g., `auth.md`, `club-create.md`).
- Never delete or rename `##` headers. Update `Last modified` on every edit.
- CHANGELOG: `- [YYYY-MM-DD] Description (related FSD: filename)` — newest on top.
- DECISIONS: `## [YYYY-MM-DD] Title` + Background / Decision / Rationale — never delete.

---

## Coding Conventions

> Customize for your tech stack.

- Variables/functions: camelCase | Components: PascalCase | Filenames: kebab-case
- Indentation: 2 spaces | Semicolons: yes
- Commit: `type: description` (feat/fix/docs/refactor/test/chore). Korean OK.

---

## Architecture Principles

> Fill after SDD.

1.
2.
3.

---

## Tech Stack

> Fill after SDD.

- **Frontend**:
- **Backend**:
- **Database**:
- **Infrastructure**:

---

## Development Notes

1. Always read FSD before implementing.
2. Record spec deviations in CHANGELOG.md immediately.
3. One feature at a time — no parallel feature work.
4. No security vulnerabilities. Error handling at boundaries only.
5. No over-abstraction — build what's needed now.
6. Sub-agents don't consume main context — delegate heavy reads/writes.

---

## Task Backlog

| # | Feature | FSD File | Status |
|---|---------|----------|--------|
| 1 | Terminal Scan (모니터 + 감지) | terminal-scan.md | Done |
| 2 | Auto Popup (윈도우 팝업) | auto-popup.md | Done |
| 3 | Popup Queue (대기열 + 서빙) | popup-queue.md | Done |
