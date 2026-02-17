# PROMETHEUS 리뷰 근거 문서 (`review-evidence.md`)

- 기준일: 2026-02-09
- 목적: `review.md`의 모든 핵심 주장에 대해 코드 근거를 남기는 기술 부록
- 범위: 문서 개편(코드 수정 없음)

## 1. 읽는 방법
- `[확정 사실]`: 코드/설정/파일에서 직접 확인된 내용
- `[추정/해석]`: 사실을 바탕으로 한 위험 해석 또는 운영 가정
- `[완화요소]`: 위험을 낮추는 기존 방어 요소 또는 반례

## 2. 정정 로그 (기존 문서 대비)

| ID | 기존 표현 | 정정 표현 | 근거 |
|---|---|---|---|
| `CORR-01` | "설정 없이 서버가 떠서 보안 구멍" | 기본값은 빈 문자열이지만, 서버는 기동 시 필수 env 누락이면 종료 | `prometheus-api/app/main.py:18`, `prometheus-api/app/main.py:27`, `prometheus-api/app/core/config.py:12` |
| `CORR-02` | N+1 위치가 `inventory.py` | 실제 N+1 핵심 경로는 조리 완료 루프(`recipes.py`) | `prometheus-api/app/api/recipes.py:274` |
| `CORR-03` | 날짜 계산 중복 예시가 `inventory.py` | 중복은 프론트 3곳 | `prometheus-app/app/(tabs)/index.tsx:67`, `prometheus-app/app/(tabs)/inventory.tsx:151`, `prometheus-app/components/InventoryItemCard.tsx:18` |
| `CORR-04` | 보안 평점이 중간 수준 | 토큰 노출 + 헤더 신뢰 모델로 상향 재평가 필요 | `prometheus-app/app.json:61`, `prometheus-api/app/core/security.py:8`, `prometheus-api/app/core/security.py:27` |

## 3. 이슈별 근거

## `SEC-01` 공유 토큰 + `device_id` 신뢰 인증 구조 (S0)
- 상태: Open
- [확정 사실]
  - 토큰 검증은 `X-App-Token` 값 일치 여부로 수행됩니다. (`prometheus-api/app/core/security.py:8`)
  - 사용자 식별은 `X-Device-ID` 헤더 문자열 검증(길이/빈값) 후 그대로 사용됩니다. (`prometheus-api/app/core/security.py:27`)
  - 인벤토리 조회는 전달된 `device_id`로 직접 필터링합니다. (`prometheus-api/app/api/inventory.py:45`)
- [추정/해석]
  - 토큰이 외부에 노출되면 `device_id` 위조를 통해 타 데이터 접근 시도가 가능해질 수 있습니다.
- [완화요소]
  - 토큰 미설정 시 서버는 시작 시점에 실패하도록 방어합니다. (`prometheus-api/app/main.py:18`, `prometheus-api/app/main.py:27`)
- [권장 조치]
  - 단기: 민감 엔드포인트에서 추가 서버 검증 계층 도입
  - 장기: 사용자/기기 바인딩 인증 체계로 전환
- [검증 기준]
  - 임의 `X-Device-ID` 헤더로 타 데이터 접근 시 401/403이 반환되어야 함

## `SEC-02` 클라이언트 토큰 번들 포함 (S1)
- 상태: Open
- [확정 사실]
  - 앱 설정에 토큰 값이 존재합니다. (`prometheus-app/app.json:61`)
  - 프론트 HTTP 클라이언트가 해당 값을 `X-App-Token` 헤더에 자동 주입합니다. (`prometheus-app/services/http-client.ts:5`, `prometheus-app/services/http-client.ts:194`)
- [추정/해석]
  - 설정 유출/분석 시 토큰 재사용 공격 표면이 커집니다.
- [완화요소]
  - 토큰이 비어 있으면 요청 자체를 막는 로직은 존재합니다. (`prometheus-app/services/http-client.ts:89`)
- [권장 조치]
  - 하드코딩 토큰 제거 + 환경별 안전 주입 + 토큰 회전 정책
- [검증 기준]
  - 저장소 및 빌드 산출물에서 고정 토큰 문자열 탐지 0건

## `DATA-01` 조리 완료 경로 원자성 부재 (S1)
- 상태: Open
- [확정 사실]
  - 재료 루프에서 재고 UPDATE/DELETE를 개별 실행합니다. (`prometheus-api/app/api/recipes.py:274`)
  - 이후 별도 호출로 요리 이력을 INSERT합니다. (`prometheus-api/app/api/recipes.py:327`)
- [추정/해석]
  - 중간 실패 시 "재고 반영은 됐는데 이력 없음" 같은 불일치 가능성이 있습니다.
- [완화요소]
  - 현재 코드는 성공 경로 중심으로 동작하며, 실패 롤백 로직은 명시되어 있지 않습니다.
- [권장 조치]
  - 트랜잭션 또는 동등한 원자성 보장 설계 적용
- [검증 기준]
  - 강제 실패 주입 테스트에서 부분 반영 상태가 0건

