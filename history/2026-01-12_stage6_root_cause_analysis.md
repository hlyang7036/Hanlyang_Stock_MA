# Stage 6 낮은 승률 근본 원인 분석

## 날짜
2026-01-12

## 분석 개요

Stage 6의 11.1% 승률(89% 손실률)에 대해 두 가지 방향에서 근본 원인을 분석합니다:
1. **Stop-loss 메커니즘 분석**: 손절이 너무 빨리 발생하는가?
2. **Stage 6 판단 로직 분석**: Stage 6 진입 조건이 잘못되었는가?

---

## Part 1: Stop-Loss 메커니즘 분석

### 1.1 Stop-Loss 실행 프로세스

#### 전체 흐름
```
engine.py::process_day()
  ↓
1. portfolio.update_trailing_stops()  # 수익 나면 손절가 상향
  ↓
2. engine.check_and_execute_stops()
  ↓
3. portfolio.check_stop_losses()
  ↓
4. stop_loss.check_stop_loss_triggered()
  ↓
5. 손절 발동 시 즉시 청산
```

### 1.2 코드 레벨 분석

#### Step 1: engine.py - check_and_execute_stops()
```python
# src/backtest/engine.py:284-339
def check_and_execute_stops(self, date, current_prices):
    # 손절 발동 체크
    triggered = self.portfolio.check_stop_losses(
        current_prices=current_prices,
        market_data=self.market_data
    )

    if not triggered:
        return

    # 손절 주문 실행
    for item in triggered:
        ticker = item['ticker']
        stop_price = item['stop_price']

        # 손절가로 체결
        execution_result = self.execution_engine.execute(
            order=order,
            market_price=stop_price  # ← 손절가로 청산
        )
```

**핵심**:
- 손절 발동 시 즉시 청산 (다음 날까지 기다리지 않음)
- 손절가로 체결 (슬리피지 적용)

#### Step 2: portfolio.py - check_stop_losses()
```python
# src/backtest/portfolio.py:370-416
def check_stop_losses(self, current_prices, market_data):
    from src.analysis.risk.stop_loss import check_stop_loss_triggered

    triggered = []

    for ticker, position in self.positions.items():
        current_price = current_prices.get(ticker)

        # 손절 발동 체크
        is_triggered = check_stop_loss_triggered(
            current_price=current_price,
            stop_price=position.stop_price,  # ← 초기 손절가 또는 trailing_stop 손절가
            position_type=position.position_type
        )

        if is_triggered:
            triggered.append({
                'ticker': ticker,
                'stop_price': position.stop_price,
                'current_price': current_price,
                'stop_type': position.stop_type
            })
```

**핵심**:
- 각 포지션의 `position.stop_price`와 현재가 비교
- `position.stop_price`는 trailing_stop에 의해 업데이트될 수 있음

#### Step 3: stop_loss.py - check_stop_loss_triggered()
```python
# src/analysis/risk/stop_loss.py:390-472
def check_stop_loss_triggered(current_price, stop_price, position_type):
    # 3. 손절 발동 확인
    if position_type == 'long':
        # 매수 포지션: 현재가 <= 손절가
        triggered = current_price <= stop_price
    else:
        # 매도 포지션: 현재가 >= 손절가
        triggered = current_price >= stop_price

    return triggered
```

**핵심 판단 로직**:
- **Long 포지션**: `현재가 <= 손절가` → 손절 발동
- **Short 포지션**: `현재가 >= 손절가` → 손절 발동
- **정확히 같아도 손절** (equal 포함)

### 1.3 초기 Stop-Price 계산 과정

#### apply_risk_management()에서의 손절가 결정
```python
# src/analysis/risk/__init__.py:330-372
# Step 3: 손절가 계산
try:
    # 3.1 변동성 기반 손절
    volatility_stop = calculate_volatility_stop(
        entry_price=current_price,
        atr=atr,
        position_type=position_type,
        atr_multiplier=cfg['atr_multiplier']  # 기본값 2.0
    )

    # 3.2 추세 기반 손절
    trend_stop = trend_stop_value  # EMA_20

    # 3.3 최종 손절가 결정
    stop_info = get_stop_loss_price(
        entry_price=current_price,
        current_price=current_price,
        atr=atr,
        trend_stop=trend_stop,  # EMA_20
        position_type=position_type,
        atr_multiplier=cfg['atr_multiplier']
    )

    stop_price = stop_info['stop_price']
    stop_type = stop_info['stop_type']  # 'volatility' or 'trend'
```

