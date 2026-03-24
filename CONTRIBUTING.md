# Contributing Guide

Agent Skills 프로젝트에 기여해 주셔서 감사합니다.

## 스킬 구조

모든 스킬은 다음 구조를 따릅니다:

```text
<skill-name>/
├── SKILL.md           # 스킬 정의 (필수)
├── references/        # 참조 문서 (선택)
└── scripts/           # 검증/자동화 스크립트 (선택)
```

## SKILL.md 작성 규칙

### Frontmatter (필수)

```yaml
---
name: skill-name
description: >-
  Skill description in English. Include trigger phrases.
  Use when [situation].
license: MIT
metadata:
  author: iceflower
  version: "1.0"
  last-reviewed: "YYYY-MM"
---
```

- `name`: 디렉토리 이름과 동일
- `description`: `>-` 형식으로 작성, 영어로 작성
- `license`: `MIT`
- `metadata.last-reviewed`: 최종 검토 연월

### 본문 규칙

- **언어**: 영어로 작성
- **길이**: 500줄 이내 (초과 시 `references/`로 분리)
- **마크다운 형식**:
  - 헤딩 전후 빈 줄
  - 코드 블록 전후 빈 줄
  - 코드 블록에 언어 식별자 명시 (예: `java`, `yaml`, `bash`)
  - 테이블 파이프 정렬

### References 파일

- frontmatter 없이 마크다운 제목(`#`)부터 시작
- SKILL.md에서 상대경로로 참조: `[references/파일명.md](references/파일명.md)`
- 다른 스킬의 references를 참조할 때: `[../other-skill/references/파일명.md](../other-skill/references/파일명.md)`

## 스킬 추가 절차

1. 디렉토리 생성: `<skill-name>/SKILL.md`
2. frontmatter 작성 (위 규칙 참고)
3. 본문 작성 (500줄 이내)
4. **index 업데이트**: `index/SKILL.md` 라우팅 테이블에 추가
5. **README 업데이트**: `README.md` 스킬 목록에 추가, 스킬 수 갱신
6. 검증 스크립트 실행:

```bash
python3 scripts/lint_frontmatter.py .
python3 scripts/check_references.py .
python3 scripts/check_index.py .
```

## 스킬 수정 절차

1. 기존 내용 유지하며 수정
2. 500줄 초과 시 `references/`로 세부 내용 분리
3. references 파일을 추가/삭제한 경우 링크 유효성 확인
4. 검증 스크립트 실행

## PR 규칙

### 제목

```text
feat: <skill-name> (<한국어 설명>) 스킬 추가
fix: <skill-name> 스킬 <수정 내용>
docs: README.md 업데이트
```

### 체크리스트

- [ ] SKILL.md frontmatter에 필수 필드 포함
- [ ] SKILL.md 500줄 이내
- [ ] references 링크가 모두 유효
- [ ] index/SKILL.md 라우팅 테이블에 포함
- [ ] README.md 스킬 목록에 포함
- [ ] `python3 scripts/lint_frontmatter.py .` 통과
- [ ] `python3 scripts/check_references.py .` 통과
- [ ] `python3 scripts/check_index.py .` 통과

## 라이선스

기여하신 내용은 MIT License로 배포됩니다.
