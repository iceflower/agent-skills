# technical-documentation

기술 문서 작성 가이드 (사용자 리서치, 품질 측정, 배포)

## 사용 방법

이 스킬은 [Agent Skills 오픈 표준](https://agentskills.io)을 따릅니다.

### 전역 설치

```bash
mkdir -p ~/.agents/skills/technical-documentation
cp SKILL.md ~/.agents/skills/technical-documentation/
```

### 프로젝트 설치

```bash
mkdir -p .agents/skills/technical-documentation
cp SKILL.md .agents/skills/technical-documentation/
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