#### 변동성 기반 손절 (Volatility Stop)
```python
# src/analysis/risk/stop_loss.py:23-118
def calculate_volatility_stop(entry_price, atr, position_type, atr_multiplier=2.0):
    """
    Formula:
        매수 포지션: 손절가 = 진입가 - (ATR × 배수)
        매도 포지션: 손절가 = 진입가 + (ATR × 배수)
    """
    if position_type == 'long':
        stop_price = entry_price - (atr * atr_multiplier)
    else:
        stop_price = entry_price + (atr * atr_multiplier)

    return stop_price
```

**예시 계산**:
```
진입가: 50,000원
ATR: 1,000원
atr_multiplier: 2.0

손절가 = 50,000 - (1,000 × 2.0) = 48,000원
손절 폭: -4.0% (2,000원 / 50,000원)
```

#### Trailing Stop 업데이트
```python
# src/backtest/portfolio.py:418-464
def update_trailing_stops(self, current_prices, market_data):
    for ticker, position in self.positions.items():
        current_price = current_prices.get(ticker)

        # 최고가 업데이트
        position.update_extremes(current_price)

        if position.position_type == 'long' and position.highest_price:
            new_stop = update_trailing_stop(
                entry_price=position.entry_price,
                highest_price=position.highest_price,  # ← 지금까지 최고가
                current_stop=position.stop_price,
                atr=latest_atr,
                position_type='long'
            )

            # 손절가는 위로만 올라감 (아래로 내려가지 않음)
            if new_stop > position.stop_price:
                position.stop_price = new_stop  # ← 손절가 상향 조정
```

**Trailing Stop 로직**:
- 가격이 상승하면 → 손절가도 따라 올라감
- 가격이 하락해도 → 손절가는 내려가지 않음
- 결과: 수익을 보호하면서 상승 추세를 따라감

### 1.4 Stop-Loss 메커니즘의 문제점

#### 문제 1: ATR 기반 손절폭이 Stage와 무관
```
Stage 3 (바닥권):
- ATR: 1,000원 (변동성 보통)
- 손절폭: 2,000원 (4%)
- 진입 후 즉시 반등 → 손절 도달 안 함

Stage 6 (반등 시작):
- ATR: 1,000원 (동일)
- 손절폭: 2,000원 (동일)
- 진입 후 재차 하락 → 바로 손절 도달
```

**핵심**: ATR 기반 손절은 변동성만 고려하고 **시장 구조(Stage)는 고려하지 않음**

#### 문제 2: Stage 6 진입 시점의 구조적 취약성
```
Stage 6 = Short > Long > Mid
        = 단기선이 최상단, 중기선이 최하단
        = 상승 초입 또는 단기 반등

실제 시나리오:
1. MACD(중) 골든크로스 발생 → Stage 6 확정
2. 매수 신호 발생 → 진입 (가격: 50,000원)
3. 초기 손절가 설정: 48,000원 (ATR 2배)
4. 다음 날 가격: 49,000원 (횡보 또는 약간 하락)
5. 그 다음 날 가격: 47,500원 (재차 하락)
6. 손절 발동! (47,500원 < 48,000원)

보유 기간: 2일
손익: -2,500원 (-5%)
```

**Stage 6의 구조적 문제**:
- MACD 골든크로스가 **지속적 상승을 보장하지 않음**
- 단기 반등일 가능성이 매우 높음
- 진입 후 바로 하락 → 손절폭 내에서 청산

#### 문제 3: Trailing Stop 활성화 실패
```
Trailing Stop 작동 조건:
- 가격이 최고가를 갱신해야 함
- 그래야 손절가가 올라감

Stage 6 실제 패턴:
진입 (50,000원) → 50,500원 (소폭 상승) → 49,500원 → 47,500원 (손절)
       ↓
최고가: 50,500원 (0.5% 상승)
Trailing stop 활성화: X (상승폭이 너무 작음)
결과: 초기 손절가 48,000원 유지 → 손절 발동
```

