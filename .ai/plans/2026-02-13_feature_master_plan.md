# Feature Enhancement Master Plan – 2026-02-13

> 7개 에이전트 리포트를 통합한 Codex 실행계획.
> 모든 작업은 "작은 커밋" 단위로 분해. 각 커밋에 변경파일·요지·테스트·수용기준 명시.

---

## 1. 통합 요약

| 에이전트 | 🔴 | 🟡 | 🟢 | 합계 |
|---------|-----|-----|-----|------|
| 01 Feature Architect | 0 | 2 | 2 | 4 |
| 02 UI/UX | 1 | 5 | 2 | 8 |
| 03 Backend/API | 3 | 5 | 3 | 11 |
| 04 Test Engineering | 4 | 6 | 0 | 10 |
| 05 Observability | 1 | 4 | 2 | 7 |
| 06 Perf/Reliability | 2 | 5 | 2 | 9 |
| 07 Security/Privacy | 2 | 4 | 3 | 9 |
| **합계** | **13** | **31** | **14** | **58** |

---

## 2. 우선순위 분류

### P0 — 즉시 해결 (보안·안정성·기반)

| # | 원본 ID | 제목 | 사용자 영향 | 리스크 | 노력 | 근거 |
|---|---------|------|-----------|--------|------|------|
| 1 | SEC-001 / BA-001 | Admin 토큰 timing-safe 비교 | 낮음 | 🔴 보안 | S | 타이밍 사이드채널; 1줄 |
| 2 | SEC-002 | Dockerfile non-root + .dockerignore | 낮음 | 🔴 컨테이너 보안 | S | 3줄; 즉시 효과 |
| 3 | PR-001 | Gemini API 타임아웃 추가 | 높음 | 🔴 서비스 중단 | S | Gemini 장애 시 전체 행 |
| 4 | PR-002 | RecipeCache 크기 제한 | 중간 | 🔴 메모리 고갈 | S | 장기 운영 시 누적 |
| 5 | BA-002 | 스캔 업로드 스트리밍 크기 검증 | 중간 | 🔴 OOM 가능 | M | 대용량 업로드 |
| 6 | BA-003 | storage_category 함수 통합 | 중간 | 🔴 데이터 불일치 | M | 동일 입력 다른 결과 |
| 7 | TE-001 | 백엔드 pytest 인프라 구축 | 높음 | 🔴 품질 기반 없음 | M | 모든 후속 작업 전제 |
| 8 | TE-002 | security.py 단위 테스트 | 중간 | 🔴 인증 검증 필수 | S | P0 수정 검증 |
| 9 | OA-001 | request_id 미들웨어 추가 | 중간 | 🔴 디버깅 불가 | S | 운영 필수 |

### P1 — 이번 사이클 1-2주 내

| # | 원본 ID | 제목 | 노력 | 근거 |
|---|---------|------|------|------|
| 10 | PR-006 | /health 엔드포인트 | S | Cloud Run 프로브 |
| 11 | BA-007 | Gemini 폴백 로깅 warning 상향 | S | 운영 가시성 |
| 12 | PR-003 | bulk_upsert 쿼리 최적화 | S | SELECT 범위 축소 |
| 13 | TE-003 | gemini_service 테스트 | M | AI 파싱 검증 |
| 14 | TE-004 | inventory_service 테스트 | M | 핵심 로직 |
| 15 | TE-005 | scans 엔드포인트 테스트 | M | 업로드 파이프라인 |
| 16 | TE-008 | 프론트 jest 인프라 구축 | M | 프론트 테스트 전제 |
| 17 | UX-001 | accessibilityLabel 적용 | M | 접근성 |
| 18 | UX-005 | 삭제 확인 대화상자 통일 | S | 데이터 손실 방지 |
| 19 | OA-002 | 로그 device_id 필수 포함 | S | 추적 |
| 20 | OA-003 | 외부 API 소요시간 로깅 | S | 성능 관측 |
| 21 | OA-004 | 비즈니스 이벤트 로깅 | M | 퍼널 분석 기반 |
| 22 | BA-004 | SELECT * 제거 | M | 성능 |
| 23 | BA-006 | 에러 메시지 영어 통일 | M | UX 일관성 |
| 24 | PR-005 | FlatList 최적화 | S | 스크롤 성능 |
| 25 | FA-002 | 기능 플래그 패턴 추가 | S | 기능 강화 전제 |

### P2 — 백로그 (차기 사이클)

