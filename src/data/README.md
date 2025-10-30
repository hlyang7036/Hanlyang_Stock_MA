# 데이터 수집 모듈 (collector.py)

## 개요

`collector.py`는 주가 데이터를 수집하고 정규화하는 공통 모듈입니다.
실시간 전략(`strategy`)과 백테스팅(`backtest`) 모두에서 사용됩니다.

## 주요 기능

### 1. 통합 데이터 수집 인터페이스
- 실시간 데이터와 과거 데이터를 동일한 인터페이스로 제공
- 자동으로 최적의 데이터 소스 선택
- 표준화된 DataFrame 형식 반환

### 2. 다양한 데이터 소스 지원
- **HantuStock API**: 실시간 및 최근 데이터
- **FinanceDataReader**: 과거 장기 데이터
- **pykrx**: 한국거래소 공식 데이터

### 3. 데이터 검증 및 정규화
- 필수 컬럼 확인
- 이상치 제거
- 표준 형식으로 변환

## 함수 목록

### 핵심 함수

#### `get_stock_data()` ⭐⭐⭐
주가 데이터 수집의 메인 함수입니다.

```python
from src.data import get_stock_data

# 최근 100일 데이터 (자동 선택)
df = get_stock_data('005930')

# 특정 기간 데이터
df = get_stock_data('005930', '2023-01-01', '2023-12-31')

# 데이터 소스 지정
df = get_stock_data('005930', source='fdr')
```

**파라미터**:
- `ticker` (str): 종목 코드
- `start_date` (str, optional): 시작일 (YYYY-MM-DD)
- `end_date` (str, optional): 종료일 (YYYY-MM-DD)
- `period` (str): 봉 주기 ('D'=일봉)
- `source` (str): 데이터 소스 ('auto', 'api', 'fdr', 'pykrx')

**반환**: DataFrame (OHLCV)

---

#### `get_real_time_data()` ⭐⭐
실시간 및 최근 데이터를 조회합니다.

```python
from src.data import get_real_time_data

# 최근 100일 데이터
df = get_real_time_data('005930', 'D', 100)
```

**파라미터**:
- `ticker` (str): 종목 코드
- `period` (str): 봉 주기 ('D'=일봉)
- `count` (int): 조회할 데이터 개수

---

#### `get_historical_data()` ⭐⭐
과거 장기간 데이터를 조회합니다.

```python
from src.data import get_historical_data

# FinanceDataReader 사용
df = get_historical_data('005930', '2020-01-01', '2023-12-31', source='fdr')

# pykrx 사용
df = get_historical_data('005930', '2020-01-01', '2023-12-31', source='pykrx')
```

---

#### `get_multiple_stocks()` ⭐
여러 종목을 병렬로 수집합니다.

```python
from src.data import get_multiple_stocks

tickers = ['005930', '000660', '035420']
data = get_multiple_stocks(tickers, '2024-01-01', '2024-01-31')

for ticker, df in data.items():
    print(f"{ticker}: {len(df)} rows")
```

---

### 보조 함수

#### `get_current_price()`
특정 종목의 현재가를 조회합니다.

```python
from src.data import get_current_price

price = get_current_price('005930')
print(f"현재가: {price:,.0f}원")
```

---

#### `get_market_status()`
현재 시장 상태를 확인합니다.

```python
from src.data import get_market_status

status = get_market_status()
if status == 'open':
    print("장이 열려있습니다.")
```

반환값: `'open'`, `'close'`, `'pre_market'`, `'after_hours'`, `'unknown'`

---

#### `validate_data()`
데이터의 유효성을 검증합니다.

```python
from src.data import validate_data

if validate_data(df, min_rows=20):
    print("데이터가 유효합니다.")
```

---

## 반환 데이터 형식

모든 함수는 동일한 형식의 DataFrame을 반환합니다:

```python
                       Open    High     Low   Close    Volume
Date                                                          
2024-01-02 00:00:00  60000   61000   59500   60500  10000000
2024-01-03 00:00:00  60500   62000   60000   61500  12000000
2024-01-04 00:00:00  61500   63000   61000   62500  15000000
```

**특징**:
- **Index**: datetime 타입 (날짜 오름차순 정렬)
- **Columns**: `Open`, `High`, `Low`, `Close`, `Volume` (대문자)
- **데이터 타입**: 가격은 float, Volume은 int64
- **결측치**: 자동 제거됨

---

## 사용 예시

### 1. 실시간 전략에서 사용

```python
from src.data import get_stock_data, get_market_status

# 장 상태 확인
if get_market_status() == 'open':
    # 최근 100일 데이터로 신호 분석
    df = get_stock_data('005930')
    
    # 분석 및 매매 로직
    # ...
```

### 2. 백테스팅에서 사용

```python
from src.data import get_stock_data

# 과거 데이터로 백테스팅
df = get_stock_data('005930', '2020-01-01', '2023-12-31')

# 전략 실행 및 성과 분석
# ...
```

### 3. 다종목 포트폴리오 백테스팅

```python
from src.data import get_multiple_stocks

# 여러 종목 동시 수집
tickers = ['005930', '000660', '035420', '005380', '051910']
data = get_multiple_stocks(tickers, '2023-01-01', '2023-12-31')

# 각 종목별로 전략 실행
for ticker, df in data.items():
    if df is not None:
        # 전략 실행
        pass
```

---

## 테스트 실행

```bash
# 전체 테스트
pytest src/tests/test_collector.py -v

# 특정 테스트 클래스만
pytest src/tests/test_collector.py::TestGetStockData -v

# 특정 테스트 함수만
pytest src/tests/test_collector.py::TestGetStockData::test_get_stock_data_auto_recent -v
```

---

## 주의사항

### 1. API 호출 제한
- HantuStock API는 10초당 1회 토큰 발급 제한이 있습니다
- 토큰 캐싱으로 24시간 동안 재사용합니다

### 2. 데이터 소스 선택
- **최근 100일 이내**: API 사용 권장 (실시간성)
- **100일 초과**: FDR 사용 권장 (안정성)
- **상장폐지 종목**: pykrx 사용

### 3. 데이터 검증
- 수집된 데이터는 자동으로 검증됩니다
- 이상치(음수, 0값)는 자동 제거됩니다
- High < Low인 데이터는 제거됩니다

### 4. 병렬 처리
- `get_multiple_stocks()`는 최대 5개 스레드로 병렬 처리합니다
- 너무 많은 종목을 동시에 요청하면 API 제한에 걸릴 수 있습니다

---

## 에러 처리

```python
from src.data import get_stock_data

try:
    df = get_stock_data('005930', '2024-01-01', '2024-12-31')
except ValueError as e:
    print(f"파라미터 오류: {e}")
except Exception as e:
    print(f"데이터 수집 실패: {e}")
```

---

## 다음 단계

이 모듈을 기반으로 다음 모듈들이 구현될 예정입니다:

1. **기술적 지표 계산** (`src/analysis/technical/`)
   - EMA, MACD, ATR 계산
   
2. **스테이지 분석** (`src/analysis/stage.py`)
   - 6단계 스테이지 판단
   
3. **매매 신호 생성** (`src/analysis/signal/`)
   - 진입/청산 신호 생성
   
4. **리스크 관리** (`src/risk/`)
   - 포지션 사이징, 손절 라인

---

## 참고

- [프로젝트 구조](../../README.md)
- [개발 계획](../../history/2025-10-30_common_modules_planning.md)
- [API 연동 가이드](../../history/2025-10-15_api_integration_and_testing.md)
