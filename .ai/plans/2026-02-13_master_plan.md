# Master Execution Plan – 2026-02-13

> PROMETHEUS 코드베이스의 6개 에이전트 보고서를 통합한 Codex용 실행계획.
> 모든 작업은 "작은 커밋" 단위로 분해되며, 각 커밋에 변경 파일·요지·테스트 커맨드를 명시한다.

---

## 1. 통합 요약

| 에이전트 | 🔴 | 🟡 | 🟢 | 합계 |
|---------|-----|-----|-----|------|
| 01 Code Review | 3 | 5 | 3 | 11 |
| 02 UI/UX | 1 | 4 | 2 | 7 |
| 03 Test Engineering | 6 | 4 | 0 | 10 |
| 04 Feature Discovery | 0 | 0 | 0 | 7 (별도) |
| 05 Perf & Reliability | 2 | 4 | 2 | 8 |
| 06 Security & Privacy | 2 | 3 | 2 | 7 |
| **합계** | **14** | **20** | **9** | **50** |

---

## 2. 우선순위 분류

### P0 — 즉시 해결 (보안·안정성 위험, 서비스 중단 가능)

| # | 원본 ID | 제목 | 사용자 영향 | 리스크 | 노력도 | 근거 |
|---|---------|------|-----------|--------|--------|------|
| 1 | SEC-001 / CR-001 | Admin 토큰 timing-safe 비교 | 낮음 | 🔴 보안 취약 | S | 타이밍 사이드채널; 1줄 수정 |
| 2 | SEC-002 | Dockerfile non-root 사용자 | 낮음 | 🔴 컨테이너 보안 | S | 3줄 추가; 배포 즉시 효과 |
| 3 | PR-001 | Gemini API 타임아웃 추가 | 높음 | 🔴 서비스 중단 | S | Gemini 장애 시 전체 행 |
| 4 | PR-002 | RecipeCache 크기 제한 | 중간 | 🔴 메모리 고갈 | S | 장기 운영 시 누적 |
| 5 | CR-002 | 스캔 업로드 스트리밍 크기 검증 | 중간 | 🔴 OOM 가능 | M | 악의적 대용량 업로드 |
| 6 | TE-SETUP-001 | 백엔드 pytest 인프라 구축 | 높음 | 🔴 품질 기반 없음 | M | 모든 후속 작업의 전제 |
| 7 | TE-001 | security.py 단위 테스트 | 중간 | 🔴 인증 검증 없음 | S | P0 수정 검증 필수 |

### P1 — 이번 사이클 (품질·안정성 개선, 1-2주 내)

| # | 원본 ID | 제목 | 사용자 영향 | 리스크 | 노력도 | 근거 |
|---|---------|------|-----------|--------|--------|------|
| 8 | CR-003 | storage_category 함수 통합 | 중간 | 🔴 데이터 불일치 | M | 동일 입력에 다른 결과 |
| 9 | SEC-007 | .dockerignore 생성 | 낮음 | 🟡 시크릿 노출 | S | 간단, 즉시 효과 |
| 10 | PR-006 | 헬스체크 엔드포인트 | 낮음 | 🟡 모니터링 공백 | S | Cloud Run 프로브 |
| 11 | PR-003 | bulk_upsert 쿼리 최적화 | 중간 | 🟡 성능 | S | SELECT 범위 축소 |
| 12 | CR-007 | Gemini 폴백 로깅 상향 | 낮음 | 🟡 운영 가시성 | S | 1줄 수정 |
| 13 | TE-SETUP-002 | 프론트 jest 인프라 구축 | 높음 | 🟡 품질 기반 | M | 프론트 테스트 전제 |
| 14 | TE-002 | gemini_service 테스트 | 중간 | 🟡 AI 파싱 검증 | M | 불안정 응답 대비 |
| 15 | TE-003 | inventory_service 테스트 | 중간 | 🟡 핵심 로직 | M | 병합 로직 검증 |
| 16 | TE-004 | scans 엔드포인트 테스트 | 중간 | 🟡 업로드 파이프라인 | M | P0 변경 검증 |
| 17 | UX-001 | accessibilityLabel 적용 | 높음 | 🟡 접근성 | M | 법적 요구사항 연관 |
| 18 | UX-005 | 삭제 확인 대화상자 통일 | 중간 | 🟡 데이터 손실 | S | 실수로 삭제 방지 |
| 19 | CR-004 | SELECT * 제거 | 낮음 | 🟡 성능 | M | 코드 전반 |
| 20 | CR-006 | 에러 메시지 일관성 | 낮음 | 🟡 UX | M | 한/영 혼재 |
| 21 | PR-005 | FlatList 최적화 | 중간 | 🟡 UX 성능 | S | 스크롤 FPS |

### P2 — 백로그 (차기 사이클)

