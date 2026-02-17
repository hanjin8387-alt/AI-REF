# Feature Discovery Report – 2026-02-13

## Summary
- **분석 범위**: 기존 API 8개 모듈 (25+ 엔드포인트), 화면 6개 탭
- **발굴된 기능**: 신규 10개, 기존 강화 7개
- **예상 총 작업량**: S: 5 / M: 7 / L: 4 / XL: 1

---

## Current Feature Map

| 영역 | 기존 기능 | 완성도 |
|------|-----------|--------|
| 스캔 | 카메라, 갤러리, 영수증 OCR, 바코드(Open Food Facts), 저장 카테고리 자동 추론, 가격 추출 | ⭐⭐⭐⭐ |
| 재고 | CRUD, 벌크 upsert, 병합, 카테고리(냉장/냉동/상온), 유통기한, 삭제 복구(undo), 정렬/필터(expiry_date/name/created_at), 페이지네이션 | ⭐⭐⭐⭐ |
| 레시피 | AI 추천(Gemini), 즐겨찾기, 요리 완료(재고 자동 차감), 요리 기록, 부족 재료→장보기 추가 | ⭐⭐⭐⭐ |
| 장보기 | CRUD, 레시피 연동(from-recipe), 저재고 자동 추천, 체크아웃→재고 반영, pending/purchased 필터 | ⭐⭐⭐⭐ |
| 알림 | 유통기한 D-3/D-1/D-day, FCM 푸시, 인앱 알림(inventory/cooking/expiry/system), 읽음 표시 | ⭐⭐⭐ |
| 통계 | 요리 활동(total/most cooked/avg per week), 소비/낭비율, 카테고리 분포, 가격 히스토리 | ⭐⭐⭐ |
| 인증/백업 | 디바이스 등록, 데이터 내보내기/복원(merge/replace) | ⭐⭐⭐ |
| 다크 모드 | Colors.ts에 dark/light 정의 완료, 앱에서 `userInterfaceStyle: "light"` 고정 | ⭐⭐ |

---

## Discovered Features

### 🌟 High Impact / Quick Win

#### FD-001: 다크 모드 전환 지원
- **카테고리**: 기존 강화
- **사용자 가치**: 야간 사용 편의성 향상, 배터리 절약(OLED), 최신 UX 트렌드 충족
- **구현 복잡도**: S
- **현황**: `Colors.ts`에 `dark`/`light` 테마가 이미 정의되어 있으나, `app.json`에서 `"userInterfaceStyle": "light"`로 고정되어 있고, 프론트엔드에서 다크 모드 전환 로직이 없음. `useColorScheme` 훅이 존재하나 미활용
- **필요 변경**:
  - 백엔드: 변경 없음
  - 프론트엔드: `app.json`의 `userInterfaceStyle`을 `"automatic"`으로 변경, `_layout.tsx`에서 `useColorScheme` 활용, 모든 탭 화면에서 `Colors[colorScheme]` 참조
  - DB: 변경 없음
- **의존성**: 없음
- **우선순위 점수**: Impact(5) × Feasibility(5) = 25

#### FD-002: 재고 및 레시피 검색 기능 추가
- **카테고리**: 기존 강화
- **사용자 가치**: 재고가 많아질수록 원하는 항목을 빠르게 찾기 어려움. 레시피 즐겨찾기 목록 내 검색도 부재
- **구현 복잡도**: S
- **현황**: 재고 목록(`inventory.tsx`)은 정렬과 카테고리 필터만 지원. 텍스트 기반 검색 없음. 레시피 즐겨찾기도 검색 없음
- **필요 변경**:
  - 백엔드: `GET /inventory`에 `search` 쿼리 파라미터 추가 (`.ilike("name", f"%{search}%")`), `GET /recipes/favorites`에도 동일 적용
  - 프론트엔드: `inventory.tsx`와 `HomeScreen`에 검색바 UI 추가, 디바운스 적용
  - DB: 변경 없음 (기존 `idx_inventory_name` 인덱스 활용)
- **의존성**: 없음
- **우선순위 점수**: Impact(5) × Feasibility(5) = 25

