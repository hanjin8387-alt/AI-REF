# Network / Cache / Data Report – 2026-02-13

## Baseline & Measurement
| 지표 | 현재 (추정) | 목표 | 측정 방법 |
|------|-----------|------|----------|
| 평균 응답 크기 (inventory) | ~5-20KB | ≤5KB | `curl -s -o /dev/null -w '%{size_download}'` |
| 캐시 히트율 (클라이언트) | 미측정 | ≥50% | 캐시 hit/miss 로그 |
| 레시피 캐시 히트율 (서버) | 미측정 | ≥70% | `recipe_cache` 로그 |
| 중복 요청 빈도 | 미측정 | 0 | 네트워크 인터셉터 |
| gzip 압축 | ❌ 미적용 | 적용 | 응답 헤더 확인 |

## Findings

### 🔴 Critical

#### NC-001: gzip/brotli 응답 압축 미적용
- **파일**: `prometheus-api/app/main.py`
- **유형**: 실제 성능
- **근거**: FastAPI/Starlette에 `GZipMiddleware` 미등록. 모든 JSON 응답 비압축 전송.
- **영향**: 대량 재고/장보기 응답 크기 3-5배 증가
- **권장 조치**: `app.add_middleware(GZipMiddleware, minimum_size=500)`
- **예상 영향**: 페이로드 -60~70%

### 🟡 Warning

#### NC-002: 클라이언트 인메모리 캐시에 중복 요청 방지(dedup) 없음
- **파일**: `http-client.ts` L176-272
- **유형**: 실제 성능
- **근거**: 동일 엔드포인트 동시 요청 시 각각 네트워크 호출. `inflight` Map 등으로 dedup 가능.
- **권장 조치**: `inflight` promise Map으로 동일 요청 병합
- **예상 영향**: 동시 요청 시 네트워크 -50%

#### NC-003: HTTP 캐시 헤더(Cache-Control/ETag) 미설정
- **파일**: `main.py` 및 라우터 전반
- **유형**: 실제 성능
- **근거**: GET 응답에 `Cache-Control`, `ETag` 헤더 미설정. 브라우저/프록시 캐시 활용 불가.
- **권장 조치**: 정적 데이터(inventory 목록)에 `Cache-Control: max-age=30` 추가
- **예상 영향**: 반복 요청 시 네트워크 -100%

#### NC-004: 프리페치 기회 미활용
- **파일**: 탭 화면 전반
- **유형**: 체감속도
- **근거**: 탭 전환 시 데이터를 탭 활성화 후에야 fetch. 인접 탭 데이터 프리페치 없음.
- **권장 조치**: `useFocusEffect` 또는 `onTabPress`에서 인접 탭 데이터 프리로드
- **예상 영향**: 탭 전환 체감 -500ms

#### NC-005: 오프라인 캐시 갱신 전략 부재
- **파일**: `offline-cache.ts`
- **유형**: 실제 성능
- **근거**: 온라인 복귀 시 전체 데이터 재요청. 변경분만 동기화하는 delta sync 없음.
- **권장 조치**: `updated_at` 기반 incremental sync (향후)

### 🟢 Info

#### NC-006: `cacheTtlMs` 값이 호출 위치마다 다름
- 일부는 30초, 일부는 5분, 일부 미설정. 정책 문서화 필요.

## Recommendations

### 실제 성능
1. GZipMiddleware 추가 (즉시 효과, 1줄)
2. inflight dedup Map 추가
3. GET 엔드포인트에 Cache-Control 헤더

### 체감속도
1. 인접 탭 프리페치
2. 오프라인 → 온라인 시 delta sync

## Task List
| # | 파일 | 변경요지 | 벤치 커맨드 | 테스트 커맨드 | 수용기준 | 예상 영향 | 위험도 |
|---|------|---------|-----------|-------------|---------|----------|--------|
| 1 | `main.py` | GZipMiddleware 추가 | `curl -H "Accept-Encoding: gzip"` | `pytest tests/ -v` | gzip 응답 확인 | 페이로드 -60% | 🔴 |
| 2 | `http-client.ts` | inflight dedup Map | 수동 테스트 | `npm test` | 동시 요청 1회 | 네트워크 -50% | 🟡 |
| 3 | 라우터 | Cache-Control 헤더 | `curl -I` | `pytest tests/ -v` | 헤더 존재 | 반복 요청 0 | 🟡 |
| 4 | 탭 화면 | 인접 탭 프리페치 | 수동 체감 | `npm test` | 탭 전환 시 즉시 | 체감 -500ms | 🟡 |

## Risk & Rollback
- NC-001: GZipMiddleware는 minimum_size=500, 작은 응답은 미압축. CPU 오버헤드 ~2%.
- NC-002: dedup 잘못 구현 시 응답 누락 → 타임아웃으로 폴백.
- NC-003: Cache-Control 과도 시 stale 데이터 → 짧은 TTL(30초) 시작.