## `SEC-03` 내부 예외 메시지 외부 노출 (S1)
- 상태: Open
- [확정 사실]
  - 스캔 실패 시 `detail`에 내부 예외 문자열이 포함됩니다. (`prometheus-api/app/api/scans.py:87`)
  - 인벤토리 수정 실패 시 예외를 그대로 노출합니다. (`prometheus-api/app/api/inventory.py:238`)
  - 디바이스 등록 실패 시 예외 문자열을 노출합니다. (`prometheus-api/app/api/auth.py:45`)
- [추정/해석]
  - 내부 구조/연동 상태 노출로 공격자에게 단서를 줄 수 있습니다.
- [완화요소]
  - 일부 경로는 사용자 친화 메시지를 이미 사용합니다.
- [권장 조치]
  - 외부 응답은 표준 코드/메시지로 통일, 상세는 내부 로그로만 유지
- [검증 기준]
  - 실패 응답 본문에서 원시 예외 텍스트 비노출

## `OPS-01` Rate Limiting 부재 (S1)
- 상태: Open
- [확정 사실]
  - 의존성 목록에 rate limiting 라이브러리가 없습니다. (`prometheus-api/requirements.txt:1`)
  - 루트 포함 API 코드에서 limiter 데코레이터 사용 흔적이 없습니다. (`prometheus-api/app/main.py:69`, 코드 검색 결과 기준)
- [추정/해석]
  - 과도 요청 시 비용/지연 리스크가 큽니다.
- [완화요소]
  - 업스트림 인프라 레벨 제한이 별도로 있을 가능성은 있으나, 저장소 기준 명시 없음
- [권장 조치]
  - 엔드포인트별 정책 도입(스캔/추천/인증 분리)
- [검증 기준]
  - 초과 호출 시 429 발생 및 정책 문서화

## `SEC-04` 운영 CORS 과개방 위험 (S2)
- 상태: Open
- [확정 사실]
  - 기본 `cors_origins` 값이 `*`입니다. (`prometheus-api/app/core/config.py:13`)
  - 앱은 이 값을 그대로 `allow_origins`에 연결합니다. (`prometheus-api/app/main.py:56`)
- [추정/해석]
  - 운영에서 광범위 Origin 허용이 보안 경계를 약하게 만들 수 있습니다.
- [완화요소]
  - 환경변수로 별도 설정이 가능하며, 반드시 `*`만 쓰는 구조는 아닙니다. (`prometheus-api/app/core/config.py:31`)
- [권장 조치]
  - 환경별 명시 도메인 화이트리스트 적용
- [검증 기준]
  - 운영에서 미허용 Origin 요청 차단

## `REL-01` 비동기 오류 무시 패턴 (`void`) (S2)
- 상태: Open
- [확정 사실]
  - 홈 화면에서 `void refreshAll(...)` 패턴이 반복됩니다. (`prometheus-app/app/(tabs)/index.tsx:98`)
  - 알림 화면도 `void loadNotifications(...)` 패턴을 사용합니다. (`prometheus-app/app/(tabs)/alerts.tsx:62`)
  - 히스토리 화면도 `void loadHistory(...)` 패턴을 사용합니다. (`prometheus-app/app/(tabs)/two.tsx:48`)
- [추정/해석]
  - 네트워크 실패 시 사용자가 오류 원인을 인지하지 못할 가능성이 있습니다.
- [완화요소]
  - 일부 함수 내부에서 실패 시 상태값을 조정하는 로직은 존재합니다.
- [권장 조치]
  - 공통 async error handler 도입 + 사용자 알림/재시도 UX 통일
- [검증 기준]
  - 강제 실패 시 화면별 일관된 에러 안내 표시

## `PERF-01` 조리 완료 경로 N+1 (S2)
- 상태: Open
- [확정 사실]
  - 조리 완료 루프 안에서 재료마다 inventory 조회를 수행합니다. (`prometheus-api/app/api/recipes.py:274`)
- [추정/해석]
  - 재료 수 증가에 따라 DB 호출 수가 선형으로 증가합니다.
- [완화요소]
  - 소규모 데이터에서는 체감이 작을 수 있습니다.
- [권장 조치]
  - 일괄 조회 후 메모리 매칭 방식으로 전환
- [검증 기준]
  - 재료 수 증가 대비 호출 수 상한 유지

## `PERF-02` 날짜 계산 중복 (S3)
- 상태: Open
- [확정 사실]
  - 동일한 `Math.ceil((expiry - now)/day)` 로직이 3개 파일에 중복됩니다.
  - 근거: `prometheus-app/app/(tabs)/index.tsx:67`, `prometheus-app/app/(tabs)/inventory.tsx:151`, `prometheus-app/components/InventoryItemCard.tsx:18`
- [추정/해석]
  - 유지보수 시 누락 위험과 일관성 깨짐 가능성이 있습니다.
- [완화요소]
  - 현재 로직 자체는 간단하여 즉시 장애 확률은 낮습니다.
- [권장 조치]
  - 공통 유틸 함수로 통합
