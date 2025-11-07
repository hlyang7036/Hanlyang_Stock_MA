# Technical Indicators Module (기술적 지표 모듈)

이동평균선 투자법 전략에 필요한 기술적 지표를 계산하는 모듈입니다.

## 📌 개요

본 모듈은 Level 2 공통 모듈로, 주가 데이터를 기반으로 다음 지표들을 계산합니다:
- **EMA (Exponential Moving Average)**: 지수 이동평균선
- **SMA (Simple Moving Average)**: 단순 이동평균선
- **ATR (Average True Range)**: 평균 진폭 (변동성 지표)
- **MACD (Moving Average Convergence Divergence)**: 이동평균 수렴확산 (예정)

---

## 🚀 시작하기

### Import

```python
from src.analysis.technical import (
    calculate_ema,
    calculate_sma,
    calculate_atr,
    calculate_true_range
)
```

---

## 📊 함수 설명 및 사용 예시

### 1. calculate_ema() - 지수 이동평균

최근 가격에 더 높은 가중치를 부여하는 이동평균입니다.

**시그니처**:
```python
calculate_ema(
    data: Union[pd.Series, pd.DataFrame],
    period: int,
    column: str = 'Close'
) -> pd.Series
```

**파라미터**:
- `data`: 가격 데이터 (Series 또는 DataFrame)
- `period`: EMA 계산 기간 (예: 5, 20, 40)
- `column`: DataFrame 사용 시 계산할 컬럼명

**사용 예시**:

```python
import pandas as pd
from src.data import get_stock_data
from src.analysis.technical import calculate_ema

# 주가 데이터 가져오기
df = get_stock_data('005930', period=100)

# 3개 이동평균선 계산
df['EMA_5'] = calculate_ema(df, period=5)
df['EMA_20'] = calculate_ema(df, period=20)
df['EMA_40'] = calculate_ema(df, period=40)

print(df[['Close', 'EMA_5', 'EMA_20', 'EMA_40']].tail())
```

**출력 예시**:
```
                Close    EMA_5   EMA_20   EMA_40
Date                                            
2024-11-03  60500.0  60234.5  59876.3  59456.2
2024-11-04  61000.0  60567.8  60123.4  59678.5
```

**특징**:
- 최근 가격에 더 민감하게 반응
- SMA보다 빠른 추세 변화 포착
- 초기 period-1개의 값은 NaN

---

### 2. calculate_sma() - 단순 이동평균

모든 기간에 동일한 가중치를 부여하는 이동평균입니다.

**시그니처**:
```python
calculate_sma(
    data: Union[pd.Series, pd.DataFrame],
    period: int,
    column: str = 'Close'
) -> pd.Series
```

**사용 예시**:

```python
# SMA 계산
df['SMA_20'] = calculate_sma(df, period=20)

# EMA와 SMA 비교
print(df[['Close', 'EMA_20', 'SMA_20']].tail())
```

**특징**:
- 모든 기간에 동일 가중치
- EMA보다 안정적이지만 느림
- 장기 추세 파악에 유용

---

### 3. calculate_atr() - 평균 진폭

변동성을 측정하는 지표로, 포지션 사이징에 사용됩니다.

**시그니처**:
```python
calculate_atr(
    data: pd.DataFrame,
    period: int = 20
) -> pd.Series
```

**파라미터**:
- `data`: OHLC 데이터 (High, Low, Close 컬럼 필요)
- `period`: ATR 계산 기간 (기본값: 20일)

**사용 예시**:

```python
from src.analysis.technical import calculate_atr

# ATR 계산
df['ATR_20'] = calculate_atr(df, period=20)

# 포지션 사이징
account_balance = 10_000_000  # 1천만원
risk_per_trade = 0.01  # 1%

current_price = df['Close'].iloc[-1]
current_atr = df['ATR_20'].iloc[-1]

# 1유닛 계산
unit_size = (account_balance * risk_per_trade) / current_atr
print(f"현재가: {current_price:,.0f}원")
print(f"ATR: {current_atr:,.0f}원")
print(f"1유닛: {unit_size:.0f}주")

# 손절 라인 계산 (진입가 - 2ATR)
entry_price = current_price
stop_loss = entry_price - (2 * current_atr)
print(f"손절가: {stop_loss:,.0f}원")
```

