# code-quality

코드 품질 6대 원칙 + 리팩토링 기법 (코드 스멜, 추출/인라인, 조건문 단순화)

## 사용 방법

이 스킬은 [Agent Skills 오픈 표준](https://agentskills.io)을 따릅니다.

### 전역 설치

```bash
cp -r code-quality/ ~/.agents/skills/code-quality/
```

### 프로젝트 설치

```bash
cp -r code-quality/ .agents/skills/code-quality/
```

## 디렉토리 구조

```text
code-quality/
├── SKILL.md
├── README.md
└── references/
    └── refactoring.md
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