#### FD-003: 온보딩 (첫 사용자 경험) 화면
- **카테고리**: 신규 기능
- **사용자 가치**: 첫 사용 시 앱의 핵심 기능(스캔→재고→레시피)을 자연스럽게 안내하여 이탈률 감소
- **구현 복잡도**: S
- **현황**: 온보딩 화면이 전혀 없음. 첫 실행 시 바로 홈 화면으로 진입
- **필요 변경**:
  - 백엔드: 변경 없음 (디바이스 첫 등록 여부는 기존 `/auth/device-register`로 판별 가능)
  - 프론트엔드: `app/(onboarding)` 또는 모달 기반 3~4단계 슬라이드 추가, AsyncStorage로 `onboarding_completed` 플래그 관리
  - DB: 변경 없음
- **의존성**: 없음
- **우선순위 점수**: Impact(4) × Feasibility(5) = 20

#### FD-004: 스캔 후 자동 레시피 추천 연결
- **카테고리**: 기존 강화
- **사용자 가치**: 스캔→재고 추가 후 "끊김" 해소, 자연스러운 사용 흐름 완성
- **구현 복잡도**: S
- **현황**: `scan.tsx`에서 재고 추가 후 "재고에 추가했어요" Alert만 표시. 다음 동작으로의 연결이 없음
- **필요 변경**:
  - 백엔드: 변경 없음 (기존 `/recipes/recommendations` 활용)
  - 프론트엔드: `scan.tsx`의 `addToInventory` 성공 후 "레시피 추천 보기" CTA 버튼 표시, 탭 전환 또는 모달로 추천 레시피 표시
  - DB: 변경 없음
- **의존성**: 없음
- **우선순위 점수**: Impact(4) × Feasibility(5) = 20

#### FD-005: 레시피 개인화 – 선호도 및 알레르기 설정
- **카테고리**: 신규 기능
- **사용자 가치**: 알레르기 재료 자동 제외, 개인 취향 반영으로 추천 적중률 향상
- **구현 복잡도**: M
- **현황**: Gemini 프롬프트에 개인화 컨텍스트 없음. 모든 사용자에게 동일한 추천
- **필요 변경**:
  - 백엔드: `user_preferences` 테이블 추가 (allergies, dietary, skill_level 등), `gemini_service.py`의 프롬프트에 사용자 선호도 주입, CRUD API 추가
  - 프론트엔드: 설정 화면 또는 온보딩에서 선호도 입력 UI
  - DB: `user_preferences` 테이블 신규
- **의존성**: FD-003 (온보딩과 병행 시 시너지)
- **우선순위 점수**: Impact(5) × Feasibility(4) = 20

---

### 🎯 High Impact / More Effort

#### FD-006: 식단 계획(Meal Planning) 자동 생성
- **카테고리**: 신규 기능 / AI 확장
- **사용자 가치**: 1주일 식단을 자동 생성하여 계획적 식사, 장보기 자동 연동으로 낭비율 감소
- **구현 복잡도**: L
- **현황**: 현재 레시피 추천은 개별 1회성. 주간 계획 기능 없음
- **필요 변경**:
  - 백엔드: `meal_plans` 테이블, `/meal-plans` API (생성/조회/수정), Gemini에 주간 식단 프롬프트 추가
  - 프론트엔드: 새 탭 또는 홈 하단에 주간 캘린더 뷰
  - DB: `meal_plans`, `meal_plan_items` 테이블 신규
- **의존성**: FD-005 (선호도 반영 시 더 정확)
- **우선순위 점수**: Impact(5) × Feasibility(3) = 15

#### FD-007: 영양 분석 기능
- **카테고리**: 신규 기능 / AI 확장
- **사용자 가치**: 레시피별 칼로리/영양소 표시, 건강 관리 동기 부여
- **구현 복잡도**: M
- **현황**: 레시피에 영양 정보 필드 없음
- **필요 변경**:
  - 백엔드: Gemini 프롬프트에 영양 정보 추가 요청, `Recipe` 스키마에 `nutrition` 필드 추가
  - 프론트엔드: 레시피 상세 화면에 영양 정보 카드 표시
  - DB: `recipes` 테이블에 `nutrition` JSONB 컬럼 추가 (선택)
- **의존성**: 없음
- **우선순위 점수**: Impact(4) × Feasibility(4) = 16

#### FD-008: 소셜/공유 기능 – 레시피 공유 링크
- **카테고리**: 신규 기능
- **사용자 가치**: 즐겨찾기 레시피를 가족/친구와 공유, 바이럴 성장
- **구현 복잡도**: M
- **현황**: 레시피 공유 기능 전무
- **필요 변경**:
  - 백엔드: `/recipes/{id}/share` 엔드포인트 → 공유 가능한 UUID 링크 생성, 공개 조회 API
  - 프론트엔드: Share 시트 연동 (`expo-sharing`), 딥링크 수신 처리
  - DB: `shared_recipes` 테이블 또는 `favorite_recipes`에 `share_token` 컬럼