| # | 원본 ID | 제목 | 노력 |
|---|---------|------|------|
| 26 | BA-005 | shopping.py 서비스 분리 | L |
| 27 | BA-008 | normalization 유틸 통합 | M |
| 28 | FA-001 | recipe_id VARCHAR 변경 | M |
| 29 | FA-003 | API v1 prefix | M |
| 30 | UX-002 | 빈 상태 공통 컴포넌트 | M |
| 31 | UX-003 | 에러 재시도 버튼 | M |
| 32 | UX-004 | 하드코딩 색상 → 토큰 | M |
| 33 | UX-006 | 공통 LoadingOverlay | M |
| 34 | PR-004 | check-expiry 배치 처리 | M |
| 35 | PR-007 | 오프라인 큐 충돌 해소 | M |
| 36 | SEC-003~005 | CORS/TOKEN 프로덕션 강화 | S~M |
| 37 | SEC-006~007 | 버전 고정, 문서화 | S |
| 38 | OA-005 | 프론트 ErrorBoundary | M |
| 39 | TE-006~010 | 추가 테스트 작성 | M×5 |

---

## 3. Implementation Plan (P0 + P1 커밋 분해)

### Phase A: P0 보안·안정성·기반 (9 커밋)

---

#### Commit A-1: Admin 토큰 timing-safe 비교
| 항목 | 내용 |
|------|------|
| 변경 파일 | `prometheus-api/app/api/admin.py` |
| 요지 | L28: `!=` → `secrets.compare_digest()` + `import secrets` |
| 테스트 | `cd prometheus-api && python -m pytest tests/test_admin.py -v` (A-7 이후) |
| 수용기준 | 유효/무효/미전송 토큰에 대해 올바른 HTTP 응답 |
| 커밋 | `security(api): SEC-001 use timing-safe admin token comparison` |

---

#### Commit A-2: Dockerfile non-root + .dockerignore
| 항목 | 내용 |
|------|------|
| 변경 파일 | `Dockerfile`, `.dockerignore` (신규) |
| 요지 | `RUN adduser --disabled-password --no-create-home appuser` + `USER appuser`. `.dockerignore`: `.env`, `__pycache__`, `.git`, `*.pyc`, `tests/` |
| 테스트 | `docker build -t prometheus-api . && docker run --rm prometheus-api whoami` → `appuser` |
| 수용기준 | 빌드 성공, non-root 실행 |
| 커밋 | `security(infra): SEC-002 run container as non-root user` |

---

#### Commit A-3: Gemini API 타임아웃
| 항목 | 내용 |
|------|------|
| 변경 파일 | `prometheus-api/app/services/gemini_service.py` |
| 요지 | `_generate_with_model_fallback()` 내 `asyncio.wait_for(coro, timeout=GEMINI_TIMEOUT_SECONDS)` |
| 테스트 | `pytest tests/test_services/test_gemini_service.py -v` |
| 수용기준 | 타임아웃 초과 시 적절한 에러 발생 |
| 커밋 | `perf(api): PR-001 add explicit timeout to gemini API calls` |

---

#### Commit A-4: RecipeCache 크기 제한
| 항목 | 내용 |
|------|------|
| 변경 파일 | `prometheus-api/app/services/recipe_cache.py` |
| 요지 | `RecipeCache.__init__(max_devices=100)` + LRU 퇴출 로직 |
| 테스트 | `pytest tests/test_services/test_recipe_cache.py -v` |
| 수용기준 | 디바이스 101개 시 가장 오래된 항목 제거 |
| 커밋 | `perf(api): PR-002 add max size limit to recipe cache` |

---

#### Commit A-5: 스캔 업로드 스트리밍 크기 검증
| 항목 | 내용 |
|------|------|
| 변경 파일 | `prometheus-api/app/api/scans.py` |
| 요지 | L287-290: chunk 읽기 → 초과 시 HTTP 413 |
| 테스트 | `pytest tests/test_scans.py -v -k "test_upload_size"` |
| 수용기준 | 초과 파일에 413 반환, 정상 파일 처리 유지 |
| 커밋 | `security(api): BA-002 stream-validate upload size` |

---

#### Commit A-6: storage_category 함수 통합
| 항목 | 내용 |
|------|------|
| 변경 파일 | `services/storage_utils.py` (신규), `scans.py`, `inventory.py` |
| 요지 | 공통 `normalize_storage_category()` 추출, 기존 함수를 import로 교체 |
| 테스트 | `pytest tests/test_services/test_storage_utils.py -v` |
| 수용기준 | 동일 입력 → 동일 결과 |
| 커밋 | `refactor(api): BA-003 extract shared storage category utilities` |

