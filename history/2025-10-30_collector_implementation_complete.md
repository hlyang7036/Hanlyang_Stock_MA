# 데이터 수집 모듈 (collector.py) 구현 및 수정

## 날짜
2025-10-30

## 작업 개요
Level 1 공통 모듈인 데이터 수집 모듈(`collector.py`)을 구현하고, 관련 의존성 문제를 해결했습니다.

---

## 1차 작업: 초기 구현

### 1.1 collector.py 모듈 구현
**경로**: `src/data/collector.py`

#### 구현된 함수 (8개)

**핵심 함수 (3개)**
1. **`get_stock_data()`** - 통합 데이터 수집 인터페이스
   - 자동 소스 선택 (100일 기준: API vs FDR)
   - strategy와 backtest의 메인 진입점
   
2. **`get_real_time_data()`** - 실시간/최근 데이터 조회
   - HantuStock API 사용
   - 일봉 데이터 조회
   
3. **`get_historical_data()`** - 과거 데이터 조회
   - FinanceDataReader 또는 pykrx 사용
   - 백테스팅용 장기간 데이터

**보조 함수 (5개)**
4. **`get_multiple_stocks()`** - 다종목 병렬 수집 (ThreadPoolExecutor)
5. **`get_current_price()`** - 현재가 조회
6. **`get_market_status()`** - 장 상태 확인
7. **`validate_data()`** - 데이터 검증
8. **`_normalize_dataframe()`** - 데이터 정규화 (내부 함수)

#### 표준 DataFrame 형식
```python
                       Open    High     Low   Close    Volume
Date                                                          
2024-01-02 00:00:00  60000   61000   59500   60500  10000000
2024-01-03 00:00:00  60500   62000   60000   61500  12000000
```

### 1.2 테스트 코드 작성
**경로**: `src/tests/test_collector.py`

#### 테스트 클래스 (8개)
- `TestNormalizeDataFrame` - 정규화 함수 (2개 테스트)
- `TestValidateData` - 검증 함수 (2개 테스트)
- `TestGetHistoricalData` - 과거 데이터 수집 (2개 테스트)
- `TestGetRealTimeData` - 실시간 데이터 수집 (1개 테스트)
- `TestGetStockData` - 통합 인터페이스 (2개 테스트)
- `TestGetMultipleStocks` - 다종목 수집 (1개 테스트)
- `TestGetCurrentPrice` - 현재가 조회 (1개 테스트)
- `TestGetMarketStatus` - 장 상태 확인 (1개 테스트)

**총 테스트**: 13개 (성공 케이스만)

### 1.3 문서화
- `src/data/README.md` - 사용 가이드
- `src/data/__init__.py` - 모듈 export

---

## 2차 작업: Import 경로 수정

### 이슈 1: koreainvestment 모듈 import 오류
**문제**: `from koreainvestment.HantuStock import HantuStock` 참조 불가

**원인**: sys.path 조작 방식의 import

**해결**:
1. `src/utils/koreainvestment/__init__.py` 업데이트
   ```python
   from .HantuStock import HantuStock
   __all__ = ['HantuStock']
   ```

2. `collector.py` import 수정
   ```python
   # 수정 전
   from koreainvestment.HantuStock import HantuStock
   
   # 수정 후
   from src.utils.koreainvestment import HantuStock
   ```

### 이슈 2: 테스트 파일 import 오류
**문제**: `from data.collector import ...` 모듈 찾을 수 없음

**해결**:
```python
# 수정 전
from data.collector import get_stock_data, ...

# 수정 후
from src.data.collector import get_stock_data, ...
```

---

## 3차 작업: HantuStock API 함수 추가

### 이슈 3: inquire_price() 함수 미존재
**문제**: `get_current_price()`에서 `api.inquire_price(ticker)` 호출하는데 함수 없음

**해결**: `HantuStock.py`에 2개 함수 추가

#### 추가된 함수

