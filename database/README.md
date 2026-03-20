# database

데이터베이스 공통 규칙 + MySQL/PostgreSQL 특화 가이드

## 사용 방법

이 스킬은 [Agent Skills 오픈 표준](https://agentskills.io)을 따릅니다.

### 전역 설치

```bash
cp -r database/ ~/.agents/skills/database/
```

### 프로젝트 설치

```bash
cp -r database/ .agents/skills/database/
```

## 디렉토리 구조

```text
database/
├── SKILL.md
├── README.md
└── references/
    ├── mysql.md
    └── postgresql.md
```

## 호환 도구

| 도구 | 전역 경로 | 프로젝트 경로 |
| ---- | --------- | ------------- |
| OpenCode | `~/.agents/skills/` | `.agents/skills/` |
| Codex | `~/.agents/skills/` | `.agents/skills/` |
| Claude Code | `~/.claude/skills/` | `.claude/skills/` |
| Antigravity | `~/.gemini/antigravity/skills/` | `.agents/skills/` |

## 라이선스

MIT License