---

#### Commit A-7: 백엔드 pytest 인프라 구축
| 항목 | 내용 |
|------|------|
| 변경 파일(신규) | `tests/__init__.py`, `tests/conftest.py`, `pytest.ini`, `.env.test` |
| 요지 | Supabase/Gemini/FCM mock fixture, asyncio_mode=auto |
| 테스트 | `cd prometheus-api && python -m pytest --co -q` |
| 수용기준 | 테스트 수집 성공, 0 에러 |
| 커밋 | `chore(test): TE-001 initialize pytest infrastructure` |

---

#### Commit A-8: security.py 단위 테스트
| 항목 | 내용 |
|------|------|
| 변경 파일(신규) | `tests/test_security.py` |
| 요지 | require_app_token, get_device_id, admin 토큰 6+ 케이스 |
| 테스트 | `pytest tests/test_security.py -v` |
| 수용기준 | 모든 케이스 통과 |
| 커밋 | `test(api): TE-002 add security module unit tests` |

---

#### Commit A-9: request_id 미들웨어
| 항목 | 내용 |
|------|------|
| 변경 파일 | `prometheus-api/app/main.py` |
| 요지 | 미들웨어: `X-Request-ID` 헤더 읽기/UUID 생성 → 로그 컨텍스트 → 응답 헤더 |
| 테스트 | `pytest tests/test_main.py -v -k "request_id"` |
| 수용기준 | 응답 헤더에 `X-Request-ID` 존재 |
| 커밋 | `feat(api): OA-001 add request-id middleware` |

---

### Phase B: P1 품질·관측·테스트 (16 커밋)

---

#### Commit B-1: /health 엔드포인트
```
파일: main.py | 요지: DB ping 응답 | 커밋: feat(api): PR-006 add /health endpoint
```

#### Commit B-2: Gemini 폴백 로깅 warning
```
파일: gemini_service.py | 요지: info→warning | 커밋: fix(api): BA-007 promote gemini fallback log
```

#### Commit B-3: bulk_upsert 쿼리 최적화
```
파일: inventory_service.py | 요지: IN절 + 컬럼지정 | 커밋: perf(api): PR-003 optimize bulk upsert query
```

#### Commit B-4: 기능 플래그 패턴 추가
```
파일: config.py | 요지: feature flag 섹션 | 커밋: feat(api): FA-002 add feature flag pattern
```

#### Commit B-5: gemini_service 테스트
```
파일(신규): tests/test_services/test_gemini_service.py | 커밋: test(api): TE-003
```

#### Commit B-6: inventory_service 테스트
```
파일(신규): tests/test_services/test_inventory_service.py | 커밋: test(api): TE-004
```

#### Commit B-7: scans 엔드포인트 테스트
```
파일(신규): tests/test_scans.py | 커밋: test(api): TE-005
```

#### Commit B-8: 프론트 jest 인프라 구축
```
파일(신규): jest.config.js, __tests__/setup.ts | 요지: jest + testing-library
커밋: chore(test): TE-008 initialize jest infrastructure
```

#### Commit B-9: accessibilityLabel 적용
```
파일: components/*.tsx + 탭 화면 | 커밋: fix(app): UX-001 add accessibility labels
```

#### Commit B-10: 삭제 확인 대화상자 통일
```
파일: 삭제 관련 화면 | 커밋: fix(app): UX-005 unify delete confirmation
```

#### Commit B-11: 로그 device_id 필수
```
파일: 라우터 전반 | 커밋: feat(observability): OA-002 include device_id in all logs
```

#### Commit B-12: 외부 API 소요시간 로깅
```
파일: gemini_service.py, scans.py | 커밋: feat(observability): OA-003 log external API duration
```

#### Commit B-13: 비즈니스 이벤트 로깅
```
파일: 라우터 전반 | 커밋: feat(observability): OA-004 add business event logging
```

#### Commit B-14: SELECT * 제거
```
파일: 백엔드 전반 | 커밋: perf(api): BA-004 replace SELECT * with explicit columns
```

#### Commit B-15: 에러 메시지 영어 통일
```
파일: 백엔드 전반 | 커밋: refactor(api): BA-006 standardize error messages to English
```

#### Commit B-16: FlatList 최적화
```
파일: 탭 화면 | 커밋: perf(app): PR-005 optimize FlatList rendering
```

