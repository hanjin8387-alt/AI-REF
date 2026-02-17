# Perf Reliability Report – 2026-02-13

## Perf Budget (초안)

| 지표 | 현재 추정 | 경고 임계 | 상한 | 비고 |
|------|---------|----------|------|------|
| API p95 (inventory) | ~200ms | 300ms | 500ms | DB 쿼리 단순 |
| API p95 (scans) | 5-10s | 10s | 15s | Gemini 의존 |
| API p95 (recipes) | 3-10s | 8s | 12s | 캐시 miss 시 |
| JS bundle (prod) | 미측정 | 6MB | 8MB | 모바일 대역폭 |
| Docker image | ~200MB | 250MB | 300MB | Cloud Run 콜드 스타트 |
| 메모리 (RSS) | ~150-300MB | 384MB | 512MB | Cloud Run 인스턴스 |
| FPS (스크롤) | 45-55 | 50 | 45 | 사용자 체감 |

## Memory Leak Risk

| # | 파일 | 구조 | 위험 | 조치 |
|---|------|------|------|------|
| PRL-001 | `recipe_cache.py` — `_recipe_store: dict` | 디바이스 수 비례 무한 성장 | 🔴 | max_devices=100 + LRU |
| PRL-002 | `http-client.ts` — `cache: Map` | 앱 세션 중 무한 성장 | 🟡 | max_entries=200 + LRU |
| PRL-003 | `offline-cache.ts` — AsyncStorage | 오프라인 데이터 누적 | 🟢 | TTL 기반 정리 |

## Load Test Plan

### 도구 (가정: `hey` 또는 `wrk`)
```bash
# 설치
go install github.com/rakyll/hey@latest
# 또는
# brew install wrk (macOS)
```

### 시나리오

| 시나리오 | 커맨드 | 목표 |
|---------|--------|------|
| 재고 조회 부하 | `hey -n 500 -c 20 -H "X-Device-ID: load-test" $API/api/inventory` | p95 < 500ms |
| 스캔 업로드 동시 | `hey -n 10 -c 5 -m POST -D test.jpg $API/api/scans/upload` | OOM 없음 |
| 레시피 추천 동시 | `hey -n 20 -c 5 $API/api/recipes/recommendations?device_id=test` | 타임아웃 동작 |

### 스모크 벤치 (CI 게이트 후보)
```bash
#!/bin/bash
# perf-smoke.sh : 성능 스모크 테스트
API_URL=${API_URL:-http://localhost:8000}
DEVICE_ID="smoke-test-device"

# 1. 헬스체크 (향후 추가 후)
# curl -sf "$API_URL/health" || exit 1

# 2. 재고 조회 p95 < 500ms
RESULT=$(hey -n 50 -c 5 \
  -H "X-Device-ID: $DEVICE_ID" \
  -H "X-App-Token: $APP_TOKEN" \
  "$API_URL/api/inventory" 2>&1)
P95=$(echo "$RESULT" | grep "95%" | awk '{print $2}')
echo "Inventory p95: ${P95}s"

# 3. 메모리 확인
docker stats --no-stream prometheus-api --format "{{.MemUsage}}"
```

## Findings

### 🔴 Critical

#### PRL-001: RecipeCache 무제한 성장
- **파일**: `recipe_cache.py`
- **유형**: 실제 성능 (메모리)
- **근거**: `_recipe_store` dict에 eviction 없음. 디바이스 증가 시 OOM.
- **권장 조치**: max_devices=100 + oldest-first eviction
- **예상 영향**: 메모리 상한 보장

### 🟡 Warning

#### PRL-002: 클라이언트 캐시 Map 무제한
- **파일**: `http-client.ts`
- **근거**: `cache: Map<string, CacheEntry>` 에 max size 없음
- **권장 조치**: max_entries=200 + TTL eviction

#### PRL-003: 회귀 방지 메커니즘 전무
- **근거**: CI 파이프라인 없음. 성능 스모크 테스트 없음. 매 릴리즈마다 성능 체크 불가.
- **권장 조치**: `perf-smoke.sh` 스크립트 생성, 배포 전 실행 규칙화

#### PRL-004: 성능 예산 미정의
- **근거**: 성능 상한이 어디에도 문서화되지 않음. 악화 감지 불가.
- **권장 조치**: 상기 Perf Budget 초안을 `.ai/` 또는 README에 기록

## Task List
| # | 파일 | 변경요지 | 벤치 커맨드 | 테스트 커맨드 | 수용기준 | 예상 영향 | 위험도 |
|---|------|---------|-----------|-------------|---------|----------|--------|
| 1 | `recipe_cache.py` | max_devices + LRU | `hey -n 50 $API/recipes` | `pytest tests/ -v` | 101번째 디바이스 시 퇴출 | 메모리 보장 | 🔴 |
| 2 | `http-client.ts` | max_entries + TTL eviction | 수동 | `npm test` | 캐시 200 초과 시 정리 | 메모리 보장 | 🟡 |
| 3 | `.ai/scripts/perf-smoke.sh` (신규) | 스모크 벤치 스크립트 | 스크립트 자체 | N/A | 실행 성공 | 회귀 방지 | 🟡 |
| 4 | (문서) | 성능 예산 기록 | N/A | N/A | 문서 존재 | 인식 | 🟢 |

## Risk & Rollback
- PRL-001: LRU 퇴출 시 캐시 miss → Gemini 재호출. 사용자 영향 미미.
- PRL-003: 스모크 스크립트는 정보성, 실패해도 배포 차단하지 않음 (초기에는).
