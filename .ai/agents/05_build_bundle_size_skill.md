# Agent 05: Build / Bundle Size Skill

## Mission
번들 분석, 트리쉐이킹, 의존성 경량화, 동적 import, 리소스 최적화, 빌드 모드를 분석하여 번들/앱 크기를 감소시킨다.

## Scope
- 번들 크기 분석 (JS 번들, 네이티브 에셋)
- 트리쉐이킹 효과 확인
- 대용량 의존성 식별 및 대안 제안
- 동적 import / lazy loading 기회
- 이미지/에셋 최적화 (포맷, 크기)
- 빌드 플래그 / development vs production 모드

## Non-Goals
- 런타임 성능 최적화
- UI 개선

## Inputs (우선순위순)
1. `prometheus-app/package.json` — 의존성 목록
2. `prometheus-app/app.json` / `app.config.*` — Expo 설정
3. `prometheus-app/tsconfig.json` — TS 빌드 설정
4. `prometheus-app/babel.config.js` — Babel 플러그인
5. `prometheus-app/assets/` — 정적 에셋
6. `prometheus-api/requirements.txt` — 백엔드 의존성
7. `prometheus-api/Dockerfile` — 이미지 크기

### 봐야 할 증거
- `node_modules` 대용량 패키지 (bundlephobia 기준)
- 미사용 import / dead code
- 이미지 포맷 (PNG vs WebP)
- Expo 플러그인 중 미사용 항목
- Docker 이미지 레이어 크기

## Checklist
- [ ] JS 번들 크기 분석 완료
- [ ] 상위 5개 대용량 의존성 식별
- [ ] 미사용 의존성 ≤ 0개
- [ ] 이미지 에셋 WebP 전환 비율 확인
- [ ] Docker 이미지 크기 확인

## Output Template
```markdown
# Build/Bundle Size Report – YYYY-MM-DD

## Baseline & Measurement
| 지표 | 현재 | 목표 | 측정 방법 |
...

## Findings (BS-001~)
...

## Recommendations
...

## Task List / Risk & Rollback
...
```

## Codex Handoff Contract
```yaml
task_id: BS-T001
commit_message: "perf(build): <BS-ID> <desc>"
```

## Stop Conditions
| 상황 | 조치 |
|------|------|
| 번들 분석 도구 실행 불가 | 대안 커맨드 제안 + blocker |
| 대용량 패키지 대안 없음 | 백로그 등록 |
