# Build / Bundle Size Report – 2026-02-13

## Baseline & Measurement
| 지표 | 현재 (추정) | 목표 | 측정 커맨드 |
|------|-----------|------|-----------|
| JS bundle (iOS) | 미측정 | ≤5MB | `npx expo export --platform ios && du -sh dist/bundles/` |
| Docker image | ~200MB | ≤180MB | `docker images prometheus-api --format "{{.Size}}"` |
| node_modules | 미측정 | 기록용 | `du -sh prometheus-app/node_modules/` |
| requirements.txt 패키지 수 | ~15 | 기록용 | `wc -l requirements.txt` |

## Findings

### 🟡 Warning

#### BS-001: Expo 빌드 최적화 설정 미확인
- **파일**: `prometheus-app/app.json`, `babel.config.js`
- **유형**: 실제 성능
- **근거**: `babel.config.js`에 production 전용 플러그인(예: `transform-remove-console`) 미설정
- **권장 조치**: production 빌드 시 콘솔 로그 제거 플러그인 추가
- **예상 영향**: 번들 -5~10%

#### BS-002: Docker 멀티스테이지 빌드 미적용
- **파일**: `Dockerfile`
- **유형**: 실제 성능
- **근거**: single-stage 빌드. `python:3.12-slim` 양호하나 pip 캐시/빌드 도구 잔존
- **권장 조치**: multi-stage (builder → runner) 분리
- **예상 영향**: 이미지 -20~30MB

#### BS-003: 미사용 의존성 가능성
- **파일**: `package.json`
- **유형**: 번들 크기
- **근거**: expo 생태계에서 자동 설치되는 패키지 중 실제 미사용 가능. 정적 분석 필요.
- **권장 조치**: `npx depcheck` 실행 → 미사용 패키지 제거
- **예상 영향**: 번들 -?% (분석 필요)

### 🟢 Info

#### BS-004: 이미지 에셋 포맷 확인 필요
- `assets/` 디렉터리의 PNG → WebP 전환 가능 여부 확인
- Expo에서 WebP 지원 (SDK 52+)

#### BS-005: `requirements.txt` 에서 dev 의존성 미분리
- 프로덕션 이미지에 dev 도구(pytest, httpx 등) 포함 가능. `requirements-dev.txt` 분리 권장.

## Task List
| # | 파일 | 변경요지 | 벤치 커맨드 | 테스트 커맨드 | 수용기준 | 예상 영향 | 위험도 |
|---|------|---------|-----------|-------------|---------|----------|--------|
| 1 | `babel.config.js` | console 제거 플러그인 | `npx expo export` 크기 비교 | `npm test` | production 콘솔 0 | 번들 -5% | 🟡 |
| 2 | `Dockerfile` | multi-stage 빌드 | `docker build && docker images` | `docker run whoami` | 이미지 크기 감소 | -20MB | 🟡 |
| 3 | `package.json` | 미사용 의존성 제거 | `npx depcheck` | `npm test` | 미사용 0개 | 번들 감소 | 🟡 |
| 4 | `requirements.txt` | dev 의존성 분리 | `docker images` 크기 | N/A | 프로덕션 slim | -5MB | 🟢 |

## Risk & Rollback
- BS-001: 프로덕션에서 디버깅 어려움 → __DEV__ 조건부로 유지
- BS-002: multi-stage 빌드 실패 시 single-stage로 복원
- BS-003: 의존성 제거 시 런타임 에러 → 철저한 테스트 필수
