# Performance Optimization Master Plan – 2026-02-13

> 8개 성능 에이전트 리포트를 통합한 Codex 실행계획.
> **원칙**: 측정 없이 최적화 금지. 1 task = 1 commit. 성능 목적 외 변경 금지.

---

## 1. 통합 요약

| 에이전트 | 🔴 | 🟡 | 🟢 | 합계 |
|---------|-----|-----|-----|------|
| 01 Profiling/Benchmark | 1 | 1 | 0 | 2 |
| 02 Frontend Rendering | 1 | 4 | 1 | 6 |
| 03 Backend Latency | 2 | 4 | 0 | 6 |
| 04 Network/Cache/Data | 1 | 4 | 1 | 6 |
| 05 Build/Bundle Size | 0 | 3 | 2 | 5 |
| 06 Perceived Speed/UX | 1 | 4 | 1 | 6 |
| 07 Perf Reliability | 1 | 3 | 0 | 4 |
| 08 Observability/Metrics | 1 | 3 | 1 | 5 |
| **합계** | **8** | **26** | **6** | **40** |

---

## 2. 성능 예산 (Perf Budget)

| 지표 | 현재 추정 | 경고 | 상한 | 비고 |
|------|---------|------|------|------|
| API p95 (재고) | ~200ms | 300ms | 500ms | |
| API p95 (스캔) | 5-10s | 10s | 15s | Gemini 의존 |
| API p95 (레시피) | 3-10s | 8s | 12s | 캐시 miss |
| JS 번들 (prod) | 미측정 | 6MB | 8MB | |
| Docker 이미지 | ~200MB | 250MB | 300MB | |
| 메모리 (RSS) | 150-300MB | 384MB | 512MB | |
| FPS (스크롤) | 45-55 | 50 | 45 | |
| 응답 payload (gzip) | 비압축 | - | - | gzip 적용 필수 |

---

## 3. 우선순위 분류

### P0 — 즉시 해결 (관측 기반 + 안정성)

| # | 원본 ID | 제목 | 유형 | 노력 | 근거 |
|---|---------|------|------|------|------|
| 1 | OM-001 | 응답 시간 미들웨어 (ProcessTimeMiddleware) | 관측 | S | **측정 기반 확립** — 이후 모든 최적화의 전제 |
| 2 | PB-002 | X-Response-Time 헤더 | 관측 | S | OM-001과 동시 (동일 미들웨어) |
| 3 | BL-001 | Gemini API 타임아웃 | 실제 | S | 장애 시 전체 서비스 행 |
| 4 | PRL-001 | RecipeCache 크기 제한 (LRU) | 실제 | S | 메모리 무한 성장 → OOM |
| 5 | NC-001 | GZipMiddleware 추가 | 실제 | S | 1줄, 페이로드 -60% |
| 6 | BL-002 | bulk_upsert SELECT * → IN절 + 컬럼 | 실제 | S | 핫패스 쿼리 최적화 |
| 7 | FR-001 | FlatList 최적화 props | 실제 | S | FPS +15-20% |
| 8 | PS-001/002 | SkeletonCard 생성 + 탭 화면 적용 | 체감 | M | 체감 대기 -40% |

### P1 — 1-2주 내

| # | 원본 ID | 제목 | 유형 | 노력 |
|---|---------|------|------|------|
| 9 | FR-002 | 인라인 함수 → useCallback | 실제 | M |
| 10 | FR-003/004 | InventoryItemCard/RecipeCardStack React.memo | 실제 | S |
| 11 | BL-004 | shopping checkout 병렬화 | 실제 | S |
| 12 | BL-006 | SELECT * 전면 제거 | 실제 | M |
| 13 | NC-002 | inflight dedup Map | 실제 | S |
| 14 | NC-003 | Cache-Control 헤더 추가 | 실제 | S |
| 15 | NC-004 | 인접 탭 프리페치 | 체감 | M |
| 16 | PS-002 | 낙관적 UI (재고 삭제/장보기) | 체감 | M |
| 17 | PS-003 | 레시피 추천 진행 단계 메시지 | 체감 | S |
| 18 | PS-004 | 스캔 업로드 진행률 바 | 체감 | S |
| 19 | OM-002 | Gemini duration 로깅 | 관측 | S |
| 20 | OM-003/005 | 캐시 hit/miss + 클라이언트 perf 유틸 | 관측 | M |
| 21 | PRL-002 | 클라이언트 캐시 Map 크기 제한 | 실제 | S |
| 22 | PRL-003 | 스모크 벤치 스크립트 작성 | 가드레일 | S |
| 23 | BS-001 | babel console 제거 플러그인 | 번들 | S |