| # | 원본 ID | 제목 | 노력도 |
|---|---------|------|--------|
| 22 | CR-005 | shopping.py 서비스 분리 | L |
| 23 | CR-008 | recipe_id 타입 재설계 | M |
| 24 | SEC-003 | CORS 프로덕션 검증 강화 | S |
| 25 | SEC-004 | APP_TOKEN 기본값 경고 | S |
| 26 | SEC-005 | 클라이언트 토큰 보안 검토 | M |
| 27 | SEC-006 | requirements.txt 버전 고정 | S |
| 28 | UX-002 | 빈 상태 공통 컴포넌트 | M |
| 29 | UX-003 | 에러 재시도 버튼 | M |
| 30 | UX-004 | 하드코딩 색상 → 토큰 | M |
| 31 | PR-004 | check-expiry 배치 처리 | M |
| 32 | TE-005~008 | 추가 테스트 작성 | M×4 |
| 33 | FD-001 | 글로벌 검색 기능 | M |
| 34 | FD-002 | 온보딩 화면 | M |
| 35 | FD-003~007 | 식단계획/영양/통계/공유/위젯 | L~XL |

---

## 3. Codex 커밋 분해 (P0 + P1)

### Phase A: P0 보안·안정성 수정 (7 커밋)

#### Commit A-1: Admin 토큰 timing-safe 비교
```
파일: prometheus-api/app/api/admin.py
변경: L28 — `x_admin_token != token` → `not secrets.compare_digest(x_admin_token, token)`
     + import secrets 추가
테스트: (TE-001 완료 후) cd prometheus-api && python -m pytest tests/test_admin.py -v
커밋: security(api): SEC-001 use timing-safe comparison for admin token
```

#### Commit A-2: Dockerfile non-root 사용자
```
파일: prometheus-api/Dockerfile
변경: RUN adduser --disabled-password --no-create-home appuser
     + USER appuser (CMD 이전)
     + .dockerignore 파일 생성 (.env, __pycache__, .git, *.pyc)
테스트: docker build -t prometheus-api . && docker run --rm prometheus-api whoami → "appuser"
커밋: security(infra): SEC-002 run container as non-root user
```

#### Commit A-3: Gemini API 타임아웃 추가
```
파일: prometheus-api/app/services/gemini_service.py
변경: _generate_with_model_fallback() 내에 asyncio.wait_for(timeout=30) 래핑
     + GEMINI_TIMEOUT_SECONDS 상수 추가
테스트: cd prometheus-api && python -m pytest tests/test_services/test_gemini_service.py -v
커밋: perf(api): PR-001 add explicit timeout to gemini API calls
```

#### Commit A-4: RecipeCache 크기 제한
```
파일: prometheus-api/app/services/recipe_cache.py
변경: RecipeCache.__init__에 max_devices=100 파라미터
     + set_many()에서 크기 초과 시 가장 오래된 디바이스 제거
     + _prune_locked()에서 max 체크 추가
테스트: cd prometheus-api && python -m pytest tests/test_services/test_recipe_cache.py -v
커밋: perf(api): PR-002 add max size limit to in-memory recipe cache
```

#### Commit A-5: 스캔 업로드 스트리밍 크기 검증
```
파일: prometheus-api/app/api/scans.py
변경: L287-290 → chunk 읽기 방식으로 변경, 크기 초과 시 조기 중단
     chunks = []
     total = 0
     async for chunk in file:  # 또는 SpooledTemporaryFile 활용
         total += len(chunk)
         if total > max_upload_bytes:
             raise HTTPException(413, ...)
         chunks.append(chunk)
     image_bytes = b"".join(chunks)
테스트: cd prometheus-api && python -m pytest tests/test_scans.py -v -k "test_upload_size"
커밋: security(api): CR-002 stream-validate upload size before full read
```

#### Commit A-6: 백엔드 pytest 인프라 구축
```
파일(신규):
  - prometheus-api/tests/__init__.py
  - prometheus-api/tests/conftest.py (mock Supabase, mock GeminiService, mock FCM)
  - prometheus-api/pytest.ini (asyncio_mode=auto, testpaths=tests)
  - prometheus-api/.env.test
변경: requirements.txt에 pytest, pytest-asyncio, httpx 추가 (dev 섹션)
테스트: cd prometheus-api && python -m pytest --co -q (테스트 수집 확인)
커밋: chore(test): TE-SETUP-001 initialize pytest infrastructure with mock fixtures
```

#### Commit A-7: security.py 단위 테스트
```
파일(신규): prometheus-api/tests/test_security.py
변경: require_app_token (유효/무효/미전송), get_device_id (유효/짧음/긴/화이트리스트)
     + _require_admin_token (timing-safe 검증)
테스트: cd prometheus-api && python -m pytest tests/test_security.py -v
커밋: test(api): TE-001 add security module unit tests
```