- **의존성**: 없음
- **우선순위 점수**: Impact(4) × Feasibility(4) = 16

#### FD-009: 가족 재고 공유 (멀티 디바이스 동기화)
- **카테고리**: 신규 기능
- **사용자 가치**: 가족 구성원이 같은 재고를 실시간 공유, 중복 구매 방지
- **구현 복잡도**: XL
- **현황**: 현재 `device_id` 단위 격리. 멀티 디바이스 그룹 개념 없음
- **필요 변경**:
  - 백엔드: `households` 테이블, 멤버 관리 API, 재고/장보기를 household 기반으로 확장
  - 프론트엔드: 가족 그룹 관리 화면, 초대 코드/QR 기반 참여
  - DB: `households`, `household_members` 테이블, 기존 쿼리에 household_id 조건 추가
- **의존성**: 인증 체계 강화 필요 (현재 디바이스 토큰 기반)
- **우선순위 점수**: Impact(5) × Feasibility(2) = 10

---

### 💡 Nice-to-Have

#### FD-010: 게이미피케이션 – 요리 연속 기록 및 절약 통계
- **카테고리**: 신규 기능
- **사용자 가치**: 요리 연속 기록(streak), 음식 낭비 절감 금액 시각화로 동기 부여
- **구현 복잡도**: M
- **현황**: `cooking_history`와 `inventory_logs`에 데이터는 축적 중이나, 연속 기록이나 절약 금액 계산 로직 없음
- **필요 변경**:
  - 백엔드: `/stats/achievements` 엔드포인트 (연속 요리일, 절약 금액, 레벨 등), `price_history` 기반 절약 금액 계산
  - 프론트엔드: `history.tsx`에 성취 배지/스트릭 카운터 표시
  - DB: 별도 테이블 불필요 (기존 데이터로 계산 가능)
- **의존성**: 없음
- **우선순위 점수**: Impact(3) × Feasibility(4) = 12

#### FD-011: 음성 인식 재고 입력
- **카테고리**: 신규 기능 / AI 확장
- **사용자 가치**: 요리 중 손이 지저분할 때 음성으로 재고 추가/차감
- **구현 복잡도**: L
- **현황**: 입력 방식이 카메라/갤러리/바코드/수동에 한정
- **필요 변경**:
  - 백엔드: `/scans/voice` 엔드포인트 또는 Gemini 음성→텍스트 파싱
  - 프론트엔드: `expo-speech` 또는 `expo-av`로 녹음, 스캔 탭에 마이크 버튼 추가
  - DB: 변경 없음 (기존 bulk_add_inventory 활용)
- **의존성**: Gemini 음성 입력 파이프라인
- **우선순위 점수**: Impact(3) × Feasibility(3) = 9

#### FD-012: 위젯/바로가기 지원 (유통기한 임박 위젯)
- **카테고리**: 신규 기능
- **사용자 가치**: 앱을 열지 않고도 유통기한 임박 재료를 홈 화면에서 확인
- **구현 복잡도**: L
- **현황**: Expo 기반으로 네이티브 위젯 미구현
- **필요 변경**:
  - 백엔드: 변경 없음 (기존 API 활용)
  - 프론트엔드: `react-native-widget-extension` (iOS) / `react-native-android-widget` 패키지 도입
  - DB: 변경 없음
- **의존성**: Expo prebuild 필요
- **우선순위 점수**: Impact(3) × Feasibility(2) = 6

#### FD-013: 다중 언어 완전 지원 (i18n)
- **카테고리**: 기존 강화
- **사용자 가치**: 해외 사용자 접근성 향상
- **구현 복잡도**: M
- **현황**: `gemini_service.py`에 `language` 설정이 있으나 (`ko`/`en`/`ja`), 프론트엔드 UI 문자열은 모두 한국어 하드코딩
- **필요 변경**:
  - 백엔드: 이미 다국어 프롬프트 지원 (확장만 필요)
  - 프론트엔드: `i18n-js` 또는 `expo-localization`으로 번역 파일 분리
  - DB: 변경 없음
- **의존성**: 없음
- **우선순위 점수**: Impact(3) × Feasibility(3) = 9