### P2 — 백로그

| # | 원본 ID | 제목 | 노력 |
|---|---------|------|------|
| 24 | BL-003 | admin 배치 페이징 | M |
| 25 | BL-005 | 레시피 추천 비동기 SSE/polling | L |
| 26 | BS-002 | Docker multi-stage | M |
| 27 | BS-003 | 미사용 의존성 제거 | M |
| 28 | BS-004 | 이미지 WebP 전환 | S |
| 29 | BS-005 | requirements dev 분리 | S |
| 30 | NC-005 | 오프라인 delta sync | L |
| 31 | FR-005 | JSON.parse 대량 데이터 (Web Worker) | M |
| 32 | FR-006 | 이미지 placeholder + fadein | S |
| 33 | PS-005 | 빈 상태 CTA | S |
| 34 | PS-006 | 화면 전환 트랜지션 | S |
| 35 | OM-004 | 릴리즈 성능 비교 메커니즘 | M |
| 36 | PRL-003 | AsyncStorage TTL 정리 | S |
| 37 | PRL-004 | 성능 예산 문서화 | S |

---

## 4. Implementation Plan (P0 + P1 커밋 분해)

### Phase A: P0 관측 기반 + 안정성 (8 커밋)

---

#### Commit A-1: ProcessTimeMiddleware + X-Response-Time
| 항목 | 내용 |
|------|------|
| 변경 파일 | `prometheus-api/app/main.py` |
| 요지 | 미들웨어: `time.perf_counter()` → `X-Process-Time` 헤더 + `logger.info("perf.request", ...)` |
| 벤치 | `hey -n 50 -c 5 $API/api/inventory` → p95 확인 |
| 테스트 | `pytest tests/ -v` |
| 수용기준 | 응답 헤더에 `X-Process-Time` 존재 |
| 커밋 | `perf(api): OM-001 add process-time middleware` |

---

#### Commit A-2: Gemini API 타임아웃
| 항목 | 내용 |
|------|------|
| 변경 파일 | `prometheus-api/app/services/gemini_service.py` |
| 요지 | `asyncio.wait_for(coro, timeout=30)` 래핑 |
| 벤치 | `hey -n 5 $API/api/scans/upload` (타임아웃 동작 확인) |
| 테스트 | `pytest tests/test_services/test_gemini_service.py -v` |
| 수용기준 | 30초 초과 시 적절한 에러 |
| 커밋 | `perf(api): BL-001 add timeout to gemini API calls` |

---

#### Commit A-3: RecipeCache LRU 크기 제한
| 항목 | 내용 |
|------|------|
| 변경 파일 | `prometheus-api/app/services/recipe_cache.py` |
| 요지 | `max_devices=100` + oldest-first eviction |
| 벤치 | `docker stats --no-stream` 메모리 확인 |
| 테스트 | `pytest tests/test_services/test_recipe_cache.py -v` |
| 수용기준 | 101번째 디바이스 시 가장 오래된 항목 퇴출 |
| 커밋 | `perf(api): PRL-001 add max size to recipe cache` |

---

#### Commit A-4: GZipMiddleware
| 항목 | 내용 |
|------|------|
| 변경 파일 | `prometheus-api/app/main.py` |
| 요지 | `app.add_middleware(GZipMiddleware, minimum_size=500)` |
| 벤치 | `curl -sH "Accept-Encoding: gzip" $API/api/inventory -o /dev/null -w '%{size_download}'` |
| 테스트 | `pytest tests/ -v` |
| 수용기준 | gzip 응답, 크기 -60% |
| 커밋 | `perf(api): NC-001 add gzip response compression` |