---

### Phase B: P1 품질·안정성 개선 (14 커밋)

#### Commit B-1: storage_category 함수 통합
```
파일: prometheus-api/app/services/storage_utils.py (신규)
     prometheus-api/app/api/scans.py, prometheus-api/app/api/inventory.py
변경: 공통 normalize_storage_category(), guess_storage_from_name() 추출
테스트: cd prometheus-api && python -m pytest tests/test_services/test_storage_utils.py -v
커밋: refactor(api): CR-003 extract shared storage category utilities
```

#### Commit B-2: .dockerignore 생성 (A-2에 포함 완료된 경우 스킵)

#### Commit B-3: 헬스체크 엔드포인트
```
파일: prometheus-api/app/main.py
변경: @app.get("/health") → DB ping + 기본 상태 반환
테스트: cd prometheus-api && python -m pytest tests/test_main.py -v -k "health"
커밋: feat(api): PR-006 add /health endpoint with DB connectivity check
```

#### Commit B-4: bulk_upsert 쿼리 최적화
```
파일: prometheus-api/app/services/inventory_service.py
변경: L89 — .select("*") → .select("id,name,quantity,unit,expiry_date,category")
     + IN 절 필터링 (입력 이름 목록으로 제한)
테스트: cd prometheus-api && python -m pytest tests/test_services/test_inventory_service.py -v
커밋: perf(api): PR-003 optimize bulk_upsert inventory query
```

#### Commit B-5: Gemini 폴백 로깅 상향
```
파일: prometheus-api/app/services/gemini_service.py
변경: 모델 NotFound 첫 실패 시 logger.warning() 사용
테스트: cd prometheus-api && python -m pytest tests/test_services/test_gemini_service.py -v
커밋: fix(api): CR-007 promote gemini model fallback log to warning
```

#### Commit B-6: 프론트 jest 인프라 구축
```
파일(신규):
  - prometheus-app/jest.config.js
  - prometheus-app/__tests__/setup.ts
변경: package.json에 jest, @testing-library/react-native, jest-expo 추가
     + "test" script 추가
테스트: cd prometheus-app && npm test -- --passWithNoTests
커밋: chore(test): TE-SETUP-002 initialize jest infrastructure
```

#### Commit B-7: gemini_service 테스트
```
파일(신규): prometheus-api/tests/test_services/test_gemini_service.py
테스트: cd prometheus-api && python -m pytest tests/test_services/test_gemini_service.py -v
커밋: test(api): TE-002 add gemini service unit tests with mocked API
```

#### Commit B-8: inventory_service 테스트
```
파일(신규): prometheus-api/tests/test_services/test_inventory_service.py
테스트: cd prometheus-api && python -m pytest tests/test_services/test_inventory_service.py -v
커밋: test(api): TE-003 add inventory service unit tests
```

#### Commit B-9: scans 엔드포인트 테스트
```
파일(신규): prometheus-api/tests/test_scans.py
테스트: cd prometheus-api && python -m pytest tests/test_scans.py -v
커밋: test(api): TE-004 add scans endpoint integration tests
```

#### Commit B-10: accessibilityLabel 적용
```
파일: prometheus-app/components/InventoryItemCard.tsx, RecipeCardStack.tsx,
     RoundButton.tsx, GlassCard.tsx + 탭 화면의 Touchable 요소
변경: 모든 Touchable/Pressable에 accessibilityLabel 추가
테스트: cd prometheus-app && npm test
커밋: fix(app): UX-001 add accessibility labels to interactive elements
```

#### Commit B-11: 삭제 확인 대화상자 통일
```
파일: 관련 탭 화면 (inventory.tsx, shopping 관련)
변경: Alert.alert() 확인 모달을 모든 삭제 작업에 통일 적용
테스트: cd prometheus-app && npm test
커밋: fix(app): UX-005 unify delete confirmation dialogs
```

#### Commit B-12: SELECT * 제거
```
파일: 백엔드 전반 (scans.py, admin.py, recipes.py 등)
변경: .select("*") → 필요 컬럼 명시
테스트: cd prometheus-api && python -m pytest -v
커밋: perf(api): CR-004 replace SELECT * with explicit column selection
```

#### Commit B-13: 에러 메시지 일관성
```
파일: 백엔드 라우터 전반
변경: 모든 HTTPException detail을 영어로 통일, localizeServerError에서 한국어 매핑
테스트: cd prometheus-api && python -m pytest -v
커밋: refactor(api): CR-006 standardize error messages to English
```

#### Commit B-14: FlatList 최적화
```
파일: prometheus-app/app/(tabs)/inventory.tsx, history.tsx
변경: getItemLayout, windowSize, maxToRenderPerBatch props 추가
테스트: cd prometheus-app && npm test
커밋: perf(app): PR-005 optimize FlatList rendering performance
```