#### FD-014: 데이터 내보내기 (CSV/PDF)
- **카테고리**: 기존 강화
- **사용자 가치**: 재고 목록이나 장보기 내역을 파일로 내보내 다른 용도로 활용
- **구현 복잡도**: S
- **현황**: JSON 백업만 존재 (`/auth/backup/export`)
- **필요 변경**:
  - 백엔드: `/stats/export` 엔드포인트 (CSV 형식), 또는 프론트엔드에서 직접 변환
  - 프론트엔드: `expo-file-system` + `expo-sharing`으로 CSV 생성/공유
  - DB: 변경 없음
- **의존성**: 없음
- **우선순위 점수**: Impact(3) × Feasibility(5) = 15

#### FD-015: 스캔 기록 조회 (히스토리)
- **카테고리**: 기존 강화
- **사용자 가치**: 과거 스캔 결과를 다시 확인하거나, 실수로 재고 추가를 안 했을 때 재시도
- **구현 복잡도**: S
- **현황**: `scans` 테이블에 모든 스캔 결과가 저장되지만, 목록 조회 API와 UI가 없음
- **필요 변경**:
  - 백엔드: `GET /scans` (디바이스별 스캔 히스토리 목록, 페이지네이션)
  - 프론트엔드: 스캔 탭 하단에 "최근 스캔" 리스트 추가
  - DB: 변경 없음 (기존 `idx_scans_device` 인덱스 활용)
- **의존성**: 없음
- **우선순위 점수**: Impact(3) × Feasibility(5) = 15

#### FD-016: 이미지 기반 요리 완성도 확인
- **카테고리**: 신규 기능 / AI 확장
- **사용자 가치**: 요리 완성 사진을 찍으면 Gemini가 완성도 평가 및 피드백 제공
- **구현 복잡도**: M
- **현황**: 관련 기능 없음
- **필요 변경**:
  - 백엔드: Gemini에 요리 완성도 평가 프롬프트 추가, `/recipes/{id}/evaluate` 엔드포인트
  - 프론트엔드: 요리 완료 후 사진 촬영 옵션 및 평가 결과 표시
  - DB: `cooking_history`에 `photo_url`, `evaluation` 추가 (선택)
- **의존성**: 없음
- **우선순위 점수**: Impact(3) × Feasibility(3) = 9

#### FD-017: 스마트 알림 설정 (알림 시간/빈도 커스터마이즈)
- **카테고리**: 기존 강화
- **사용자 가치**: 유통기한 알림 시점(D-7, D-3 등), 알림 시간대를 사용자가 직접 설정
- **구현 복잡도**: S
- **현황**: 유통기한 알림은 D-3 고정 (`admin.py`의 `check_expiring_items`), 사용자별 알림 설정 불가
- **필요 변경**:
  - 백엔드: `devices` 또는 `user_preferences` 테이블에 `notification_settings` JSONB 추가, `check_expiring_items`에서 디바이스별 threshold 참조
  - 프론트엔드: Alerts 탭에 알림 설정 모달 추가
  - DB: `devices` 테이블에 `notification_settings` 컬럼 추가
- **의존성**: 없음
- **우선순위 점수**: Impact(4) × Feasibility(4) = 16

---

## Backlog (우선순위 순)

| # | 기능 | Impact | Effort | 점수 | 카테고리 |
|---|------|--------|--------|------|----------|
| FD-001 | 다크 모드 전환 지원 | 5 | S | 25 | 강화 |
| FD-002 | 재고/레시피 검색 기능 | 5 | S | 25 | 강화 |
| FD-003 | 온보딩 화면 | 4 | S | 20 | 신규 |
| FD-004 | 스캔 후 자동 레시피 추천 연결 | 4 | S | 20 | 강화 |
| FD-005 | 레시피 개인화 (선호도/알레르기) | 5 | M | 20 | 신규 |
| FD-007 | 영양 분석 기능 | 4 | M | 16 | AI 확장 |
| FD-008 | 레시피 공유 링크 | 4 | M | 16 | 신규 |
| FD-017 | 스마트 알림 설정 | 4 | S | 16 | 강화 |
| FD-006 | 식단 계획(Meal Planning) | 5 | L | 15 | 신규 |
| FD-014 | 데이터 내보내기(CSV) | 3 | S | 15 | 강화 |
| FD-015 | 스캔 기록 조회 | 3 | S | 15 | 강화 |
| FD-010 | 게이미피케이션 | 3 | M | 12 | 신규 |
| FD-009 | 가족 재고 공유 | 5 | XL | 10 | 신규 |
| FD-011 | 음성 인식 재고 입력 | 3 | L | 9 | AI 확장 |
| FD-013 | 다중 언어 지원(i18n) | 3 | M | 9 | 강화 |
| FD-016 | 요리 완성도 AI 평가 | 3 | M | 9 | AI 확장 |
| FD-012 | 위젯/바로가기 | 3 | L | 6 | 신규 |