---

#### Commit A-5: bulk_upsert 쿼리 최적화
| 항목 | 내용 |
|------|------|
| 변경 파일 | `prometheus-api/app/services/inventory_service.py` |
| 요지 | SELECT * → IN 절 필터 + 컬럼 지정 |
| 벤치 | `hey -n 50 -m POST $API/api/inventory/bulk` |
| 테스트 | `pytest tests/test_services/test_inventory_service.py -v` |
| 수용기준 | SELECT * 0건, p95 -100ms |
| 커밋 | `perf(api): BL-002 optimize bulk upsert query` |

---

#### Commit A-6: FlatList 최적화 props
| 항목 | 내용 |
|------|------|
| 변경 파일 | 탭 화면 (`inventory.tsx` 등) |
| 요지 | `getItemLayout`, `windowSize={5}`, `maxToRenderPerBatch={10}` |
| 벤치 | React DevTools Profiler 녹화 |
| 테스트 | `npm test` |
| 수용기준 | FlatList에 getItemLayout 존재 |
| 커밋 | `perf(app): FR-001 optimize FlatList rendering` |

---

#### Commit A-7: SkeletonCard 컴포넌트 생성
| 항목 | 내용 |
|------|------|
| 변경 파일(신규) | `prometheus-app/components/SkeletonCard.tsx` |
| 요지 | GlassCard 기반 shimmer 애니메이션 스켈레톤 |
| 벤치 | 수동 체감 |
| 테스트 | `npm test` |
| 수용기준 | shimmer 동작 확인 |
| 커밋 | `perf(ux): PS-001 create SkeletonCard component` |

---

#### Commit A-8: SkeletonCard 탭 화면 적용
| 항목 | 내용 |
|------|------|
| 변경 파일 | 탭 화면 3개 (inventory, recipes, shopping) |
| 요지 | `isLoading ? <SkeletonCard count={5} /> : <FlatList .../>` |
| 벤치 | 수동 체감 |
| 테스트 | `npm test` |
| 수용기준 | 로딩 시 스켈레톤 표시, 빈 화면 0 |
| 커밋 | `perf(ux): PS-001 apply skeleton to tab screens` |

---

### Phase B: P1 품질·체감·관측 (15 커밋)

---

#### Commit B-1: React.memo 리스트 아이템
```
파일: InventoryItemCard.tsx, RecipeCardStack.tsx
요지: React.memo() 래핑
벤치: Profiler 녹화
커밋: perf(app): FR-003 wrap list items with React.memo
```

#### Commit B-2: 인라인 함수 → useCallback
```
파일: 탭 화면 전반
커밋: perf(app): FR-002 replace inline handlers with useCallback
```

#### Commit B-3: shopping checkout 병렬화
```
파일: shopping.py
요지: 알림 asyncio.create_task()
커밋: perf(api): BL-004 parallelize checkout notifications
```

#### Commit B-4: SELECT * 전면 제거
```
파일: 백엔드 전반
커밋: perf(api): BL-006 replace SELECT * with explicit columns
```

#### Commit B-5: inflight dedup Map
```
파일: http-client.ts
커밋: perf(network): NC-002 add request deduplication
```

#### Commit B-6: Cache-Control 헤더
```
파일: 라우터 GET 엔드포인트
커밋: perf(api): NC-003 add Cache-Control headers
```

#### Commit B-7: 인접 탭 프리페치
```
파일: 탭 화면
커밋: perf(ux): NC-004 prefetch adjacent tab data
```

#### Commit B-8: 낙관적 UI (재고 삭제)
```
파일: inventory.tsx
커밋: perf(ux): PS-002 optimistic UI for inventory delete
```

#### Commit B-9: 레시피 추천 진행 메시지
```
파일: 레시피 탭 화면
커밋: perf(ux): PS-003 add recipe generation progress steps
```

#### Commit B-10: 스캔 진행률 바
```
파일: 스캔 화면
커밋: perf(ux): PS-004 add upload progress indicator
```