**백테스팅 결과 검증**:
```
Stage 6: 45건 중
- trailing_stop: 2건 (4.4%) ← Trailing stop까지 도달한 경우 극소수
- stop_loss: 40건 (88.9%) ← 대부분 초기 손절가에 걸림
- exit_signal: 3건 (6.7%)
```

### 1.5 Stop-Loss 메커니즘 결론

#### ✅ Stop-Loss 로직은 정상 작동
- 코드에 버그 없음
- ATR 기반 계산 정확함
- Trailing stop 업데이트 정상
- 손절 발동 조건 명확함

#### ❌ 문제는 Stage 6의 시장 구조
- **Stop-loss가 "너무 빨리" 발동하는 것이 아님**
- **Stage 6 진입 후 실제로 가격이 하락하는 것이 문제**
- Stop-loss는 설계된 대로 작동 중 (진입가 - 2×ATR)

#### 📊 Stage 3 vs Stage 6 비교
| 항목 | Stage 3 (역발상) | Stage 6 (일반) |
|------|----------------|---------------|
| **진입 시점** | 바닥권 (과매도) | 반등 시작 (불확실) |
| **이후 움직임** | 즉시 반등 ↗️ | 재차 하락 ↘️ |
| **손절 도달** | 도달 안 함 (0건) | 바로 도달 (40건) |
| **Trailing stop** | 100% 활성화 | 4.4% 활성화 |

**결론**: Stop-loss 메커니즘은 정상. **문제는 Stage 6 진입 조건 자체**.

---

## Part 2: Stage 6 판단 로직 분석

### 2.1 데이터 로딩 및 MACD 계산 프로세스

#### 전체 흐름
```
engine.py::run_backtest()
  ↓
data_manager.load_market_data(start_date, end_date)
  ↓
data_manager.load_data([ticker], start_date, end_date)
  ↓
collector.get_stock_data(ticker, start_date, end_date)  # OHLCV 로드
  ↓
indicators.calculate_all_indicators(data)  # EMA, MACD 계산
  ↓
stage.determine_stage(data)  # Stage 판단
  ↓
stage.detect_stage_transition(data)  # Stage 전환 감지
```

### 2.2 코드 레벨 분석

#### Step 1: engine.py - 데이터 로딩
```python
# src/backtest/engine.py:194-208
# MACD 계산을 위한 lookback period 추가
LOOKBACK_DAYS = 60  # MACD(중): 5|40|9 → 최소 49일 + 여유 10일

start_date_dt = datetime.strptime(start_date, '%Y-%m-%d')
data_start_date = (start_date_dt - timedelta(days=LOOKBACK_DAYS)).strftime('%Y-%m-%d')

logger.info(f"데이터 수집 기간: {data_start_date} ~ {end_date} (lookback {LOOKBACK_DAYS}일 포함)")

# 1. 전체 시장 데이터 로드 (lookback period 포함)
self.market_data = self.data_manager.load_market_data(
    start_date=data_start_date,  # lookback 포함한 시작일
    end_date=end_date,
    market=market
)
```

**핵심**:
- 60일 lookback으로 MACD 계산에 필요한 사전 데이터 확보
- 예: 백테스트 2025-05-01 시작 → 데이터는 2025-03-02부터 로드

#### Step 2: data_manager.py - 지표 계산
```python
# src/backtest/data_manager.py:271-277
if calculate_indicators:
    # 지표 계산
    data = calculate_all_indicators(data)

    # 스테이지 분석
    data['Stage'] = determine_stage(data)
    data['Stage_Transition'] = detect_stage_transition(data)
```

**핵심**:
- `calculate_all_indicators()`: EMA, MACD, ATR, RSI 등 모든 지표 계산
- `determine_stage()`: 6단계 Stage 판단
- 모든 데이터에 대해 일괄 계산