- [검증 기준]
  - 중복 계산 코드 제거 및 공통 유틸 단일화

## `TEST-01` 테스트 부족 (S2)
- 상태: Open
- [확정 사실]
  - 프론트 자체 테스트는 스냅샷 1건이 확인됩니다. (`prometheus-app/components/__tests__/StyledText-test.js:1`)
  - 저장소 기준 백엔드 테스트 디렉터리/테스트 파일이 확인되지 않습니다. (repo scan, 2026-02-09)
- [추정/해석]
  - 회귀 버그 탐지력이 낮아 배포 리스크가 큽니다.
- [완화요소]
  - 타입체크(`npx tsc --noEmit`)는 통과합니다.
- [권장 조치]
  - 인증/조리/재고 핵심 시나리오 우선 자동화
- [검증 기준]
  - 최소 10개 핵심 시나리오 CI 자동 검증

## `OPS-02` 구조화 로깅 미도입 (S3)
- 상태: Open
- [확정 사실]
  - 앱 lifecycle 로그가 `print`로 기록됩니다. (`prometheus-api/app/main.py:29`)
- [추정/해석]
  - 장애 분석 및 집계 지표 연동 효율이 낮아질 수 있습니다.
- [완화요소]
  - 최소한의 시작/종료 출력 자체는 존재합니다.
- [권장 조치]
  - 표준 logger + 공통 필드(request id 등)로 전환
- [검증 기준]
  - 운영 로그 검색/집계 가능 포맷 확보

## `ARCH-01` 대형 화면 컴포넌트 집중 (S3)
- 상태: Open
- [확정 사실]
  - 주요 화면 파일 크기가 큽니다. (`prometheus-app/app/(tabs)/index.tsx`, `prometheus-app/app/(tabs)/inventory.tsx`, `prometheus-app/app/(tabs)/scan.tsx`)
  - 측정값(2026-02-09): 356줄, 360줄, 329줄
- [추정/해석]
  - 화면별 책임이 커져 기능 추가 시 충돌 확률이 올라갑니다.
- [완화요소]
  - 이미 일부 화면은 스타일 분리 등 구조 개선 흔적이 있습니다.
- [권장 조치]
  - 훅/프리젠테이션 컴포넌트로 단계적 분리
- [검증 기준]
  - 화면 파일 책임 단순화 + 평균 파일 길이 감소

## `CFG-01` 하드코딩 운영 값 (S3)
- 상태: Open
- [확정 사실]
  - API URL 기본값이 코드에 직접 포함됩니다. (`prometheus-app/services/api.ts:32`)
  - 요청 타임아웃이 상수로 고정되어 있습니다. (`prometheus-app/services/http-client.ts:6`)
- [추정/해석]
  - 환경 전환/긴급 변경 시 운영 비용이 증가합니다.
- [완화요소]
  - `app.json`의 `extra`를 이미 사용하고 있어 확장 기반은 존재합니다. (`prometheus-app/app.json:60`)
- [권장 조치]
  - 설정 모듈 단일화 + 환경별 주입 원칙 문서화
- [검증 기준]
  - 운영 값 변경 시 코드 수정 없이 설정만으로 반영

## `INTF-01` 문서 개편 단계의 인터페이스 변경 범위
- 상태: Closed (정책 확정)
- [확정 사실]
  - 이번 변경은 문서(`review.md`, `review-evidence.md`) 중심이며 코드 인터페이스 변경은 수행하지 않았습니다.
- [추정/해석]
  - 구현 단계에서 인증/에러응답/트랜잭션 계약 변경이 후속으로 필요합니다.
- [완화요소]
  - 변경 범위를 문서에 먼저 고정해 구현 리스크를 줄일 수 있습니다.
- [권장 조치]
  - 후속 스프린트에서 별도 RFC로 API 변경안을 승인 후 착수
- [검증 기준]
  - 이번 커밋에 코드 동작 변경이 없어야 함

## 4. 점수 산정 근거
- 가중치: 보안 30, 데이터 무결성 20, 안정성/오류처리 15, 테스트/검증 15, 성능 10, 유지보수성 10
- 상한 규칙: `S0` 1개 이상 -> 총점 상한 59, `S1` 3개 이상 -> 총점 상한 69
- 현재 판정: `S0` 1개 + `S1` 4개 -> 총점 상한 59 적용
- 항목 점수: 보안 8, 데이터 무결성 11, 안정성/오류처리 10, 테스트/검증 4, 성능 6, 유지보수성 8
- 합계: 47/100, 상한 적용 후 47/59

## 5. 실행 검증 체크리스트
- 모든 핵심 주장에 근거 파일/라인이 연결되어 있는가
- 확정 사실과 해석 문장이 분리되어 있는가
- 긴급 이슈(`SEC-01`, `SEC-02`, `SEC-03`, `OPS-01`, `DATA-01`)에 담당/기간/DoD가 있는가
- 오표기(잘못된 파일/라인)가 없는가
- 문서 인코딩이 UTF-8로 저장되어 IDE/터미널에서 깨지지 않는가
