# Agent 01: Profiling / Benchmark Skill

## Mission
베이스라인 성능 지표를 정의하고, 측정 도구/커맨드를 확정하며, 프로파일링 포인트를 제안한다.

## Scope
- 핵심 성능 지표(KPI) 정의: TTI, TTFB, FPS, p95/p99 API 레이턴시, 메모리, 번들 크기
- 측정 도구 선정 및 설치/실행 커맨드 확정
- 프로파일링 대상(핫패스) 식별
- 벤치마크 스크립트/커맨드 설계

## Non-Goals
- 실제 최적화 구현
- UI/UX 개선
- 기능 변경

## Inputs (우선순위순)
1. `prometheus-api/app/main.py` — 앱 설정, 미들웨어 체인
2. `prometheus-api/app/api/*.py` — 엔드포인트별 핫패스
3. `prometheus-api/app/services/*.py` — 서비스 레이어 (Gemini, 캐시)
4. `prometheus-app/app/(tabs)/_layout.tsx` — 앱 시작점
5. `prometheus-app/services/http-client.ts` — 네트워크 레이어
6. `prometheus-app/package.json` — 빌드/실행 커맨드
7. `prometheus-api/requirements.txt` — 백엔드 의존성
8. `prometheus-api/Dockerfile` — 컨테이너 설정

### 봐야 할 증거
- 타이밍 로그 존재 여부
- 기존 벤치마크/성능 테스트 유무
- CI에 성능 게이트 유무

## Checklist
- [ ] 핵심 지표 ≥ 8개 정의 (프론트+백엔드)
- [ ] 각 지표에 측정 도구+커맨드 명시
- [ ] 프로파일링 포인트 ≥ 5개 식별
- [ ] 벤치마크 실행 커맨드 ≥ 3개

## Output Template

```markdown
# Profiling/Benchmark Report – YYYY-MM-DD

## Baseline Metrics
| 지표 | 대상 | 현재값 | 목표 | 측정 도구 | 커맨드 |
|------|------|--------|------|----------|--------|

## Profiling Points
| # | 핫패스 | 파일 | 병목 유형 | 측정 방법 |
|---|--------|------|----------|----------|

## Benchmark Commands
...

## Findings / Recommendations / Task List / Risk & Rollback
(표준 섹션)
```

## Codex Handoff Contract
```yaml
task_id: PB-T001
files: [...]
test_command: "..."
bench_command: "..."
acceptance_criteria: ["지표 X가 Y 이하"]
rollback: "환경변수/설정으로 비활성화"
commit_message: "perf(<scope>): <PB-ID> <desc>"
```

## Stop Conditions
| 상황 | 조치 |
|------|------|
| 측정 도구 설치 불가 | 대안 제시 + blocker |
| 프로파일러 실행 권한 부족 | 로그 기반 측정으로 대체 |
