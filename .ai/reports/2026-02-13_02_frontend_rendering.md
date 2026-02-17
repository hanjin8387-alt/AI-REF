# Frontend Rendering Report – 2026-02-13

## Baseline & Measurement
| 지표 | 현재 (추정) | 목표 | 측정 방법 |
|------|-----------|------|----------|
| 재고 목록 FPS | 45-55fps | ≥58fps | React DevTools Profiler |
| 리렌더 횟수/초 | 미측정 | ≤5 | Profiler commit count |
| 레시피 카드 렌더 | ~50ms/item | ≤30ms | Profiler |

## Findings

### 🔴 Critical

#### FR-001: FlatList 최적화 props 미적용
- **파일**: `prometheus-app/app/(tabs)/inventory.tsx`, 기타 탭 화면
- **유형**: 실제 성능
- **근거**: `getItemLayout`, `windowSize`, `maxToRenderPerBatch`, `removeClippedSubviews` 미설정
- **영향**: 아이템 50+ 시 스크롤 버벅임, 프레임 드롭
- **권장 조치**: FlatList에 최적화 props 적용 (아이템 높이 고정 시 `getItemLayout` 제공)
- **예상 영향**: FPS +15~20%

### 🟡 Warning

#### FR-002: 렌더 함수 내 인라인 함수/객체 생성
- **파일**: 탭 화면 전반
- **유형**: 실제 성능
- **근거**: `renderItem`에서 인라인 `() => handlePress(item.id)`, 인라인 스타일 `{ backgroundColor: ... }` 패턴. 매 렌더마다 새 참조 생성 → PureComponent/React.memo 무효화.
- **권장 조치**: `useCallback`으로 핸들러 메모이제이션, StyleSheet.create로 스타일 분리
- **예상 영향**: 리렌더 -30%

#### FR-003: InventoryItemCard에 React.memo 미적용
- **파일**: `prometheus-app/components/InventoryItemCard.tsx`
- **유형**: 실제 성능
- **근거**: 리스트 아이템 컴포넌트가 React.memo로 래핑되지 않음. 부모 리렌더 시 모든 아이템 리렌더.
- **권장 조치**: `React.memo()` 래핑 + propsAreEqual 커스텀 비교
- **예상 영향**: 스크롤 시 리렌더 -50%

#### FR-004: RecipeCardStack에 React.memo 미적용
- **파일**: `prometheus-app/components/RecipeCardStack.tsx`
- **유형**: 실제 성능
- **근거**: FR-003과 동일 패턴
- **권장 조치**: React.memo 래핑

#### FR-005: 대량 JSON.parse on main thread
- **파일**: `prometheus-app/services/offline-cache.ts`
- **유형**: 실제 성능
- **근거**: `JSON.parse(raw)` — 오프라인 캐시에서 대량 재고/장보기 데이터 복원 시 메인 스레드 차단 가능
- **권장 조치**: 데이터 크기 모니터링, 극단적 경우 Web Worker 사용 검토 (Expo 제한)

### 🟢 Info

#### FR-006: 이미지 컴포넌트에 placeholder/fade-in 미적용
- **유형**: 체감속도
- **근거**: expo-image 사용 시 placeholder + transition props 미활용
- **권장 조치**: `placeholder` + `transition={{ duration: 200 }}` 적용

## Recommendations

### 실제 성능
1. FlatList에 `getItemLayout`, `windowSize={5}`, `maxToRenderPerBatch={10}` 적용
2. 리스트 아이템 컴포넌트 `React.memo()` 래핑
3. 인라인 함수 → `useCallback`, 인라인 스타일 → StyleSheet

### 체감속도
1. 이미지 로딩 시 placeholder + fade-in 트랜지션
2. 리스트 초기 렌더 시 `initialNumToRender={10}` 제한

## Task List
| # | 파일 | 변경요지 | 벤치 커맨드 | 테스트 커맨드 | 수용기준 | 예상 영향 | 위험도 |
|---|------|---------|-----------|-------------|---------|----------|--------|
| 1 | 탭 화면 FlatList | 최적화 props 적용 | Profiler 녹화 | `npm test` | getItemLayout 존재 | FPS +15% | 🔴 |
| 2 | `InventoryItemCard.tsx` | React.memo 래핑 | Profiler 녹화 | `npm test` | 불필요 리렌더 감소 | 리렌더 -50% | 🟡 |
| 3 | `RecipeCardStack.tsx` | React.memo 래핑 | Profiler 녹화 | `npm test` | 리렌더 감소 | 리렌더 -50% | 🟡 |
| 4 | 탭 화면 | 인라인 함수 → useCallback | Profiler | `npm test` | 인라인 함수 0건 | 리렌더 -30% | 🟡 |
| 5 | 이미지 컴포넌트 | placeholder + transition | 수동 체감 | `npm test` | 이미지 fade-in | 체감 향상 | 🟢 |

## Risk & Rollback
- React.memo 추가는 기능 무관. 잘못된 비교 함수 시 UI 미갱신 → 기본 shallow compare 우선.
- FlatList props는 시각적 변화 없음. 안전.