---

## User Journey Improvements

```
현재:  스캔 → 결과 확인 → 재고 추가 → (끊김)
제안:  스캔 → 결과 확인 → 재고 추가 → [자동 레시피 추천] → 요리 완료 → [장보기 자동 생성] → 체크아웃

현재:  홈 → 레시피 추천 보기 → (개인화 없음, 동일 추천)
제안:  [온보딩에서 선호도 입력] → 홈 → [개인화된 레시피 추천] → 요리 → [영양 분석 확인] → [성취 배지 획득]

현재:  유통기한 D-3 알림 → 앱 열기 → 재고 확인
제안:  [홈 위젯에서 임박 재료 확인] → 탭 → [자동 레시피 추천] → 요리 → 낭비 방지
```

---

## Action Items

| # | 제목 | Impact | Effort | 다음 단계 |
|---|------|--------|--------|-----------|
| FD-001 | 다크 모드 전환 | High | S | 즉시 구현 가능 – `app.json` 변경 + Colors 연결 |
| FD-002 | 검색 기능 추가 | High | S | API `search` 파라미터 추가 + 프론트엔드 SearchBar |
| FD-003 | 온보딩 화면 | High | S | 3단계 슬라이드 컴포넌트 생성 |
| FD-004 | 스캔→레시피 연결 | High | S | `scan.tsx` 성공 콜백에 CTA 추가 |
| FD-005 | 레시피 개인화 | High | M | 스키마 설계 → API → 프론트엔드 순서 |

---

## Task List (Codex 구현용)

> 아래 태스크는 Codex가 순차적으로 실행할 수 있도록 파일 경로/함수명/수정 요지/테스트 명령으로 구체화했습니다.

---

### TASK-001: 다크 모드 전환 지원 (FD-001)

| 단계 | 파일 | 수정 내용 | 테스트 |
|------|------|-----------|--------|
| 1-1 | `prometheus-app/app.json` | `"userInterfaceStyle"` 값을 `"light"`에서 `"automatic"`으로 변경 | `npx expo config --type public` 확인 |
| 1-2 | `prometheus-app/app/_layout.tsx` | `useColorScheme()` 훅 import 및 `ThemeProvider` 또는 Context로 테마 전달 | 앱 빌드 후 시스템 다크 모드 전환 시 배경색 변경 확인 |
| 1-3 | `prometheus-app/app/(tabs)/_layout.tsx` | 탭 바 색상을 `Colors[colorScheme]`에서 동적 참조하도록 수정 | 다크 모드에서 탭 바 배경색이 `#0F172A`로 변경 확인 |
| 1-4 | `prometheus-app/app/(tabs)/index.tsx` | `HomeScreen` 내 하드코딩 색상을 `Colors[colorScheme]` 참조로 교체 (배경, 텍스트, 카드 등) | 다크 모드에서 홈 화면 가독성 확인 |
| 1-5 | `prometheus-app/app/(tabs)/inventory.tsx` | 동일하게 테마 색상 적용 | 다크 모드에서 재고 목록 표시 확인 |
| 1-6 | `prometheus-app/app/(tabs)/scan.tsx` | 카메라 뷰 외 영역의 테마 색상 적용 | 다크 모드에서 스캔 화면 확인 |
| 1-7 | `prometheus-app/app/(tabs)/shopping.tsx` | 테마 색상 적용 | 다크 모드에서 장보기 화면 확인 |
| 1-8 | `prometheus-app/app/(tabs)/alerts.tsx` | 테마 색상 적용 | 다크 모드에서 알림 화면 확인 |
| 1-9 | `prometheus-app/app/(tabs)/history.tsx` | 테마 색상 적용 | 다크 모드에서 요리 기록 화면 확인 |
| 1-10 | `prometheus-app/components/RecipeCardStack.tsx` | `Colors[colorScheme]` 참조로 카드 색상 변경 | 다크 모드에서 레시피 카드 가독성 확인 |
| 1-11 | `prometheus-app/components/InventoryItemCard.tsx` | 동일 적용 | 다크 모드에서 재고 카드 확인 |