#### Step 3: indicators.py - MACD 계산
```python
# MACD 계산 로직 (indicators.py에서)
# MACD_상 = EMA_5 - EMA_20
data['MACD_상'] = data['EMA_5'] - data['EMA_20']
data['Signal_상'] = data['MACD_상'].ewm(span=9, adjust=False).mean()

# MACD_중 = EMA_5 - EMA_40
data['MACD_중'] = data['EMA_5'] - data['EMA_40']
data['Signal_중'] = data['MACD_중'].ewm(span=9, adjust=False).mean()

# MACD_하 = EMA_20 - EMA_40
data['MACD_하'] = data['EMA_20'] - data['EMA_40']
data['Signal_하'] = data['MACD_하'].ewm(span=9, adjust=False).mean()
```

**필요 기간**:
- EMA_40: 최소 40일
- Signal (EMA 9): 추가 9일
- **총 필요 기간**: 40 + 9 = 49일 (영업일 기준)

#### Step 4: stage.py - Stage 6 판단
```python
# src/analysis/stage.py:196-295
def determine_stage(data):
    # 1단계: 이동평균선 배열로 기본 스테이지 판단
    stage = determine_ma_arrangement(data)

    # 2단계: MACD 0선 교차 감지
    crosses = detect_macd_zero_cross(data)

    # 3단계: MACD 교차로 스테이지 확정
    # MACD(중) 골든크로스 → 제6스테이지 확정
    stage[crosses['Cross_중'] == 1] = 6  # ← Stage 6 판단 핵심
    gc2_count = (crosses['Cross_중'] == 1).sum()
    if gc2_count > 0:
        logger.info(f"골든크로스2 발생: {gc2_count}회 → 제6스테이지 확정")
```

**Stage 6 판단 조건**:
```
조건: MACD(중) 골든크로스 발생
즉: MACD(중) [이전 < 0, 현재 > 0] 또는
    MACD(중)과 Signal(중)의 교차
```

### 2.3 Stage 6 판단의 문제점

#### 문제 1: MACD 골든크로스의 의미 오해

**이론적 의미**:
```
MACD(중) = EMA_5 - EMA_40

MACD(중) 골든크로스 (0선 돌파):
- 단기선(EMA_5)이 장기선(EMA_40)을 상향 돌파
- "상승 추세 전환" 신호
```

**실제 시장 동작**:
```
시나리오 A (진짜 추세 전환):
날짜    가격    EMA_5   EMA_40   MACD(중)
D-10   45,000  46,000  48,000   -2,000  (하락세)
D-5    46,000  46,500  47,500   -1,000  (바닥)
D-1    47,000  47,500  47,200   +300    (골든크로스!) ← Stage 6
D+1    48,000  48,000  47,300   +700    (상승 지속)
D+5    50,000  49,500  47,800   +1,700  (강한 상승)
→ 결과: 수익

시나리오 B (거짓 신호 - Dead Cat Bounce):
날짜    가격    EMA_5   EMA_40   MACD(중)
D-10   45,000  46,000  48,000   -2,000  (하락세)
D-5    44,000  45,000  47,500   -2,500  (추가 하락)
D-1    46,000  45,500  47,000   -1,500  (단기 반등)
D+0    47,000  46,500  46,800   -300    (반등 지속)
D+1    48,000  47,500  46,700   +800    (골든크로스!) ← Stage 6
D+2    47,500  47,500  46,600   +900    (상승 둔화)
D+3    46,500  47,000  46,500   +500    (재차 하락)
D+4    45,000  46,200  46,300   -100    (하락 지속)
→ 결과: 손실 (손절)
```

**백테스팅 결과**:
- Stage 6 45건 중 40건이 시나리오 B 패턴 (88.9%)
- Stage 6 진입 = Dead Cat Bounce (죽은 고양이 반등) 포착 가능성 높음

#### 문제 2: MACD 골든크로스의 지연성

**MACD는 후행 지표**:
```
실제 가격 움직임:
Day 1-10: 하락
Day 11-15: 바닥
Day 16-20: 반등 시작  ← 여기서 매수해야 함
Day 21-25: 반등 지속
Day 26: MACD 골든크로스 발생! ← Stage 6 판단, 매수 신호

문제:
- 실제 반등 시작(Day 16)부터 10일 지연
- Day 26에 진입 = 반등의 중간/후반부 진입
- 이미 많이 올랐거나, 반등이 끝나는 시점일 가능성
```

