# Backend Latency Report – 2026-02-13

## Baseline & Measurement
| 엔드포인트 | 추정 p95 | 목표 | 병목 유형 | 측정 방법 |
|-----------|---------|------|----------|----------|
| POST /scans/upload | 5-10s | ≤8s | Gemini I/O | 타이밍 로그 |
| GET /recipes/recommendations | 3-10s | ≤5s | Gemini + 캐시 | 캐시 hit/miss 로그 |
| GET /inventory | ~200ms | ≤150ms | DB | hey 벤치 |
| POST /inventory/bulk | ~500ms | ≤400ms | DB (SELECT *) | hey 벤치 |
| POST /shopping/checkout | ~500ms | ≤400ms | DB 체인 | 타이밍 로그 |
| POST /admin/check-expiry | 1-5s | ≤3s | 풀 스캔 | 타이밍 로그 |

## Findings

### 🔴 Critical

#### BL-001: Gemini API 호출에 타임아웃 없음
- **파일**: `gemini_service.py` — `generate_content_async()` 호출
- **유형**: 실제 성능
- **근거**: 기본 타임아웃(무한)에 의존 → Gemini 장애 시 요청 행
- **영향**: 전체 서비스 중단 가능
- **권장 조치**: `asyncio.wait_for(coro, timeout=30)` 래핑
- **예상 영향**: 장애 시 30초 내 해제, 정상 시 영향 없음

#### BL-002: `inventory_service.bulk_upsert`가 `SELECT *` 전체 로드
- **파일**: `inventory_service.py` L89
- **유형**: 실제 성능
- **근거**: 디바이스 전체 재고를 메모리에 로드 후 병합
- **영향**: 재고 수백 건 이상 시 불필요한 데이터 전송
- **권장 조치**: 입력 아이템 이름으로 IN 절 필터 + 컬럼 지정
- **예상 영향**: 쿼리 크기 -60%, 응답 시간 -100ms

### 🟡 Warning

#### BL-003: `admin.check_expiry` 모든 디바이스 재고 한 번에 조회
- **파일**: `admin.py` L52
- **권장 조치**: 디바이스별 배치 + 커서 기반 페이징
- **예상 영향**: 디바이스 100+ 시 p95 -50%

#### BL-004: `shopping.py`에서 2개 이상 직렬 await 체인
- **파일**: `shopping.py` — checkout 로직
- **근거**: 장보기 체크아웃 시 `fetch_items` → `bulk_upsert` → `update_status` → `notification` 순차 실행
- **권장 조치**: 독립 작업(notification)은 `asyncio.create_task()` 또는 `asyncio.gather()`로 병렬화
- **예상 영향**: 체크아웃 p95 -30%

#### BL-005: 레시피 추천 시 캐시 miss → Gemini 전체 대기
- **파일**: `recipes.py` → `gemini_service.py`
- **근거**: 캐시 miss 시 사용자가 Gemini 응답까지 전체 대기 (3-10초)
- **권장 조치(체감)**: 즉시 최소 응답(스켈레톤) → 비동기 Gemini → SSE/polling으로 결과 전달
- **권장 조치(실제)**: Gemini 요청 최적화 (프롬프트 길이, 모델 선택)
- **예상 영향**: 체감 대기 -50%

#### BL-006: SELECT * 남용 (scans.py, admin.py, recipes.py 등)
- **파일**: 다수
- **권장 조치**: `.select("id,name,quantity,...")`로 컬럼 지정
- **예상 영향**: 페이로드 -30~50%

## Recommendations

### 실제 성능
1. Gemini 타임아웃 30초 적용 (이미지), 45초 (레시피)
2. bulk_upsert IN 절 필터 + 컬럼 지정
3. 독립 작업 병렬화 (notification 등)
4. SELECT * → 컬럼 지정

### 체감속도
1. 레시피 추천: 캐시 miss 시 빈 결과 즉시 + 백그라운드 갱신
2. 스캔 업로드: 서버 접수 즉시 응답 → 처리 완료 후 푸시/폴링

## Task List
| # | 파일 | 변경요지 | 벤치 커맨드 | 테스트 커맨드 | 수용기준 | 예상 영향 | 위험도 |
|---|------|---------|-----------|-------------|---------|----------|--------|
| 1 | `gemini_service.py` | 타임아웃 래핑 | `hey -n 10 $API/scans/upload` | `pytest tests/ -v` | 30초 타임아웃 | 장애 방지 | 🔴 |
| 2 | `inventory_service.py` | IN절 + 컬럼 지정 | `hey -n 50 $API/inventory/bulk` | `pytest tests/ -v` | SELECT * 0건 | p95 -100ms | 🔴 |
| 3 | `admin.py` | 배치 페이징 | 타이밍 로그 | `pytest tests/ -v` | 디바이스별 처리 | p95 -50% | 🟡 |
| 4 | `shopping.py` | 알림 병렬화 | `hey -n 20 $API/shopping/checkout` | `pytest tests/ -v` | 직렬 await -1 | p95 -30% | 🟡 |
| 5 | 백엔드 전반 | SELECT * 제거 | `hey -n 50 $API/inventory` | `pytest tests/ -v` | 컬럼 지정 | 페이로드 -30% | 🟡 |

## Risk & Rollback
- BL-001: 타임아웃 너무 짧으면 정상 요청 실패 → 환경변수로 설정
- BL-002: IN 절 + 컬럼 지정은 동일 결과 반환, 안전
- BL-004: `create_task`의 에러 핸들링 필수 (fire-and-forget에도 로깅)