**커밋 메시지**: `feat(app): FD-001 enable dark mode toggle with system preference`

---

### TASK-002: 재고/레시피 검색 기능 추가 (FD-002)

| 단계 | 파일 | 수정 내용 | 테스트 |
|------|------|-----------|--------|
| 2-1 | `prometheus-api/app/api/inventory.py` :: `get_inventory()` | `search: Optional[str] = Query(None)` 파라미터 추가, `if search: query = query.ilike("name", f"%{search}%")` | `curl -H "X-Device-ID: test" -H "X-App-Token: ..." "localhost:8000/inventory?search=우유"` |
| 2-2 | `prometheus-api/app/api/recipes.py` :: `get_favorite_recipes()` | `search: Optional[str] = Query(None)` 파라미터 추가, `.ilike("title", f"%{search}%")` 조건 추가 | `curl "localhost:8000/recipes/favorites?search=볶음"` |
| 2-3 | `prometheus-app/services/api.ts` :: `ApiClient.getInventory()` | `search?: string` 파라미터 추가, 쿼리스트링에 `search` 포함 | TypeScript 컴파일 확인 |
| 2-4 | `prometheus-app/services/api.ts` :: `ApiClient.getFavoriteRecipes()` | `search?: string` 파라미터 추가 | TypeScript 컴파일 확인 |
| 2-5 | `prometheus-app/app/(tabs)/inventory.tsx` :: `InventoryScreen` | 검색바 `<TextInput>` 추가 (상단), `searchQuery` state 추가, `useMemo` 또는 API 호출 시 search 전달 (디바운스 300ms) | 검색어 입력 후 목록 필터링 동작 확인 |
| 2-6 | `prometheus-app/app/(tabs)/index.tsx` :: `HomeScreen` | 즐겨찾기 모드에서 검색바 추가 | 즐겨찾기 내 검색 동작 확인 |

**커밋 메시지**: `feat(api,app): FD-002 add search functionality for inventory and favorites`

---

### TASK-003: 온보딩 화면 (FD-003)

| 단계 | 파일 | 수정 내용 | 테스트 |
|------|------|-----------|--------|
| 3-1 | `prometheus-app/components/OnboardingSlide.tsx` [NEW] | 3단계 슬라이드 컴포넌트: ① "스캔으로 재료 등록" ② "AI 레시피 추천" ③ "유통기한 관리" | 컴포넌트 렌더링 확인 |
| 3-2 | `prometheus-app/app/(onboarding)/index.tsx` [NEW] | 온보딩 화면: 슬라이드 3개 + "시작하기" 버튼, `AsyncStorage.setItem('onboarding_completed', 'true')` 후 `/(tabs)` 라우팅 | 최초 실행 시 온보딩 표시, 이후 미표시 확인 |
| 3-3 | `prometheus-app/app/_layout.tsx` | 앱 시작 시 `AsyncStorage.getItem('onboarding_completed')` 확인, 미완료 시 `/(onboarding)` 라우팅 | 앱 재시작 후 온보딩 스킵 확인 |

**커밋 메시지**: `feat(app): FD-003 add 3-step onboarding flow for new users`

---

### TASK-004: 스캔→레시피 추천 자동 연결 (FD-004)

| 단계 | 파일 | 수정 내용 | 테스트 |
|------|------|-----------|--------|
| 4-1 | `prometheus-app/app/(tabs)/scan.tsx` :: `ScanScreen.addToInventory()` | 성공 Alert에 "레시피 추천 보기" 버튼 추가, `router.push('/(tabs)')` 또는 추천 모달 표시 | 스캔→재고 추가 후 "레시피 추천 보기" 버튼 클릭 시 홈 탭 이동 확인 |
| 4-2 | `prometheus-app/app/(tabs)/index.tsx` :: `HomeScreen` | 외부에서 `forceRefresh` 파라미터 수신 시 자동 새로고침 | 스캔 후 홈 이동 시 최신 추천 표시 확인 |

**커밋 메시지**: `feat(app): FD-004 link scan completion to recipe recommendations`

---

### TASK-005: 레시피 개인화 – 선호도/알레르기 (FD-005)