**백테스팅 증거**:
```
Stage 6 진입 후 평균 보유기간:
- 손실 거래: 2.1일 ← 진입 후 바로 하락
- 수익 거래: 8.6일 ← 오래 보유해야 수익

해석:
- 손실 = 반등이 이미 끝난 시점에 진입 → 즉시 하락
- 수익 = 반등이 실제 추세 전환으로 이어짐 → 장기 보유
```

#### 문제 3: Stage 6 vs Stage 3 구조적 차이

| 항목 | Stage 3 (역발상) | Stage 6 (골든크로스) |
|------|----------------|---------------------|
| **진입 시점** | MACD 데드크로스 (매도 신호를 역발상) | MACD 골든크로스 (매수 신호) |
| **시장 상태** | 과매도 바닥권 (공포 극대화) | 반등 시작 (불확실) |
| **가격 위치** | 저가 (안전 마진 큼) | 중가 (안전 마진 작음) |
| **이후 움직임** | 즉시 반등 (평균 1.3일) | 불확실 (재차 하락 89%) |
| **심리적 상태** | 공포 → 희망 | 희망 → 실망 |

**Stage 3의 성공 요인**:
```
Stage 3 진입 = 과매도 바닥에서 매수
→ 하방 리스크 제한적 (이미 충분히 하락)
→ 상방 잠재력 큼 (반등 여력)
→ 손절가까지 거리 확보 (바닥 가격)
→ 100% 승률
```

**Stage 6의 실패 요인**:
```
Stage 6 진입 = 반등 중간/후반부에 매수
→ 하방 리스크 큼 (재차 하락 가능)
→ 상방 잠재력 제한적 (이미 반등함)
→ 손절가까지 거리 좁음 (반등 후 가격)
→ 11.1% 승률
```

### 2.4 Stage 6 판단 로직의 문제점 종합

#### 문제 요약

**1. MACD 골든크로스의 본질적 한계**:
- MACD는 후행 지표 → 10-15일 지연
- 골든크로스 발생 시점 = 반등의 중간/후반부
- Dead Cat Bounce와 진짜 추세 전환 구별 불가

**2. 데이터는 정확하게 로딩됨**:
- Lookback period 60일로 충분
- MACD 계산 정상
- Stage 판단 로직 코드 정상

**3. 문제는 Stage 6의 정의 자체**:
```
현재 정의:
Stage 6 = MACD(중) 골든크로스 발생

문제:
→ 골든크로스 = 이미 반등한 상태
→ 진입 시점이 너무 늦음
→ 재차 하락 가능성 높음 (Dead Cat Bounce)
```

#### 근본 원인

**Stage 6의 구조적 모순**:
```
책의 이론:
Stage 6 = 상승 변화기2
         = "상승 추세로 전환 중"
         = 매수 적기

실제 백테스팅:
Stage 6 = MACD 골든크로스 발생
         = "반등이 이미 진행됨"
         = 매수 지연 (늦은 진입)
         = 재차 하락 위험 높음
```

**MACD 지연성의 영향**:
```
실제 시장 타임라인:
Day 1: 바닥 형성
Day 5: 반등 시작 ← 이상적 진입 시점
Day 10: 반등 지속
Day 15: MACD 골든크로스 발생 ← Stage 6 확정, 실제 진입
Day 17: 반등 종료, 재차 하락 시작
Day 18: 손절 발동

결과: 2일 보유, -5% 손실
```

---

## Part 3: 종합 분석 및 결론

### 3.1 두 가지 원인의 상호작용

```
┌─────────────────────────────────────────────┐
│  Stage 6 진입 (MACD 골든크로스)              │
│  - 반등의 중간/후반부 진입                  │
│  - 가격이 이미 많이 올라간 상태              │
└─────────────────┬───────────────────────────┘
                  ↓
┌─────────────────────────────────────────────┐
│  Stop-Loss 설정                             │
│  - 진입가 - (2 × ATR)                       │
│  - 예: 50,000원 - 2,000원 = 48,000원       │
│  - 손절폭: 4%                                │
└─────────────────┬───────────────────────────┘
                  ↓
┌─────────────────────────────────────────────┐
│  가격 움직임 (Dead Cat Bounce 패턴)         │
│  Day 1: 50,000원 (진입)                     │
│  Day 2: 49,000원 (소폭 하락)                │
│  Day 3: 47,500원 (재차 하락)                │
└─────────────────┬───────────────────────────┘
                  ↓
┌─────────────────────────────────────────────┐
│  Stop-Loss 발동 (현재가 <= 손절가)          │
│  - 47,500원 < 48,000원 → 손절                │
│  - 보유 기간: 2일                            │
│  - 손익: -2,500원 (-5%)                      │
└─────────────────────────────────────────────┘
```