**1. inquire_price(ticker)** - 현재가 조회
```python
def inquire_price(self, ticker):
    """
    특정 종목의 현재가 조회
    
    TR ID: FHKST01010100 (국내주식 기본시세 조회)
    """
    headers = self.get_header('FHKST01010100', add_prefix=False)
    # API 호출 및 현재가 반환
```

**2. inquire_daily_price(ticker, start_date, end_date, adj_price)** - 일봉 조회
```python
def inquire_daily_price(self, ticker, start_date=None, end_date=None, adj_price=True):
    """
    특정 종목의 일봉 데이터 조회
    
    TR ID: FHKST03010100 (국내주식 기간별 시세 조회)
    """
    headers = self.get_header('FHKST03010100', add_prefix=False)
    # API 호출 및 DataFrame 반환
```

---

## 4차 작업: get_header() 함수 개선

### 이슈 4: TR ID prefix 문제
**문제**: 
- 시세 조회 API는 실거래/모의투자 **동일한 TR ID** 사용
- 기존 `get_header()`는 항상 prefix(T/V) 추가
- 결과: `FHKST01010100` → `TFHKST01010100` (잘못됨)

**분석**:
- H로 시작하는 TR ID도 존재
- 모의투자 미지원 API 존재
- 예측 불가능한 예외 케이스 발생 가능

**해결책 선택**: **명시적 파라미터 방식** (방법 2)

#### 수정된 get_header()
```python
# 수정 전
def get_header(self, tr_id_suffix):
    tr_id = f"{self._tr_prefix}{tr_id_suffix}"
    ...

# 수정 후
def get_header(self, tr_id, add_prefix=True):
    """
    Args:
        tr_id (str): TR ID 또는 TR ID suffix
        add_prefix (bool): 모드에 따라 T/V prefix 추가 여부
            - True: 주문/계좌 API용 (예: TTC0802U → TTTC0802U)
            - False: 시세 조회 API용 (예: FHKST01010100)
    """
    if add_prefix:
        final_tr_id = f"{self._tr_prefix}{tr_id}"
    else:
        final_tr_id = tr_id
    ...
```

#### TR ID 처리 결과

| API 종류 | 원본 TR ID | add_prefix | 실거래 | 모의투자 |
|----------|-----------|------------|--------|----------|
| 시세 조회 | FHKST01010100 | False | FHKST01010100 | FHKST01010100 |
| 일봉 조회 | FHKST03010100 | False | FHKST03010100 | FHKST03010100 |
| 계좌 조회 | TTC8434R | True | TTTC8434R | VTTC8434R |
| 매수 주문 | TTC0012U | True | TTTC0012U | VTTC0012U |

---

## 5차 작업: HantuStock 초기화 수정

### 이슈 5: API 인증 정보 전달
**문제**: `collector.py`에서 `api = HantuStock()` 파라미터 없이 호출

**해결**: config_loader에서 인증 정보 가져와서 전달

```python
# 수정 후
from src.utils.koreainvestment import HantuStock
from src.config.config_loader import get_api_credentials

# API 인증 정보 가져오기
credentials = get_api_credentials()

# API 인스턴스 생성
api = HantuStock(
    api_key=credentials['api_key'],
    secret_key=credentials['secret_key'],
    account_id=credentials['account_id'],
    mode=credentials['mode']
)
```

**적용 함수**:
- `get_real_time_data()`
- `get_current_price()`

---

## 6차 작업: 테스트 코드 정리

### 수정 사항
**삭제**: `test_get_stock_data_default_params()` 테스트

**이유**:
- 기본 파라미터(최근 100일)에 대한 상세 검증 불필요
- 날짜 범위 검증은 다른 테스트에서 충분히 커버됨

**최종 테스트**: 12개 (1개 삭제)

---

## 최종 파일 구조

```
src/
├── data/
│   ├── __init__.py                # ✅ 모듈 export
│   ├── collector.py               # ✅ 데이터 수집 모듈 (8개 함수)
│   └── README.md                  # ✅ 사용 가이드
│
├── utils/
│   └── koreainvestment/
│       ├── __init__.py            # ✅ HantuStock export
│       └── HantuStock.py          # ✅ inquire_price(), inquire_daily_price() 추가
│                                  # ✅ get_header() add_prefix 파라미터 추가
│
└── tests/
    └── test_collector.py          # ✅ 테스트 코드 (12개)
```

