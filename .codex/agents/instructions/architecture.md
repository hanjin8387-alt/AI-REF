# Architecture 점검 지침

## 개요
PROMETHEUS의 소프트웨어 아키텍처를 분석하여 설계 결함을 탐지합니다.

## 현재 아키텍처 구조

### 백엔드 계층
```
app/
├── api/         # 프레젠테이션 계층 (FastAPI 라우터)
├── core/        # 횡단 관심사 (설정, DB, 보안)
├── services/    # 비즈니스 로직 계층
└── schemas/     # 데이터 전송 객체 (Pydantic)
```

### 의존성 규칙 (이상적)
```
api → services → core
api → schemas
services → schemas
```

### 프론트엔드 계층
```
prometheus-app/
├── app/(tabs)/    # 화면 (프레젠테이션)
├── components/    # 재사용 UI 컴포넌트
├── services/      # API 통신 + 캐시
├── constants/     # 상수 정의
└── utils/         # 유틸리티 함수
```

## 점검 포인트

### 계층 위반 탐지
- `api/*.py`에서 Supabase 쿼리를 **직접** 실행하는 경우 → 서비스 계층으로 이동 필요
- `services/*.py`에서 `HTTPException`을 **발생**시키는 경우 → 커스텀 예외로 변환
- 프론트엔드 탭 컴포넌트에서 직접 HTTP 호출 (api.ts 우회) → api 서비스로 이동

### 순환 의존성 탐지
- 두 모듈이 서로를 import하는 경우
- 서비스가 다른 서비스를 직접 import하여 호출하는 경우

### API 설계 일관성
- REST 규칙: GET 조회, POST 생성, PATCH 수정, DELETE 삭제
- 응답 형식: 모든 엔드포인트가 동일한 응답 래핑 형식 사용
- 상태 코드: 200/201/204/400/401/404/500

### 프론트엔드-백엔드 계약
- `api.types.ts`의 타입이 `schemas.py`의 Pydantic 모델과 일치하는지
- 필드명 불일치 (camelCase vs snake_case 변환)
- 응답 필드 누락 또는 불일치