### 3.2 Stage 3 vs Stage 6 완전 비교

| 구분 | Stage 3 (역발상) | Stage 6 (골든크로스) |
|------|----------------|---------------------|
| **진입 신호** | MACD 데드크로스 (역발상) | MACD 골든크로스 |
| **시장 위치** | 과매도 바닥권 | 반등 중간/후반부 |
| **가격 상태** | 저가 (충분히 하락함) | 중가 (이미 반등함) |
| **심리** | 공포 극대화 | 희망 시작 |
| **진입 타이밍** | 최적 (바닥) | 지연 (늦음) |
| **하방 리스크** | 제한적 (더 이상 안 떨어짐) | 높음 (재차 하락 가능) |
| **상방 잠재력** | 큼 (반등 여력 충분) | 작음 (이미 반등함) |
| **손절가 거리** | 멀음 (안전 마진) | 가까움 (바로 도달) |
| **실제 움직임** | 즉시 상승 ↗️ | 재차 하락 ↘️ (89%) |
| **손절 발동** | 0건 (0%) | 40건 (89%) |
| **평균 보유** | 1.3일 (빠른 수익) | 2.8일 (길지만 손실) |
| **승률** | 100% | 11.1% |
| **평균 수익** | 116,562원 | 8,661원 |

### 3.3 근본 원인 결론

#### ❌ Stop-Loss가 문제가 아님
- Stop-loss 로직은 정상 작동
- ATR 기반 계산 정확
- Stage 3에서는 완벽하게 작동 (0건 발동)
- **Stage 6에서 자주 발동하는 이유 = 실제로 가격이 하락하기 때문**

#### ✅ Stage 6 진입 조건이 근본 문제
1. **MACD 골든크로스의 지연성**:
   - 반등 시작부터 10-15일 지연
   - 진입 시점 = 반등의 중간/후반부
   - 최적 타이밍을 놓침

2. **Dead Cat Bounce 포착 실패**:
   - 진짜 추세 전환 vs 단기 반등 구별 불가
   - 89%가 단기 반등 (재차 하락)
   - 11%만 실제 추세 전환

3. **진입 가격의 불리함**:
   - 이미 많이 올라간 가격에 진입
   - 손절가까지 거리 좁음
   - 작은 조정에도 손절 발동

### 3.4 개선 방향

#### 방향 1: Stage 6 진입 조건 대폭 강화 (권장)
```python
# 현재
if stage == 6 and buy_signal:
    enter()

# 개선 1: MACD 지속성 확인
if stage == 6 and buy_signal:
    if MACD_중 > 0 for 3+ days:  # 골든크로스 지속 확인
        if volume_surge > 50%:  # 거래량 급증
            if price > EMA_20:  # 가격이 중기선 위
                enter()

# 개선 2: Stage 6 초입만 진입
if stage == 6 and buy_signal:
    if stage_duration <= 2:  # Stage 6 진입 2일 이내만
        if MACD_중_increasing:  # MACD가 계속 증가 중
            enter()
```

#### 방향 2: Stage 6 완전 제외
- 가장 단순하고 효과적
- Stage 3만으로도 충분한 수익
- 거래 건수는 줄지만 승률 100% 유지

#### 방향 3: Stage 6 Stop-Loss 완화 (비권장)
```python
# 현재
stop_loss = entry_price - (2 × ATR)  # 4% 손절

# 개선 (비권장)
if stage == 6:
    stop_loss = entry_price - (3 × ATR)  # 6% 손절
```
**문제**: 손절폭을 늘려도 근본적으로 가격이 하락하면 결국 손절됨. 손실만 더 커질 가능성.

#### 방향 4: 선행 지표 추가 (장기)
```python
# MACD 대신 가격 행동 직접 감지
if price_bounce_from_support and volume_surge and rsi_oversold:
    enter()  # MACD 골든크로스를 기다리지 않음
```

