# Profiling / Benchmark Report – 2026-02-13

## Baseline Metrics

| 지표 | 대상 | 현재값 (추정) | 목표 | 측정 도구 | 커맨드 |
|------|------|-------------|------|----------|--------|
| TTFB (p95) | GET /api/inventory | ~200ms | ≤150ms | httpx + time | `time curl -s $API/api/inventory -H "X-Device-ID: test"` |
| API p95 | POST /api/scans/upload | 5-10s | ≤8s | py-spy / cProfile | `py-spy top --pid $(pgrep uvicorn)` |
| API p95 | GET /api/recipes/recommendations | 3-10s | ≤5s | cProfile | `python -m cProfile -o prof.out -m pytest tests/` |
| 메모리 (RSS) | uvicorn 프로세스 | ~150-300MB | ≤256MB | `ps aux` / docker stats | `docker stats --no-stream prometheus-api` |
| 번들 크기 | JS bundle (production) | 미측정 | ≤5MB | `npx expo export` | `cd prometheus-app && npx expo export --platform ios && du -sh dist/` |
| FPS | 재고 목록 스크롤 | 추정 45-55 | ≥58fps | React DevTools Profiler | 수동: Profiler 녹화 |
| Docker 이미지 | Docker image | ~200MB | ≤180MB | docker images | `docker images prometheus-api --format "{{.Size}}"` |
| 앱 시작 시간 | Expo → 첫 화면 | 미측정 | ≤2s | console.time | 앱 코드에 시간 로그 삽입 |

## Profiling Points

| # | 핫패스 | 파일 | 병목 유형 | 측정 방법 |
|---|--------|------|----------|----------|
| PP-1 | 스캔 업로드 → Gemini 분석 | `scans.py:upload_scan()` → `gemini_service.py` | 외부 API I/O | 타이밍 로그 (before/after) |
| PP-2 | 레시피 추천 (캐시 miss) | `recipes.py:get_recommendations()` → `gemini_service.py` | 외부 API + 캐시 | 캐시 hit/miss 로그 |
| PP-3 | 재고 bulk_upsert | `inventory_service.py:bulk_upsert()` | DB 쿼리 (`SELECT *`) | 쿼리 시간 로깅 |
| PP-4 | 장보기 체크아웃 | `shopping.py:checkout()` → `inventory_service.py` | DB 쿼리 체인 | 트랜잭션 시간 |
| PP-5 | 유통기한 알림 배치 | `admin.py:check_expiry()` | 전체 테이블 스캔 | 배치 처리 시간 |
| PP-6 | 재고 FlatList 렌더 | 탭 화면 `inventory.tsx` | 렌더 성능 | React Profiler |
| PP-7 | 앱 초기 로딩 | `_layout.tsx` → http-client 초기화 | 기기 I/O + 네트워크 | console.time |

## Benchmark Commands

```bash
# 백엔드 API 벤치마크 (hey 도구)
hey -n 100 -c 10 -H "X-Device-ID: bench-device" \
  -H "X-App-Token: $APP_TOKEN" \
  "$API_URL/api/inventory"

# 특정 엔드포인트 프로파일링
py-spy record -o profile.svg --pid $(pgrep -f uvicorn)

# Docker 이미지 크기
docker build -t prometheus-api . && docker images prometheus-api

# JS 번들 크기
cd prometheus-app && npx expo export --platform ios && du -sh dist/bundles/

# uvicorn 메모리 모니터링
docker stats --no-stream prometheus-api
```

## Findings

### PB-001: 성능 측정 인프라 전무
- **근거**: 어떠한 프로파일러, 벤치마크, APM 도구도 설정되어 있지 않음
- **권장 조치**: `hey`(HTTP 벤치), `py-spy`(Python 프로파일러), React DevTools Profiler 활용 기반 확립
- **위험도**: 🔴

### PB-002: 서버 응답 시간 미들웨어 없음
- **파일**: `main.py`
- **근거**: 요청 소요시간을 응답 헤더/로그에 기록하는 미들웨어 없음
- **권장 조치**: `X-Response-Time` 미들웨어 추가
- **위험도**: 🟡

## Task List
| # | 파일 | 변경요지 | 벤치 커맨드 | 테스트 커맨드 | 수용기준 | 예상 영향 | 위험도 |
|---|------|---------|-----------|-------------|---------|----------|--------|
| 1 | `main.py` | 응답 시간 미들웨어 추가 | `hey -n 50 $API/api/inventory` | `pytest tests/ -v` | X-Response-Time 헤더 | 관측성 +100% | 🟡 |
| 2 | `requirements.txt` | py-spy dev 의존성 문서화 | N/A | N/A | 문서화 | 프로파일링 가능 | 🟢 |

## Risk & Rollback
- 미들웨어 추가는 ~1μs 오버헤드, 무시 가능. 환경변수로 비활성화 옵션 제공.
