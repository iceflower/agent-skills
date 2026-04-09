# spring-ai

Spring AI (ChatClient, Tool Calling, Prompt Template, Vector Store, RAG, MCP 통합)

## 사용 방법

이 스킬은 [Agent Skills 오픈 표준](https://agentskills.io)을 따릅니다.

### 전역 설치

```bash
cp -r spring-ai/ ~/.agents/skills/spring-ai/
```

### 프로젝트 설치

```bash
cp -r spring-ai/ .agents/skills/spring-ai/
```

## 디렉토리 구조

```text
spring-ai/
├── SKILL.md
├── README.md
└── references/
    ├── advanced-rag-agents.md
    ├── chatclient-patterns.md
    ├── migration-2x.md
    ├── tool-calling.md
    └── vector-store-rag.md
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