---

## 4. 테스트 전략

### 단위 테스트 (Unit)
```bash
# 백엔드
cd prometheus-api && python -m pytest tests/ -v --tb=short

# 프론트엔드
cd prometheus-app && npm test
```

### 통합 테스트 (Integration)
```bash
# FastAPI TestClient로 엔드포인트 E2E 호출
cd prometheus-api && python -m pytest tests/ -v -k "integration" --tb=short
```

### E2E 테스트 (향후)
- Detox 또는 Maestro로 모바일 플로우 자동화
- 핵심 시나리오: 스캔→재고→레시피→요리 완료→재고 차감

### 커버리지 확인
```bash
cd prometheus-api && python -m pytest --cov=app --cov-report=term-missing
```

---

## 5. 롤백 / 가드레일

### 기능 플래그
- 현재 기능 플래그 시스템 없음. 신규 기능(FD-*) 구현 시 환경변수 기반 플래그 도입 권장:
  ```python
  # config.py
  feature_search_enabled: bool = False
  feature_onboarding_enabled: bool = False
  ```

### 단계적 적용
| Phase | 범위 | 롤백 판단 시점 |
|-------|------|--------------|
| A (P0) | 보안/안정성 — 즉시 배포 | 배포 후 5분: 에러율 > 5% |
| B (P1) | 품질 — 1주 내 배포 | 배포 후 1시간: p95 레이턴시 > 3초 |
| P2 | 백로그 — 차기 스프린트 | 스프린트 단위 판단 |

### 관측 지표
| 지표 | 소스 | 임계치 | 조치 |
|------|------|--------|------|
| API 에러율 | Cloud Run 로그 | > 5% (5분) | 즉시 이전 리비전으로 롤백 |
| p95 레이턴시 | Cloud Run 메트릭 | > 3초 | 원인 분석 후 판단 |
| 메모리 사용량 | Cloud Run 메트릭 | > 512MB | 캐시 크기 조정 |
| Gemini 실패율 | 앱 로그 `gemini` | > 10% | 폴백 모델 확인 |
| 헬스체크 | `/health` 엔드포인트 | 3연속 실패 | Cloud Run 자동 재시작 |

### DB 마이그레이션 롤백
- 현 사이클에 스키마 변경 없음. P2에서 필요 시 역방향 SQL 필수 동봉.

---

## 6. Codex Instructions (체크리스트)

Codex가 이 계획을 실행할 때 **반드시** 준수해야 하는 규칙:

### 커밋 규칙
- [ ] 하나의 커밋 = 하나의 논리적 변경 (복수 파일 허용, 10개 이하)
- [ ] 커밋 메시지: `<type>(<scope>): <원본 ID> <description>`
- [ ] 타입: fix, feat, refactor, test, perf, security, chore, docs
- [ ] 스코프: api, app, infra, test, schema, service, component

### 코드 작업 규칙
- [ ] 모든 API 라우터에 `dependencies=[Depends(require_app_token)]` 유지
- [ ] 모든 DB 쿼리에 `.eq("device_id", device_id)` 필터 필수
- [ ] Pydantic 모델은 `schemas/schemas.py`에 정의
- [ ] Gemini 응답은 `json.loads()` + `try/except` 필수
- [ ] 프론트 데이터 변경 후 `invalidateCache()` 필수
- [ ] 새 패키지 추가 시 라이선스(MIT/Apache 2.0) 확인

### 테스트 규칙
- [ ] 🔴 변경: 단위 + 통합 테스트 필수
- [ ] 🟡 변경: 최소 1개 관련 테스트 필수
- [ ] 🟢 변경: 기존 테스트 통과 확인
- [ ] 매 커밋 후 `pytest -v` / `npm test` 실행

### 보고 규칙
- [ ] 각 커밋 완료 후 `.ai/reports/2026-02-13_changelog.md`에 기록
- [ ] 모든 작업 완료 후 PR 요약 작성
- [ ] 해결되지 않은 항목은 `.ai/reports/backlog.md`로 이관

### 안전 규칙
- [ ] DB 스키마 변경 시 반드시 인간 리뷰 후 적용
- [ ] `.env`, API 키, 토큰은 절대 커밋하지 않음
- [ ] 배포 전 전체 테스트 스위트 통과 확인
- [ ] 위험도 🔴 변경은 반드시 인간 리뷰 후 머지

### 실행 순서
- [ ] Phase A (P0) → Phase B (P1) 순서 엄수
- [ ] Phase A 내에서 A-6 (pytest 인프라) → A-7 (보안 테스트) → 나머지 순서
- [ ] Phase B 내에서 B-6 (jest 인프라) 선행 후 프론트 작업 진행
