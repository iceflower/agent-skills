# observability

옵저버빌리티 통합 (메트릭, 트레이싱, 알림, OTel SDK, OTLP, Collector, 헬스체크)

## 사용 방법

이 스킬은 [Agent Skills 오픈 표준](https://agentskills.io)을 따릅니다.

### 전역 설치

```bash
cp -r observability/ ~/.agents/skills/observability/
```

### 프로젝트 설치

```bash
cp -r observability/ .agents/skills/observability/
```

## 디렉토리 구조

```text
observability/
├── SKILL.md
├── README.md
└── references/
    ├── alerting-rules.md
    ├── health-checks.md
    ├── otel-collector.md
    ├── otel-sdk-patterns.md
    ├── prometheus-queries.md
    ├── semantic-conventions.md
    └── slo-sli-design.md
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
