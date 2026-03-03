# Performance 점검 지침

## 개요
PROMETHEUS의 백엔드/프론트엔드 전체에서 성능 병목과 메모리 낭비를 탐지합니다.

## 백엔드 안티패턴

### 캐시 관련
| 패턴 | 위험도 | 탐지 방법 |
|------|--------|----------|
| `dict` 캐시에 eviction 정책 없음 | High | `dict()` 또는 `{}` 할당 후 `del`/pop 없는지 확인 |
| Redis 연결 실패 시 무한 재시도 | Medium | try/except 내 재귀/루프 확인 |
| 캐시 키 해시 충돌 | Low | 키 생성 알고리즘 확인 |

### 쿼리 관련
| 패턴 | 위험도 | 탐지 방법 |
|------|--------|----------|
| SELECT * 전체 행 조회 | High | `.select("*")` 패턴 탐색 |
| 루프 내 개별 쿼리 | High | for/while 내 `.execute()` 호출 |
| 페이지네이션 없는 대량 조회 | Medium | `.range()` 없는 `.select()` |

### API 관련
| 패턴 | 위험도 | 탐지 방법 |
|------|--------|----------|
| 동기 블로킹 호출 in async | High | async 함수 내 `time.sleep`, 동기 I/O |
| AI API 불필요한 반복 호출 | High | 동일 입력에 대한 캐시 미스 |

## 프론트엔드 안티패턴

### 렌더링 관련
| 패턴 | 위험도 | 탐지 방법 |
|------|--------|----------|
| `useFocusEffect` 내 전체 데이터 재요청 | High | 변경 없는 데이터도 매번 fetch |
| 인라인 객체/함수 생성 (매 렌더) | Medium | JSX 내 `{}` 리터럴, `() =>` 콜백 |
| `useMemo`/`useCallback` 누락 | Medium | 의존성이 큰 계산에 메모이제이션 없음 |

### 메모리 관련
| 패턴 | 위험도 | 탐지 방법 |
|------|--------|----------|
| `Map` 캐시 무한 성장 | High | `.set()` 있고 `.delete()` 없는 Map |
| 이벤트 리스너 클린업 누락 | Medium | `addEventListener` 후 `removeEventListener` 없음 |
| 타이머 클린업 누락 | Medium | `setInterval`/`setTimeout` 후 `clear*` 없음 |
