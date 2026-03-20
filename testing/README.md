# testing

BDD 스타일 테스트 작성 규칙 (단위 테스트, 통합 테스트, 계약 테스트, 성능 테스트)

## 사용 방법

이 스킬은 [Agent Skills 오픈 표준](https://agentskills.io)을 따릅니다.

### 전역 설치

```bash
cp -r testing/ ~/.agents/skills/testing/
```

### 프로젝트 설치

```bash
cp -r testing/ .agents/skills/testing/
```

## 디렉토리 구조

```text
testing/
├── SKILL.md
├── README.md
└── references/
    ├── integration.md
    ├── contract.md
    └── performance.md
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
