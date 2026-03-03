# Dead Code 점검 지침

## 개요
이 에이전트는 PROMETHEUS 코드베이스에서 **불필요한 코드**를 탐지합니다.

## 스캔 전략

### Phase 1: Import 분석
```
각 파일의 import 문을 추출하고, 해당 파일 내에서 import된 이름이
실제로 참조되는지 확인합니다.
```

### Phase 2: 함수/변수 사용 추적
```
정의된 함수, 변수, 클래스를 추출하고,
프로젝트 전체에서 해당 이름이 참조되는지 확인합니다.
```

### Phase 3: 반환값 추적
```
함수 호출의 반환값이 변수에 할당되거나 다른 표현식에서 사용되는지 확인합니다.
Statement 레벨에서 호출만 되고 반환값이 버려지는 경우를 탐지합니다.
```

### Phase 4: 도달 불가 코드
```
return, raise, break, continue 이후의 코드를 탐지합니다.
조건문에서 항상 참/거짓인 분기를 탐지합니다.
```

## 프로젝트별 주요 점검 파일

### 백엔드 (`prometheus-api/`)
| 파일 | 주요 점검 포인트 |
|------|-----------------|
| `app/schemas/schemas.py` | 미사용 Pydantic 모델/필드 |
| `app/services/*.py` | 미사용 헬퍼 함수 |
| `app/api/*.py` | 미호출 엔드포인트, 미사용 import |
| `app/core/*.py` | 미사용 설정값 |

### 프론트엔드 (`prometheus-app/`)
| 파일 | 주요 점검 포인트 |
|------|-----------------|
| `services/api.ts` | 미호출 API 함수 |
| `services/api.types.ts` | 미사용 타입 정의 |
| `app/(tabs)/*.tsx` | 미사용 state, 미사용 StyleSheet 항목 |
| `constants/Colors.ts` | 미참조 색상 상수 |

## 오탐 방지 규칙
1. `export` 된 항목은 외부에서 사용될 수 있으므로 "확인 필요"로 분류
2. `useEffect` 클린업 함수는 미사용으로 분류하지 않음
3. `console.log`, `logger.*` 등 사이드이펙트 호출은 비사용으로 분류하지 않음
4. 테스트 파일에서만 사용되는 유틸은 정상으로 분류
5. `_` 접두사 변수는 의도적 미사용으로 허용