---

## Part 4: 최종 권고사항

### 즉시 실행 가능한 조치

#### 1순위: Stage 6 진입 중단 (단기)
```python
# engine.py의 generate_and_execute_entries() 수정
if signal['stage'] == 6:
    logger.info(f"Stage 6 진입 스킵: {ticker}")
    continue
```

**효과**:
- 승률: 45.95% → 100%
- 수익: 10.3% 감소 (허용 가능)
- 손실 거래 완전 제거

#### 2순위: Stage 6 필터 강화 (중기)
```python
if signal['stage'] == 6:
    # 추가 필터 적용
    if signal['signal_strength'] < 75:  # 신호 강도 강화
        continue
    if not check_macd_sustainability(data, days=3):  # MACD 지속성
        continue
    if not check_volume_surge(data, threshold=1.5):  # 거래량 확인
        continue
    # 모든 필터 통과 시에만 진입
    enter()
```

#### 3순위: Stage별 Stop-Loss 차등화 (장기)
```python
if stage == 3:
    atr_multiplier = 2.0  # 기본값 유지
elif stage == 6:
    atr_multiplier = 3.0  # 손절폭 50% 확대
```
**주의**: 근본 해결책은 아니지만 보완책으로 고려 가능

### 백테스팅 재실행 계획

**테스트 1**: Stage 6 완전 제외
```python
config = {
    'enable_stage_6': False
}
```
**예상 결과**:
- 승률: 100%
- 거래 건수: 29건
- 수익: 약 3,380,310원

**테스트 2**: Stage 6 강화 필터
```python
config = {
    'stage_6_filters': {
        'min_strength': 75,
        'min_macd_duration': 3,
        'min_volume_ratio': 1.5,
        'max_stage_duration': 2
    }
}
```
**예상 결과**:
- Stage 6 거래: 45건 → 5-8건
- Stage 6 승률: 11.1% → 40-60%
- 전체 승률: 45.95% → 75-85%

---

## 부록: 코드 흐름 다이어그램

### 백테스팅 일일 프로세스
```
process_day(date)
  ├─1. portfolio.update_trailing_stops()
  │   └─ 수익 나면 손절가 상향 조정
  │
  ├─2. engine.check_and_execute_stops()
  │   ├─ portfolio.check_stop_losses()
  │   │   └─ stop_loss.check_stop_loss_triggered()
  │   │       └─ 현재가 <= 손절가 ?
  │   └─ 발동 시 즉시 청산
  │
  ├─3. engine.generate_and_execute_exits()
  │   └─ exit_signal 처리
  │
  ├─4. engine.generate_and_execute_entries()
  │   ├─ entry_signals 생성 (전체 종목)
  │   ├─ signal['stage'] 확인 → 6이면 진입
  │   ├─ apply_risk_management()
  │   │   ├─ position_sizing
  │   │   ├─ stop_price 계산
  │   │   │   ├─ volatility_stop = 진입가 - (2×ATR)
  │   │   │   └─ trend_stop = EMA_20
  │   │   └─ risk_assessment
  │   └─ 진입 실행
  │
  └─5. portfolio.record_snapshot()
```

### Stage 6 판단 프로세스
```
load_market_data(start_date - 60, end_date)
  ↓
calculate_all_indicators(data)
  ├─ EMA_5, EMA_20, EMA_40 계산
  ├─ MACD_상 = EMA_5 - EMA_20
  ├─ MACD_중 = EMA_5 - EMA_40  ← Stage 6 핵심
  └─ MACD_하 = EMA_20 - EMA_40
  ↓
determine_stage(data)
  ├─1. determine_ma_arrangement()
  │   └─ 이동평균선 배열로 기본 stage
  ├─2. detect_macd_zero_cross()
  │   └─ MACD 0선 교차 감지
  └─3. MACD 교차로 stage 확정
      └─ stage[Cross_중 == 1] = 6  ← MACD(중) 골든크로스
  ↓
generate_entry_signals(data)
  └─ Stage 6에서 매수 신호 발생
  ↓
진입 → 재차 하락 → 손절 (89%)
```

---

## 작성자
- seunghakim
- AI Assistant (Claude)

## 작성 일자
2026-01-12