---

## 4. 테스트 전략

### 실행 커맨드
```bash
# 백엔드 단위/통합
cd prometheus-api && python -m pytest tests/ -v --tb=short

# 백엔드 커버리지
cd prometheus-api && python -m pytest --cov=app --cov-report=term-missing

# 프론트엔드
cd prometheus-app && npm test

# Docker 빌드 검증
cd prometheus-api && docker build -t prometheus-api .
```

### 테스트 피라미드
| 레벨 | 비율 | 도구 | 범위 |
|------|------|------|------|
| 단위 | 70% | pytest / jest | 서비스, 유틸, 컴포넌트 |
| 통합 | 25% | httpx TestClient / @testing-library | API 엔드포인트, 화면 흐름 |
| E2E | 5% | (향후 Detox/Maestro) | 스캔→재고→레시피 |

---

## 5. 가드레일

### 기능 플래그 (Commit B-4 이후)
```python
# config.py
feature_search_enabled: bool = False
feature_onboarding_enabled: bool = False
```
- 신규 기능은 플래그 OFF 상태로 배포
- QA 확인 후 플래그 ON

### 점진적 적용
| Phase | 범위 | 기간 |
|-------|------|------|
| A (P0) | 보안·안정성 9커밋 | 즉시 |
| B (P1) | 품질·테스트 16커밋 | 1-2주 |
| P2 | 백로그 | 차기 사이클 |

### 관측 지표
| 지표 | 임계치 | 조치 |
|------|--------|------|
| API 에러율 | > 5% (5분) | 이전 리비전 롤백 |
| p95 레이턴시 | > 3초 | 원인 분석 |
| 메모리 | > 512MB | 캐시 크기 조정 |
| Gemini 실패율 | > 10% | 폴백 모델 확인 |
| 헬스체크 | 3연속 실패 | 자동 재시작 |

---

## 6. 롤백 기준 / 절차

### 롤백 기준
- 배포 후 5분 내 에러율 > 5%
- 배포 후 1시간 내 p95 레이턴시 > 3초
- 헬스체크 3연속 실패

### 롤백 절차
1. Cloud Run → 이전 리비전으로 트래픽 100% 전환
2. 원인 분석 → `.ai/reports/YYYY-MM-DD_rollback_analysis.md` 작성
3. 수정 후 재배포

### DB 마이그레이션 롤백
- 현 P0/P1 사이클에 스키마 변경 없음
- P2에서 `recipe_id` 변경 시 역마이그레이션 SQL 필수 동봉

---

## 7. Codex Instructions 체크리스트

### 커밋 규칙
- [ ] 1 task = 1 commit, 변경 파일 ≤ 10
- [ ] 메시지: `<type>(<scope>): <원본ID> <description>`
- [ ] 타입: fix, feat, refactor, test, perf, security, chore, docs
- [ ] 스코프: api, app, infra, test, schema, service, component, observability

### 코드 규칙
- [ ] 모든 라우터에 `Depends(require_app_token)` 유지
- [ ] 모든 DB 쿼리에 `.eq("device_id", device_id)` 필터
- [ ] Gemini 응답은 `json.loads()` + `try/except`
- [ ] 새 패키지 라이선스 확인 (MIT/Apache 2.0)
- [ ] 프론트 데이터 변경 후 `invalidateCache()`

### 테스트 규칙
- [ ] 🔴 변경: 단위 + 통합 테스트 필수
- [ ] 🟡 변경: 최소 1개 테스트
- [ ] 매 커밋 후 테스트 실행
- [ ] 2회 연속 실패 → 중단 + 블로커 리포트

### 보고 규칙
- [ ] 매 커밋 → `.ai/reports/2026-02-13_codex_change_log.md` 기록
- [ ] 실패 시 → `.ai/reports/2026-02-13_codex_blockers.md` 생성
- [ ] 미해결 항목 → `.ai/reports/backlog.md` 이관

### 실행 순서
- [ ] Phase A (A-7 pytest 인프라 → A-8 보안 테스트 → A-1~A-6 → A-9)
- [ ] Phase B (B-1~B-8 순서, B-8 jest 인프라 후 프론트 작업)

### 안전 규칙
- [ ] DB 스키마 변경 시 인간 리뷰 필수
- [ ] `.env`, API 키, 토큰 절대 커밋 금지
- [ ] 🔴 변경은 인간 리뷰 후 머지
