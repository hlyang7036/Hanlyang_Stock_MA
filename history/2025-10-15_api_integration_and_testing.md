# 한국투자증권 API 연동 및 테스트 환경 구축

## 날짜
2025-10-15

## 작업 내용

### 1. 한국투자증권 API 클래스 개선
- **HantuStock.py 리팩토링**
  - Slack 클래스 및 AI 캐시 관련 코드 제거
  - 코드 구조 정리 (섹션별 주석 추가)
  - 모든 메서드에 상세한 docstring 추가
  - 실거래/모의투자 모드 자동 전환 기능 유지

### 2. 보안 강화 - 환경변수 기반 설정 관리
- **.env 파일 생성**
  - API Key, Secret Key 등 중요 정보를 환경변수로 관리
  - `.gitignore`에 등록하여 Git 업로드 방지
  
- **.env.example 템플릿 생성**
  - 새로운 환경에서 설정 가능하도록 템플릿 제공
  
- **config_loader.py 구현**
  - YAML 파일의 환경변수 참조 자동 치환
  - 싱글톤 패턴으로 설정 로더 구현
  - `get_api_credentials()` 간편 함수 제공
  
- **config.yaml 수정**
  - 실제 값 대신 `${ENV_VAR}` 형태로 환경변수 참조

### 3. 테스트 환경 구축
- **테스트 패키지 생성** (`src/tests/`)
  - `conftest.py`: pytest fixtures 정의
    - `api_credentials`: API 인증 정보
    - `hantu_api`: HantuStock 인스턴스 (세션 스코프)
    - `test_ticker`: 테스트용 종목 코드
  
- **test_hantu_api.py 작성**
  - `TestHantuAPIConnection`: API 연결 및 인증 테스트
  - `TestHantuAPIMarketData`: 시장 데이터 조회 테스트
  - `TestHantuAPIAccount`: 계좌 정보 조회 테스트
  - `TestHantuAPIOrder`: 주문 기능 테스트 (기본 skip)
  - `TestHantuAPIIntegration`: 통합 테스트
  
- **테스트 문서 작성**
  - `tests/README.md`: 테스트 가이드 및 사용법

### 4. 토큰 캐싱 로직 구현
- **문제점 발견**
  - 10초 이내 중복 토큰 발급으로 API 제한 발생
  - 테스트 시 불필요한 대기 시간 발생 (60초+)

- **해결 방법**
  - 토큰 캐싱 메커니즘 추가
  - 토큰 발급 시간 추적 (`_token_issued_at`)
  - 24시간 유효기간 중 23시간까지 재사용
  - `get_token_info()` 메서드로 토큰 상태 확인 가능
  - `force_refresh` 옵션으로 강제 갱신 가능

- **효과**
  - 불필요한 토큰 재발급 제거
  - 테스트 실행 시간 60초+ → 1초 이내로 단축
  - API 호출 제한 회피

### 5. 의존성 관리
- **requirements.txt 생성**
  - 프로젝트 필수 패키지 목록화
  - pandas, requests, pykrx, FinanceDataReader 등
  - pytest, pytest-cov, pytest-mock (테스트용)
  - setuptools (pykrx 의존성)

## 이슈 및 해결

### 이슈 1: pkg_resources 모듈 없음
- **문제**: `ModuleNotFoundError: No module named 'pkg_resources'`
- **원인**: Python 3.12에서 setuptools가 기본 포함되지 않음
- **해결**: `uv pip install setuptools`로 해결

### 이슈 2: 접근 토큰 중복 발급
- **문제**: 10초 이내 토큰 재발급으로 API 제한 걸림
- **원인**: 
  - `__init__`에서 토큰 발급
  - `test_get_access_token`에서 다시 토큰 발급
- **해결**: 
  - 토큰 캐싱 로직 구현
  - 유효한 토큰 재사용으로 불필요한 발급 방지

### 이슈 3: 중요 정보 노출 위험
- **문제**: config.yaml에 API 키가 평문으로 저장
- **원인**: 설정 파일을 Git에 직접 커밋할 경우 키 노출
- **해결**:
  - .env 파일로 중요 정보 분리
  - config_loader로 환경변수 자동 치환
  - .env.example로 템플릿 제공

## 파일 구조

```
src/
├── config/
│   ├── __init__.py
│   ├── config.yaml              # 환경변수 참조
│   └── config_loader.py         # 설정 로더
├── tests/
│   ├── __init__.py
│   ├── README.md                # 테스트 가이드
│   ├── conftest.py              # pytest fixtures
│   └── test_hantu_api.py        # API 테스트
└── utils/
    └── koreainvestment/
        └── HantuStock.py        # 개선된 API 클래스

.env                              # 중요 정보 (Git 제외)
.env.example                      # 설정 템플릿
requirements.txt                  # 의존성 목록
```

## 테스트 실행 결과

```bash
# 전체 테스트 실행
pytest src/tests/test_hantu_api.py -v

# 결과
🟢 모의투자 모드로 초기화됩니다.
✅ API 초기화 성공
✅ 토큰 캐싱 작동 확인
✅ 토큰 정보 조회 성공
✅ 보유 현금 조회 성공
✅ 전체 보유 주식 조회 성공
✅ 모든 통합 테스트 통과!
```

## 다음 단계

### 1. 기술적 지표 구현
- 이동평균선 계산 모듈 (`src/analysis/technical/`)
- MACD 계산 모듈
- ATR 계산 모듈

### 2. 6단계 대순환 분석 로직
- 스테이지 판단 로직 구현
- MACD 기반 스테이지 전환 감지

### 3. 매매 전략 구현
- 진입 신호 생성
- 청산 신호 생성 (3단계)
- 포지션 사이징 (유닛 기반)

### 4. 백테스팅 엔진
- 과거 데이터 기반 전략 검증
- 성과 분석 및 리포팅

## 참고 사항

- 모든 테스트는 모의투자 계정으로 실행
- 주문 테스트는 기본적으로 skip 처리 (실제 주문 발생 방지)
- 토큰은 24시간 유효하며, 23시간까지 자동 재사용
- API 호출 제한: 10초당 1회 (토큰 발급), 초당 N회 (일반 API)
