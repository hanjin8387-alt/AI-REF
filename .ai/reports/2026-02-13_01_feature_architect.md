# Feature Architect Report – 2026-02-13

## Feature: <FEATURE_REQUEST> 기반 기능강화 구조화

> 주의: 사용자로부터 구체적 기능요청(`<FEATURE_REQUEST>`)이 아직 바인딩되지 않았다.
> 본 보고서는 현재 코드베이스를 분석하여 **기능 아키텍처 관점의 개선 사항**과 **기능 확장 준비 상태**를 평가한다.

---

## Assumptions
- `<FEATURE_REQUEST>`가 구체적으로 주어지면 유저스토리/수용기준을 즉시 생성 가능
- 현재는 "기능강화 준비도" 분석으로 대체

---

## Current Architecture Assessment

### User Story Readiness
| 도메인 | 유저스토리 작성 가능 | 제약 |
|--------|---------------------|------|
| 스캔 | ✅ | Gemini 의존; 타임아웃 미적용 |
| 재고 | ✅ | `_normalize_storage_category` 중복 |
| 레시피 | ✅ | `recipe_id` UUID vs 해시 불일치 |
| 장보기 | ✅ | 734줄 단일 파일 (분리 필요) |
| 알림 | ✅ | FCM 연동 존재 |
| 통계 | 🟡 | stats 엔드포인트 존재하나 제한적 |

### Data Model Gaps

#### FA-001: `cooking_history.recipe_id` UUID 강제 → AI 생성 레시피 호환 불가
- **파일**: `schema.sql` L94 — `recipe_id UUID REFERENCES recipes(id)`
- **설명**: AI가 생성한 레시피는 `gemini-{hash}` 형태의 비UUID ID 사용. `cooking_history`에 기록 시 NULL로 우회 중.
- **영향**: 요리 기록 추적 불완전, 통계 정확도 저하
- **권장 조치**: `recipe_id`를 `VARCHAR(255)`로 변경, FK 제거 또는 별도 `recipe_ref` 컬럼
- **위험도**: 🟡

```sql
-- Forward Migration
ALTER TABLE cooking_history ALTER COLUMN recipe_id TYPE VARCHAR(255);
ALTER TABLE cooking_history DROP CONSTRAINT IF EXISTS cooking_history_recipe_id_fkey;

-- Rollback
ALTER TABLE cooking_history ADD CONSTRAINT cooking_history_recipe_id_fkey
  FOREIGN KEY (recipe_id) REFERENCES recipes(id);
ALTER TABLE cooking_history ALTER COLUMN recipe_id TYPE UUID USING recipe_id::uuid;
```

#### FA-002: 기능 플래그 패턴 부재
- **파일**: `config.py` — 기능 플래그 전용 속성 없음
- **설명**: `require_app_token: bool` 같은 ON/OFF 설정은 있으나, 기능별 플래그 패턴이 정의되지 않음.
- **권장 조치**: `config.py`에 feature flag 섹션 추가
- **위험도**: 🟡

```python
# Feature Flags
feature_search_enabled: bool = False
feature_onboarding_enabled: bool = False
feature_meal_planning_enabled: bool = False
```

#### FA-003: API 버전닝 미적용
- **파일**: `main.py` — 라우터 prefix가 `/api/v1/...` 이 아닌 `/api/...`
- **설명**: breaking change 시 하위 호환성 유지 어려움
- **권장 조치**: `/api/v1/` prefix 도입 (현재 클라이언트가 적으므로 즉시 가능)
- **위험도**: 🟢

---

## Findings

| # | 제목 | 파일 | 위험도 |
|---|------|------|--------|
| FA-001 | recipe_id UUID 강제 | schema.sql L94 | 🟡 |
| FA-002 | 기능 플래그 패턴 부재 | config.py | 🟡 |
| FA-003 | API 버전닝 미적용 | main.py | 🟢 |
| FA-004 | 유저스토리 템플릿/백로그 도구 없음 | - | 🟢 |

## Recommendations
1. `config.py`에 `FeatureFlags` 하위 클래스를 도입하여 기능 플래그를 구조적으로 관리
2. 새 기능 추가 시 `schema.sql`에 `-- Migration: YYYY-MM-DD` 주석과 역마이그레이션 동봉
3. API 버전닝은 다음 breaking change 시 도입 (현재는 `/api/` 유지)

## Task List
| # | 파일 | 변경요지 | 테스트 커맨드 | 수용기준 | 위험도 |
|---|------|---------|-------------|---------|--------|
| 1 | `schema.sql` | recipe_id VARCHAR(255)로 변경 | `pytest tests/ -v` | 기존 레시피 조회 정상 | 🟡 |
| 2 | `config.py` | feature flag 섹션 추가 | `pytest tests/ -v` | 플래그 OFF 시 기능 비활성 | 🟡 |
| 3 | `main.py` | API v1 prefix 도입 (선택적) | `pytest tests/ -v` | 기존 경로 호환 | 🟢 |

## Risk & Rollback
- **FA-001 롤백**: 역마이그레이션 SQL 상기 포함
- **FA-002 롤백**: 플래그 제거 시 기능이 기본 동작으로 복귀 (안전)
- **FA-003 롤백**: prefix 제거만으로 복원 가능