**출력 예시**:
```
현재가: 60,500원
ATR: 2,345원
1유닛: 43주
손절가: 55,810원
```

**특징**:
- 변동성이 클수록 ATR 값 증가
- 터틀 트레이딩 기법에서 사용
- 손절/익절 라인 설정 시 2ATR 사용

---

### 4. calculate_true_range() - True Range

ATR의 구성 요소로, 일일 변동폭을 계산합니다.

**시그니처**:
```python
calculate_true_range(data: pd.DataFrame) -> pd.Series
```

**계산 방식**:
```
True Range = Max(
    고가 - 저가,
    |고가 - 전일 종가|,
    |저가 - 전일 종가|
)
```

**사용 예시**:

```python
from src.analysis.technical import calculate_true_range

# True Range 계산
df['TR'] = calculate_true_range(df)

print(df[['High', 'Low', 'Close', 'TR']].tail())
```

**특징**:
- 갭 상승/하락 시에도 정확한 변동폭 측정
- ATR 계산의 기초 지표

---

## 🔧 실전 활용 예시

### 예시 1: 이동평균선 대순환 분석 준비

```python
from src.data import get_stock_data
from src.analysis.technical import calculate_ema, calculate_atr

# 1. 데이터 수집
ticker = '005930'  # 삼성전자
df = get_stock_data(ticker, period=100)

# 2. 3개 이동평균선 계산
df['EMA_5'] = calculate_ema(df, period=5)   # 단기선
df['EMA_20'] = calculate_ema(df, period=20)  # 중기선
df['EMA_40'] = calculate_ema(df, period=40)  # 장기선

# 3. ATR 계산 (포지션 사이징용)
df['ATR_20'] = calculate_atr(df, period=20)

# 4. 최근 데이터 확인
print(df[['Close', 'EMA_5', 'EMA_20', 'EMA_40', 'ATR_20']].tail(10))
```

### 예시 2: 다종목 지표 계산

```python
from src.data import get_multiple_stocks
from src.analysis.technical import calculate_ema, calculate_atr

# 1. 다종목 데이터 수집
tickers = ['005930', '000660', '035420']  # 삼성전자, SK하이닉스, NAVER
data = get_multiple_stocks(tickers, period=100)

# 2. 각 종목별 지표 계산
results = {}
for ticker, df in data.items():
    if df is not None:
        df['EMA_5'] = calculate_ema(df, period=5)
        df['EMA_20'] = calculate_ema(df, period=20)
        df['EMA_40'] = calculate_ema(df, period=40)
        df['ATR_20'] = calculate_atr(df, period=20)
        results[ticker] = df

# 3. 최근 상태 비교
for ticker, df in results.items():
    latest = df.iloc[-1]
    print(f"\n{ticker}:")
    print(f"  종가: {latest['Close']:,.0f}원")
    print(f"  EMA5: {latest['EMA_5']:,.0f}원")
    print(f"  ATR: {latest['ATR_20']:,.0f}원")
```

### 예시 3: 포지션 사이징 계산기

