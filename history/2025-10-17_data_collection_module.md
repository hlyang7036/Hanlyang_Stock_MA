# 데이터 수집 모듈 구현

## 날짜
2025-10-17

## 작업 내용

### 1. HantuStock.py 확장 기능 추가
- **신규 메서드 구현**
  - `get_current_price()`: 한국투자증권 API를 통한 실시간 현재가 조회
  - `get_past_data_by_date()`: 날짜 범위 지정 과거 데이터 조회
  - `get_market_data_by_date()`: 특정 날짜의 전체 시장 데이터 조회
  - `_get_past_data_by_date_fallback()`: pykrx를 사용한 대체 조회
  - `_standardize_pykrx_data()`: pykrx 데이터 표준화

- **주요 특징**
  - 한국투자증권 API 우선 사용, 실패시 pykrx로 폴백
  - 실시간 데이터 지원으로 strategy 모듈 요구사항 충족
  - 날짜 지정 조회로 백테스트 지원

### 2. 데이터 수집 모듈 (DataCollector) 구현
- **위치**: `src/analysis/data/data_collector.py`

- **주요 기능**
  1. **실시간 데이터 조회**
     - `get_realtime_data()`: 개별 종목 실시간 데이터
     - `get_realtime_data_bulk()`: 여러 종목 일괄 조회
  
  2. **과거 데이터 조회**
     - `get_historical_data()`: 유연한 인터페이스 (날짜/기간 선택)
     - `get_historical_data_for_backtest()`: 백테스트 전용 (특정일 기준)
  
  3. **시장 데이터 조회**
     - `get_market_data()`: 전체 시장 데이터
     - `get_market_data_range()`: 날짜 범위 시장 데이터
  
  4. **계좌 정보 조회**
     - `get_account_info()`: 현금 잔고 및 보유 종목

- **설계 특징**
  - 싱글톤 패턴으로 인스턴스 관리
  - 메모리 캐싱으로 반복 조회 성능 향상
  - 데이터 표준화로 일관된 형식 제공
  - HantuStock 인스턴스 지연 초기화

### 3. 테스트 코드 작성
- **test_hantu_api_extended.py**
  - HantuStock 확장 기능 테스트
  - 실시간 현재가, 날짜별 조회 등
  
- **test_data_collector.py**
  - DataCollector 모듈 전체 테스트
  - 캐시 기능, 데이터 일관성 등

### 4. 프로젝트 구조 업데이트
```
src/
├── analysis/
│   ├── data/                    # 신규 생성
│   │   ├── __init__.py
│   │   └── data_collector.py    # 데이터 수집 모듈
│   └── technical/
├── tests/
│   ├── test_hantu_api.py
│   ├── test_hantu_api_extended.py    # 신규
│   └── test_data_collector.py        # 신규
└── utils/
    └── koreainvestment/
        └── HantuStock.py        # 확장됨
```

## 이슈

### 이슈 1: API 선택
- **문제**: HantuStock.py만으로 데이터 수집 모듈 구현 가능 여부
- **분석**: 실시간 데이터, 날짜 지정 조회 등 핵심 기능 누락
- **해결**: HantuStock.py에 필요 메서드 추가 (방안1 채택)

### 이슈 2: 데이터 소스 통합
- **문제**: 한투 API, pykrx, FinanceDataReader 등 다양한 소스
- **해결**: 한투 API 우선, 실패시 pykrx 폴백 메커니즘 구현

### 이슈 3: 백테스트 vs 실거래 요구사항
- **문제**: 백테스트는 과거 특정 시점, 실거래는 실시간 데이터 필요
- **해결**: 유연한 인터페이스로 두 경우 모두 지원

## 참고 사항

### 기존 코드 호환성
- 기존 `get_past_data`, `get_past_data_total` 메서드는 수정하지 않음
- 기존 테스트 코드에 영향 없음
- 신규 기능은 별도 메서드로 추가

### 성능 최적화
- 메모리 캐시로 반복 조회 최소화
- 캐시 크기 제한 (100개)으로 메모리 관리
- 지연 초기화로 불필요한 API 연결 방지

### 확장 가능성
- DataCollector는 추상화된 인터페이스 제공
- 새로운 데이터 소스 추가 용이
- strategy/backtest 모듈에서 동일하게 사용 가능

## 다음 단계
1. 기술적 지표 계산 모듈 구현 (이동평균선, MACD, ATR)
2. 스테이지 판단 모듈 구현
3. 실제 테스트 실행 및 검증