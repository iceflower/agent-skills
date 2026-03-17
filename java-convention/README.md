# java-convention

Java 코딩 컨벤션 + 버전 마이그레이션 가이드 (8 → 25)

## 사용 방법

이 스킬은 [Agent Skills 오픈 표준](https://agentskills.io)을 따릅니다.

### 전역 설치

```bash
cp -r java-convention/ ~/.agents/skills/java-convention/
```

### 프로젝트 설치

```bash
cp -r java-convention/ .agents/skills/java-convention/
```

## 디렉토리 구조

```text
java-convention/
├── SKILL.md
├── README.md
└── references/
    └── migration.md
```

## 호환 도구

| 도구 | 전역 경로 | 프로젝트 경로 |
|------|-----------|---------------|
| OpenCode | `~/.agents/skills/` | `.agents/skills/` |
| Codex | `~/.agents/skills/` | `.agents/skills/` |
| Claude Code | `~/.claude/skills/` | `.claude/skills/` |
| Antigravity | `~/.gemini/antigravity/skills/` | `.agents/skills/` |

## 라이선스

MIT License
