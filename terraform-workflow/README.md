# terraform-workflow

Terraform 핵심 워크플로우 + AWS/Azure/GCP 프로바이더 가이드

## 사용 방법

이 스킬은 [Agent Skills 오픈 표준](https://agentskills.io)을 따릅니다.

### 전역 설치

```bash
cp -r terraform-workflow/ ~/.agents/skills/terraform-workflow/
```

### 프로젝트 설치

```bash
cp -r terraform-workflow/ .agents/skills/terraform-workflow/
```

## 디렉토리 구조

```text
terraform-workflow/
├── SKILL.md
├── README.md
└── references/
    ├── aws-provider.md
    ├── azure-provider.md
    └── gcp-provider.md
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