```python
from src.analysis.technical import calculate_atr

def calculate_position_size(df, account_balance, risk_percent=1.0):
    """
    포지션 사이징 계산
    
    Args:
        df: 주가 데이터 (ATR_20 컬럼 필요)
        account_balance: 계좌 잔고
        risk_percent: 리스크 비율 (기본 1%)
    
    Returns:
        dict: 포지션 정보
    """
    current_price = df['Close'].iloc[-1]
    atr = df['ATR_20'].iloc[-1]
    
    # 1유닛 계산
    risk_amount = account_balance * (risk_percent / 100)
    unit_size = risk_amount / atr
    
    # 손절가 계산 (진입가 - 2ATR)
    stop_loss = current_price - (2 * atr)
    stop_loss_percent = ((current_price - stop_loss) / current_price) * 100
    
    return {
        'ticker': df.index.name if hasattr(df.index, 'name') else 'Unknown',
        'current_price': current_price,
        'atr': atr,
        'unit_size': int(unit_size),
        'stop_loss': stop_loss,
        'stop_loss_percent': stop_loss_percent,
        'max_loss': risk_amount
    }

# 사용 예시
df = get_stock_data('005930', period=100)
df['ATR_20'] = calculate_atr(df, period=20)

position = calculate_position_size(df, account_balance=10_000_000, risk_percent=1.0)

print(f"\n포지션 정보:")
print(f"현재가: {position['current_price']:,.0f}원")
print(f"1유닛: {position['unit_size']}주")
print(f"손절가: {position['stop_loss']:,.0f}원 ({position['stop_loss_percent']:.2f}%)")
print(f"최대 손실: {position['max_loss']:,.0f}원")
```

---

## ⚠️ 주의사항

### 1. 데이터 길이 요구사항

각 지표는 최소 데이터 길이가 필요합니다:

| 지표 | 최소 데이터 길이 |
|------|----------------|
| EMA(5) | 5일 |
| EMA(20) | 20일 |
| EMA(40) | 40일 |
| ATR(20) | 21일 (True Range 계산에 1일 추가 필요) |

**권장**: 최소 100일 이상의 데이터 사용

### 2. NaN 값 처리

초기 period-1개의 값은 NaN입니다:

```python
df['EMA_20'] = calculate_ema(df, period=20)

# 처음 19개는 NaN
print(df['EMA_20'].iloc[:19].isna().all())  # True

# 20번째부터 값 존재
print(df['EMA_20'].iloc[19:].isna().any())  # False
```

### 3. 데이터 정합성

ATR 계산 시 가격 관계 검증:
- High >= Close
- Close >= Low
- High >= Low

잘못된 데이터는 이상한 ATR 값을 생성할 수 있습니다.

### 4. 계산 순서

MACD 계산 시 EMA가 먼저 필요합니다:

```python
# 올바른 순서
df['EMA_5'] = calculate_ema(df, period=5)
df['EMA_20'] = calculate_ema(df, period=20)
# MACD = EMA_5 - EMA_20 (다음 단계에서 구현)
```

---

## 🧪 테스트

테스트 코드 실행:

```bash
# 전체 테스트
pytest src/tests/test_indicators.py -v

# 특정 테스트 클래스
pytest src/tests/test_indicators.py::TestCalculateEMA -v

# 특정 테스트 함수
pytest src/tests/test_indicators.py::TestCalculateEMA::test_ema_with_dataframe -v
```

**테스트 결과**:
```
✅ 19 passed (EMA 7개, SMA 2개, TR 4개, ATR 5개, 통합 1개)
```

---

## 📝 다음 단계

### 2단계: MACD 계산 모듈 (예정)

다음 단계에서 구현할 함수들:
- `calculate_macd()` - 단일 MACD 계산
- `calculate_triple_macd()` - 3종 MACD 동시 계산
  - MACD(상): 5|20|9
  - MACD(중): 5|40|9
  - MACD(하): 20|40|9

### 3단계: 방향성 분석 함수 (예정)

- `detect_peakout()` - 피크아웃 감지
- `calculate_slope()` - 기울기 계산
- `check_direction()` - 방향 판단

---

## 📚 참고 자료

- [이동평균선 투자법 전략 정리](../../Moving_Average_Investment_Strategy_Summary.md)
- [개발 계획](../../history/2025-10-30_common_modules_planning.md)
- [데이터 수집 모듈](../data/README.md)

---

## 작성자

- seunghakim
- AI Assistant (Claude)

## 버전 이력

- 2025-11-07: Level 2 - 기본 지표 모듈 완성 (EMA, SMA, ATR) ✅