| 단계 | 파일 | 수정 내용 | 테스트 |
|------|------|-----------|--------|
| 5-1 | `prometheus-api/schema.sql` | `user_preferences` 테이블 추가: `device_id VARCHAR(255) UNIQUE NOT NULL, allergies JSONB DEFAULT '[]', dietary_restrictions JSONB DEFAULT '[]', skill_level VARCHAR(20) DEFAULT 'beginner', preferred_cuisines JSONB DEFAULT '[]', disliked_ingredients JSONB DEFAULT '[]'` | `psql` 또는 Supabase에서 테이블 생성 확인 |
| 5-2 | `prometheus-api/app/schemas/schemas.py` | `UserPreferences`, `UserPreferencesRequest`, `UserPreferencesResponse` 모델 추가 | Python import 확인 |
| 5-3 | `prometheus-api/app/api/preferences.py` [NEW] | `GET/PUT /preferences` 엔드포인트: device_id 기반 CRUD | `curl -X PUT "localhost:8000/preferences" -d '{"allergies":["견과류"]}'` |
| 5-4 | `prometheus-api/app/main.py` | `from .api.preferences import router as preferences_router` 추가, `app.include_router(preferences_router)` | 서버 시작 확인 |
| 5-5 | `prometheus-api/app/services/gemini_service.py` :: `generate_recipe_recommendations()` | 프롬프트에 `"User allergies: {allergies}, dietary: {dietary}, skill_level: {skill_level}"` 주입, `allergies`/`dietary` 파라미터 추가 | 알레르기 재료가 추천 결과에서 제외되는지 확인 |
| 5-6 | `prometheus-api/app/api/recipes.py` :: `get_recommendations()` | DB에서 `user_preferences` 조회 후 `gemini.generate_recipe_recommendations()`에 전달 | 선호도 설정 후 추천 결과 변화 확인 |
| 5-7 | `prometheus-app/services/api.ts` | `getPreferences()`, `updatePreferences()` 메서드 추가 | TypeScript 컴파일 확인 |
| 5-8 | `prometheus-app/services/api.types.ts` | `UserPreferences` 타입 추가 | TypeScript 컴파일 확인 |
| 5-9 | `prometheus-app/app/(tabs)/alerts.tsx` 또는 새 설정 화면 | 선호도 입력 UI: 알레르기 태그 입력, 식이제한 체크박스, 요리 실력 슬라이더 | 설정 저장 후 API 반영 확인 |

**커밋 메시지**: `feat(api,app): FD-005 add user preferences for personalized recipe recommendations`

---

### TASK-006: 스마트 알림 설정 (FD-017)

| 단계 | 파일 | 수정 내용 | 테스트 |
|------|------|-----------|--------|
| 6-1 | `prometheus-api/schema.sql` | `devices` 테이블에 `notification_settings JSONB DEFAULT '{"expiry_threshold_days": 3, "notify_time": "09:00"}'` 컬럼 추가 | SQL 실행 확인 |
| 6-2 | `prometheus-api/app/schemas/schemas.py` | `NotificationSettings` 모델 추가, `DeviceRegisterRequest`에 `notification_settings` 필드 추가 | Python import 확인 |
| 6-3 | `prometheus-api/app/api/admin.py` :: `check_expiring_items()` | 디바이스별 `notification_settings.expiry_threshold_days` 읽어서, D-day 계산 시 사용 | 다른 threshold 설정 후 알림 발송 확인 |
| 6-4 | `prometheus-app/app/(tabs)/alerts.tsx` | 알림 설정 모달 추가: 유통기한 알림 일수 슬라이더(1~7일), 알림 시간 선택 | 설정 변경 후 디바이스 재등록 확인 |

**커밋 메시지**: `feat(api,app): FD-017 add customizable notification settings`

---

### TASK-007: 스캔 기록 조회 (FD-015)

| 단계 | 파일 | 수정 내용 | 테스트 |
|------|------|-----------|--------|
| 7-1 | `prometheus-api/app/api/scans.py` | `GET /scans` 엔드포인트 추가: `db.table("scans").select("id,source_type,status,original_filename,created_at", count="exact").eq("device_id", device_id).order("created_at", desc=True).range(offset, offset+limit-1)` | `curl "localhost:8000/scans?limit=10"` |
| 7-2 | `prometheus-api/app/schemas/schemas.py` | `ScanHistoryItem`, `ScanHistoryResponse` 모델 추가 | Python import 확인 |
| 7-3 | `prometheus-app/services/api.ts` | `getScanHistory(limit, offset)` 메서드 추가 | TypeScript 컴파일 확인 |
| 7-4 | `prometheus-app/app/(tabs)/scan.tsx` | 초기 상태(카메라 대기 화면) 하단에 "최근 스캔" 목록 표시, 항목 탭 시 결과 재조회 | 스캔 후 목록에 새 항목 표시 확인 |