#### Commit B-11: Gemini duration 로깅
```
파일: gemini_service.py
커밋: perf(observability): OM-002 log gemini call duration
```

#### Commit B-12: 캐시 hit/miss + 클라이언트 perf 유틸
```
파일: recipe_cache.py, services/perf-logger.ts (신규)
커밋: perf(observability): OM-003 add cache and perf logging
```

#### Commit B-13: 클라이언트 캐시 Map 크기 제한
```
파일: http-client.ts
커밋: perf(network): PRL-002 limit client cache map size
```

#### Commit B-14: 스모크 벤치 스크립트
```
파일(신규): scripts/perf-smoke.sh
커밋: chore(perf): PRL-003 add perf smoke benchmark script
```

#### Commit B-15: babel console 제거
```
파일: babel.config.js
커밋: perf(build): BS-001 remove console in production
```

---

## 5. 테스트 / 벤치 전략

### 실행 커맨드
```bash
# 백엔드 테스트
cd prometheus-api && python -m pytest tests/ -v --tb=short

# 프론트 테스트
cd prometheus-app && npm test

# HTTP 벤치마크
hey -n 100 -c 10 -H "X-Device-ID: bench" -H "X-App-Token: $TOKEN" "$API/api/inventory"

# 메모리 확인
docker stats --no-stream prometheus-api

# 번들 크기
cd prometheus-app && npx expo export --platform ios && du -sh dist/bundles/

# gzip 효과
curl -sH "Accept-Encoding: gzip" "$API/api/inventory" -o /dev/null -w '%{size_download}'
```

### 벤치 before/after 기록
매 커밋 후 `.ai/reports/2026-02-13_codex_change_log.md`에 지표 기록:
```markdown
## Commit A-N
- **before**: p95=Xms, payload=YKB, memory=ZMB
- **after**: p95=X'ms, payload=Y'KB, memory=Z'MB
- **변화**: p95 -N%, payload -N%
```

---

## 6. 회귀 방지 (Perf Guard)

### 스모크 벤치 (Commit B-14)
- 배포 전 `scripts/perf-smoke.sh` 실행
- 핵심 API p95 + 메모리 확인
- 예산 초과 시 경고 (초기에는 차단 없음)

### CI 게이트 (향후)
```bash
# .github/workflows/perf-gate.yml (향후)
- name: Perf Smoke
  run: bash scripts/perf-smoke.sh
  env:
    API_URL: http://localhost:8000
```

### 성능 예산 문서
- `.ai/` 또는 `README.md` 에 성능 예산 테이블 유지
- 매 릴리즈마다 갱신

---

## 7. 롤백 기준 / 절차

### 롤백 기준
- API p95 > 성능 예산 상한 (5분 이상 지속)
- 메모리 RSS > 512MB
- FPS < 45
- 번들 크기 > 8MB

### 롤백 절차
1. Cloud Run → 이전 리비전 트래픽 전환
2. 원인 분석 → blocker 리포트
3. 수정 후 재배포

---

## 8. Codex Instructions 체크리스트

### 커밋 규칙
- [ ] 1 task = 1 commit, 변경 파일 ≤ 10
- [ ] 메시지: `perf(<scope>): <원본ID> <description>`
- [ ] 성능 목적 외 기능/스타일 변경 금지

### 벤치/테스트 게이트
- [ ] 매 커밋 후 테스트 + 벤치 실행
- [ ] before/after 지표 기록
- [ ] 2회 연속 실패 → 중단 + blocker 리포트

### 실행 순서
- [ ] Phase A: A-1(관측) → A-2(타임아웃) → A-3(캐시) → A-4(gzip) → A-5(쿼리) → A-6(FlatList) → A-7/A-8(스켈레톤)
- [ ] Phase B: B-1~B-15 순차 (jest 인프라 확보 후 프론트 작업)

### 보고
- [ ] `.ai/reports/2026-02-13_codex_change_log.md` (커밋별 before/after)
- [ ] 실패 시 `.ai/reports/2026-02-13_codex_blockers.md`
- [ ] 미해결 → backlog.md