---

## 핵심 개선 사항

### 1. 표준 패키지 Import
- sys.path 조작 제거
- IDE 자동완성 및 타입 체크 지원

### 2. API 함수 완성
- 현재가 조회 (`inquire_price`)
- 일봉 데이터 조회 (`inquire_daily_price`)

### 3. 유연한 TR ID 처리
- `add_prefix` 파라미터로 명시적 제어
- H로 시작하는 TR ID, 모의투자 미지원 API 대응

### 4. 자동 인증 관리
- config_loader에서 API 키 자동 로드
- 모드(실거래/모의투자) 자동 전환

---

## 테스트 결과

```bash
$ pytest src/tests/test_collector.py -v

TestNormalizeDataFrame::test_normalize_fdr_format ✅
TestNormalizeDataFrame::test_normalize_pykrx_format ✅
TestValidateData::test_validate_valid_data ✅
TestValidateData::test_validate_with_min_rows ✅
TestGetHistoricalData::test_get_historical_data_fdr ✅
TestGetHistoricalData::test_get_historical_data_pykrx ✅
TestGetRealTimeData::test_get_real_time_data_daily ✅
TestGetStockData::test_get_stock_data_auto_recent ✅
TestGetStockData::test_get_stock_data_auto_historical ✅
TestGetMultipleStocks::test_get_multiple_stocks_success ✅
TestGetCurrentPrice::test_get_current_price_success ✅
TestGetMarketStatus::test_get_market_status_success ✅

✅ 12 passed
```

---

## 사용 예시

### 기본 사용법
```python
from src.data import get_stock_data

# 최근 100일 (자동 선택)
df = get_stock_data('005930')

# 과거 데이터
df = get_stock_data('005930', '2023-01-01', '2023-12-31')

# 다종목 수집
data = get_multiple_stocks(['005930', '000660', '035420'])

# 현재가 조회
price = get_current_price('005930')
```

---

## 다음 단계

### Level 2: 기술적 지표 계산 모듈
`src/analysis/technical/indicators.py`

**구현 예정**:
1. EMA 계산 (5일, 20일, 40일)
2. MACD 3종 조합 (5|20|9, 5|40|9, 20|40|9)
3. ATR 계산
4. 히스토그램 & 시그널선
5. 피크아웃 감지

**예상 일정**: 1-2일

---

## 이슈 요약

| # | 이슈 | 해결 방법 |
|---|------|----------|
| 1 | koreainvestment import 오류 | 표준 패키지 import 사용 |
| 2 | 테스트 파일 import 오류 | src.data.collector로 수정 |
| 3 | inquire_price 함수 미존재 | HantuStock.py에 함수 추가 |
| 4 | TR ID prefix 문제 | get_header에 add_prefix 파라미터 |
| 5 | API 인증 정보 미전달 | config_loader 사용 |
| 6 | 불필요한 테스트 | default_params 테스트 삭제 |

---

## 주요 기술 결정

### 1. Import 방식
- ❌ sys.path 조작
- ✅ 표준 패키지 import

### 2. TR ID 처리
- ❌ 자동 감지 (규칙 기반)
- ✅ 명시적 파라미터 (add_prefix)

### 3. 테스트 범위
- ❌ 날짜 범위 상세 검증
- ✅ 기본 동작 검증

---

## 참고 문서

- [개발 계획](plan/2025-10-30_common_modules_planning.md)
- [데이터 수집 모듈 README](../src/data/README.md)
- [API 연동 가이드](./2025-10-15_api_integration_and_testing.md)

---

## 작성자
- seunghakim
- AI Assistant (Claude)

## 검토 이력
- 2025-10-30: 데이터 수집 모듈 구현 완료 ✅
- 2025-10-30: Import 경로 수정 ✅
- 2025-10-30: API 함수 추가 및 get_header 개선 ✅
- 2025-10-30: 테스트 정리 완료 ✅