**커밋 메시지**: `feat(api,app): FD-015 add scan history viewing`

---

### TASK-008: 데이터 내보내기 CSV (FD-014)

| 단계 | 파일 | 수정 내용 | 테스트 |
|------|------|-----------|--------|
| 8-1 | `prometheus-app/utils/csv-export.ts` [NEW] | 재고/장보기 데이터를 CSV 문자열로 변환하는 유틸 함수 `inventoryToCsv(items)`, `shoppingToCsv(items)` | 단위 테스트(Jest) |
| 8-2 | `prometheus-app/app/(tabs)/inventory.tsx` | 설정/더보기 메뉴에 "CSV 내보내기" 버튼 추가, `FileSystem.writeAsStringAsync` + `Sharing.shareAsync` | 내보낸 CSV 파일이 올바른 형식인지 확인 |
| 8-3 | `prometheus-app/app/(tabs)/shopping.tsx` | 동일하게 "CSV 내보내기" 버튼 추가 | CSV 내보내기 동작 확인 |

**커밋 메시지**: `feat(app): FD-014 add CSV export for inventory and shopping`

---

### TASK-009: 영양 분석 기능 (FD-007)

| 단계 | 파일 | 수정 내용 | 테스트 |
|------|------|-----------|--------|
| 9-1 | `prometheus-api/app/schemas/schemas.py` :: `Recipe` | `nutrition: Optional[dict] = None` 필드 추가 (calories, protein, carbs, fat 등) | Python import 확인 |
| 9-2 | `prometheus-api/app/services/gemini_service.py` :: `generate_recipe_recommendations()` | 프롬프트에 `"nutrition": {"calories": N, "protein_g": N, "carbs_g": N, "fat_g": N}` 요청 추가 | 추천 결과에 영양 정보 포함 확인 |
| 9-3 | `prometheus-app/services/api.types.ts` | `NutritionInfo` 타입 추가, `ApiRecipe`에 `nutrition` 필드 추가 | TypeScript 컴파일 확인 |
| 9-4 | `prometheus-app/app/(tabs)/index.tsx` :: 레시피 상세 모달 | 영양 정보 카드 UI 추가 (칼로리, 단백질, 탄수화물, 지방 원형 차트 또는 바) | 레시피 상세에서 영양 정보 표시 확인 |

**커밋 메시지**: `feat(api,app): FD-007 add nutrition analysis to recipe recommendations`

---

### TASK-010: 게이미피케이션 – 요리 연속 기록 (FD-010)

| 단계 | 파일 | 수정 내용 | 테스트 |
|------|------|-----------|--------|
| 10-1 | `prometheus-api/app/api/stats.py` | `GET /stats/achievements` 엔드포인트 추가: 연속 요리 일수(streak), 총 요리 횟수, 이번 주 요리 횟수, 절약 추정 금액 계산 | `curl "localhost:8000/stats/achievements?period=month"` |
| 10-2 | `prometheus-api/app/schemas/schemas.py` | `AchievementsResponse` 모델 추가: `streak_days`, `total_recipes_cooked`, `estimated_savings`, `badges` | Python import 확인 |
| 10-3 | `prometheus-app/services/api.ts` | `getAchievements()` 메서드 추가 | TypeScript 컴파일 확인 |
| 10-4 | `prometheus-app/app/(tabs)/history.tsx` | 상단에 성취 요약 카드 추가: 🔥 연속 N일, 절약 금액, 배지 | 요리 기록 화면 상단에 스트릭 표시 확인 |

**커밋 메시지**: `feat(api,app): FD-010 add gamification achievements and cooking streak`

---

### 우선순위별 실행 순서 권장

```
Phase 1 (Quick Wins – 1~2주):
  TASK-001 → TASK-002 → TASK-003 → TASK-004

Phase 2 (핵심 가치 – 2~3주):
  TASK-005 → TASK-006 → TASK-007 → TASK-008

Phase 3 (차별화 – 3~4주):
  TASK-009 → TASK-010
```
