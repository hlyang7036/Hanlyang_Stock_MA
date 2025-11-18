# Level 6 백테스팅 엔진 계획

## 날짜
2025-11-16

## 계획 개요
Level 1-5에서 구현된 데이터 수집, 지표 계산, 스테이지 분석, 시그널 생성, 리스크 관리 모듈을 통합하여
과거 데이터 기반 전략 성과 검증 시스템을 구축합니다.

**핵심 특징**:
- **전체 시장 스캔 방식**: 매 거래일마다 코스피/코스닥 전체 종목(약 2,400개)을 스캔하여 진입/청산 신호가 발생한 종목만 거래
- **종목 제한 없음**: 특정 종목을 미리 정하지 않고, 신호 기반으로 동적 선택
- **포트폴리오 제한 제외**: Level 5-3의 포트폴리오 제한(단일/상관관계/분산 제한)은 적용하지 않음
- **자본 제약**: 현금이 허락하는 한 무제한 보유 가능

---

## 모듈 구조

```
src/backtest/
├── __init__.py              # 패키지 초기화
├── engine.py                # 백테스팅 메인 엔진 (3개 클래스)
├── portfolio.py             # 포트폴리오 관리 (2개 클래스)
├── execution.py             # 주문 실행 시뮬레이션 (2개 클래스 + 1개 함수)
├── data_manager.py          # 멀티 종목 데이터 관리 (1개 클래스)
└── analytics.py             # 성과 분석 (1개 클래스)

src/tests/backtest/
├── conftest.py              # 테스트 픽스처
├── test_portfolio.py        # 포트폴리오 테스트
├── test_execution.py        # 실행 엔진 테스트
├── test_data_manager.py     # 데이터 관리자 테스트
├── test_engine.py           # 백테스팅 엔진 테스트
└── test_analytics.py        # 성과 분석 테스트
```

**핵심 컴포넌트**: 5개 모듈, 9개 클래스, 다수 함수

---

## 아키텍처 설계

### 데이터 흐름

```
┌─────────────────────────────────────────────────────────────┐
│                    백테스팅 데이터 흐름                        │
└─────────────────────────────────────────────────────────────┘

1. 초기화 단계
   DataManager: 전체 시장 종목 코드 조회 (코스피 + 코스닥)
        ↓
   각 종목별 과거 데이터 로딩 (Level 1, 병렬 처리)
        ↓
   지표 계산 (Level 2: calculate_all_indicators)
        ↓
   스테이지 분석 (Level 3: determine_stage)
        ↓
   [준비된 시장 데이터: 약 2,400개 종목의 OHLCV + 지표 + 스테이지]

2. 일별 거래 루프 (각 거래일마다)
   ┌─────────────────────────────────────────────┐
   │ Portfolio: 포트폴리오 가치 업데이트          │
   │  - 모든 보유 포지션의 현재가 반영             │
   │  - 자산 총액 = 현금 + 포지션 평가액          │
   └─────────────────────────────────────────────┘
        ↓
   ┌─────────────────────────────────────────────┐
   │ Portfolio: 손절가 체크 (모든 포지션)         │
   │  - Level 5-2: check_stop_loss_triggered()   │
   │  - 트레일링 스톱 업데이트                     │
   │  - 손절 발동 시 청산 주문 생성                │
   └─────────────────────────────────────────────┘
        ↓
   ┌─────────────────────────────────────────────┐
   │ Level 4: 청산 신호 생성                      │
   │  - generate_exit_signal()                   │
   │  - 3단계 청산: 히스토그램/MACD/크로스        │
   └─────────────────────────────────────────────┘
        ↓
   ┌─────────────────────────────────────────────┐
   │ ExecutionEngine: 청산 주문 실행              │
   │  - 슬리피지 적용                             │
   │  - 수수료 계산                               │
   │  - 포트폴리오 업데이트 (포지션 감소/제거)     │
   └─────────────────────────────────────────────┘
        ↓
   ┌─────────────────────────────────────────────┐
   │ Level 4: 진입 신호 생성 (전체 종목 스캔)      │
   │  - 모든 종목(~2,400개)에 대해:              │
   │    • generate_entry_signals()              │
   │    • evaluate_signal_strength()            │
   │    • filter_signals_by_stage()             │
   │  - 신호가 발생한 종목만 선별                  │
   └─────────────────────────────────────────────┘
        ↓
   ┌─────────────────────────────────────────────┐
   │ Level 5: 리스크 관리 적용 (간소화)           │
   │  - 포지션 사이징 (Level 5-1)                │
   │  - 손절가 계산 (Level 5-2)                  │
   │  - 리스크 평가 (Level 5-4)                  │
   │  ※ 포트폴리오 제한 체크(Level 5-3) 제외      │
   └─────────────────────────────────────────────┘
        ↓
   ┌─────────────────────────────────────────────┐
   │ ExecutionEngine: 진입 주문 실행              │
   │  - 승인된 주문만 실행                         │
   │  - 슬리피지 적용                             │
   │  - 수수료 계산                               │
   │  - 포트폴리오 업데이트 (포지션 추가/증가)     │
   └─────────────────────────────────────────────┘
        ↓
   ┌─────────────────────────────────────────────┐
   │ Portfolio: 거래 기록                         │
   │  - 모든 체결 내역 저장                        │
   │  - 일별 자산 스냅샷 저장                      │
   └─────────────────────────────────────────────┘

3. 백테스팅 종료
   PerformanceAnalyzer: 성과 분석
        ↓
   리포트 생성 (수익률, MDD, Sharpe, 거래 통계)
        ↓
   차트 생성 (자산곡선, 낙폭, 월별 수익률)
        ↓
   거래 내역 export (CSV/JSON)
```

### 신호 우선순위

백테스팅 엔진은 매일 다음 순서로 신호를 처리합니다:

1. **손절 발동 체크** (최우선)
   - 모든 보유 포지션의 손절가 체크
   - 손절 발동 시 즉시 청산

2. **청산 신호** (2순위)
   - Level 4의 `generate_exit_signal()` 실행
   - 히스토그램 피크아웃, MACD 피크아웃, 크로스 감지

3. **진입 신호** (3순위)
   - 청산 완료 후 새로운 진입 신호 생성
   - Level 5 리스크 관리 승인 후에만 진입

---

## Level 6-1: 포트폴리오 관리 (portfolio.py)

### 핵심 개념

**포트폴리오**: 현금 + 보유 포지션의 집합
**포지션**: 특정 종목의 보유 내역 (진입가, 수량, 손절가 등)

백테스팅에서는 실제 거래와 동일하게 포트폴리오 상태를 추적하고 업데이트해야 합니다.

---

### 클래스 1: Position

```python
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

@dataclass
class Position:
    """
    개별 포지션 정보

    Attributes:
        ticker: 종목코드
        position_type: 'long' 또는 'short'
        entry_date: 진입 날짜
        entry_price: 진입 평균가
        shares: 보유 주식 수
        units: 유닛 수 (터틀 트레이딩)
        stop_price: 손절가
        stop_type: 손절 유형 ('volatility' or 'trend')
        highest_price: 진입 후 최고가 (매수 포지션)
        lowest_price: 진입 후 최저가 (매도 포지션)
        signal_strength: 진입 시 신호 강도
        stage_at_entry: 진입 시 스테이지

    Methods:
        current_value(current_price): 현재 포지션 가치
        unrealized_pnl(current_price): 미실현 손익
        realized_pnl(exit_price): 실현 손익 (청산 시)
        update_extremes(current_price): 최고가/최저가 업데이트
    """
```

**메서드 명세**:

#### Position.current_value()

```python
def current_value(self, current_price: float) -> float:
    """
    현재 포지션 가치 계산

    Args:
        current_price: 현재가

    Returns:
        float: 포지션 평가액 (원)

    Notes:
        매수 포지션: shares × current_price
        매도 포지션: shares × (2 × entry_price - current_price)

    Examples:
        >>> position = Position(ticker='005930', position_type='long',
        ...                     entry_price=50000, shares=100, ...)
        >>> position.current_value(52000)
        5200000
    """
    if self.position_type == 'long':
        return self.shares * current_price
    else:  # short
        # 공매도는 진입가와 현재가 차이만큼 손익
        return self.shares * (2 * self.entry_price - current_price)
```

#### Position.unrealized_pnl()

```python
def unrealized_pnl(self, current_price: float) -> float:
    """
    미실현 손익 계산

    Args:
        current_price: 현재가

    Returns:
        float: 미실현 손익 (원)

    Examples:
        >>> position = Position(ticker='005930', position_type='long',
        ...                     entry_price=50000, shares=100, ...)
        >>> position.unrealized_pnl(52000)  # 2000원 × 100주
        200000
    """
    if self.position_type == 'long':
        return (current_price - self.entry_price) * self.shares
    else:  # short
        return (self.entry_price - current_price) * self.shares
```

#### Position.realized_pnl()

```python
def realized_pnl(self, exit_price: float, shares: int = None) -> float:
    """
    실현 손익 계산 (청산 시)

    Args:
        exit_price: 청산가
        shares: 청산 주식 수 (None이면 전체 청산)

    Returns:
        float: 실현 손익 (원)

    Examples:
        >>> position = Position(ticker='005930', position_type='long',
        ...                     entry_price=50000, shares=100, ...)
        >>> position.realized_pnl(52000)  # 전체 청산
        200000
        >>> position.realized_pnl(52000, 50)  # 부분 청산
        100000
    """
    if shares is None:
        shares = self.shares

    if self.position_type == 'long':
        return (exit_price - self.entry_price) * shares
    else:  # short
        return (self.entry_price - exit_price) * shares
```

#### Position.update_extremes()

```python
def update_extremes(self, current_price: float) -> None:
    """
    최고가/최저가 업데이트 (트레일링 스톱용)

    Args:
        current_price: 현재가

    Notes:
        매수 포지션: 최고가 갱신 시 highest_price 업데이트
        매도 포지션: 최저가 갱신 시 lowest_price 업데이트
    """
    if self.position_type == 'long':
        if self.highest_price is None or current_price > self.highest_price:
            self.highest_price = current_price
    else:  # short
        if self.lowest_price is None or current_price < self.lowest_price:
            self.lowest_price = current_price
```

---

### 클래스 2: Portfolio

```python
from typing import Dict, List, Optional
from datetime import datetime
import pandas as pd

class Portfolio:
    """
    포트폴리오 관리 클래스

    Attributes:
        initial_capital: 초기 자본금
        cash: 현금 잔고
        positions: 보유 포지션 딕셔너리 {ticker: Position}
        closed_positions: 청산된 포지션 리스트
        history: 포트폴리오 스냅샷 히스토리
        trades: 모든 거래 내역

    Methods:
        # 포지션 관리
        add_position(position, cost): 포지션 추가
        update_position(ticker, shares, price): 포지션 업데이트 (추가 매수/매도)
        close_position(ticker, exit_price, shares, reason): 포지션 청산

        # 가치 계산
        calculate_equity(current_prices): 총 자산 계산
        get_available_capital(): 사용 가능 자본

        # 손절 관리
        check_stop_losses(current_prices, market_data): 손절가 체크
        update_trailing_stops(current_prices, market_data): 트레일링 스톱 업데이트

        # 기록
        record_snapshot(date, current_prices): 일별 스냅샷 저장
        record_trade(trade_info): 거래 기록

        # 조회
        get_position(ticker): 포지션 조회
        get_total_units(): 총 유닛 수 (리스크 관리용)
        get_position_dict(): 포지션 딕셔너리 (ticker: units)
    """
```

**메서드 명세**:

#### Portfolio.add_position()

```python
def add_position(
    self,
    position: Position,
    cost: float
) -> bool:
    """
    새로운 포지션 추가

    Args:
        position: Position 객체
        cost: 총 비용 (주식 가격 + 수수료)

    Returns:
        bool: 추가 성공 여부

    Raises:
        ValueError: 현금 부족 시

    Examples:
        >>> portfolio = Portfolio(initial_capital=10_000_000)
        >>> position = Position(ticker='005930', ...)
        >>> portfolio.add_position(position, 5_000_000)
        True
    """
    if cost > self.cash:
        raise ValueError(f"현금 부족: 필요={cost:,.0f}, 보유={self.cash:,.0f}")

    # 기존 포지션이 있으면 업데이트 (평균가 계산)
    if position.ticker in self.positions:
        existing = self.positions[position.ticker]
        # 평균 진입가 계산
        total_shares = existing.shares + position.shares
        avg_price = (
            (existing.entry_price * existing.shares +
             position.entry_price * position.shares) / total_shares
        )
        existing.shares = total_shares
        existing.entry_price = avg_price
        existing.units += position.units
    else:
        self.positions[position.ticker] = position

    self.cash -= cost
    return True
```

#### Portfolio.close_position()

```python
def close_position(
    self,
    ticker: str,
    exit_price: float,
    shares: int = None,
    reason: str = None
) -> Dict[str, Any]:
    """
    포지션 청산

    Args:
        ticker: 종목코드
        exit_price: 청산가
        shares: 청산 주식 수 (None이면 전체 청산)
        reason: 청산 사유 ('stop_loss', 'exit_signal', 'stage_change' 등)

    Returns:
        Dict: 청산 결과
            - ticker: 종목코드
            - shares: 청산 수량
            - entry_price: 진입가
            - exit_price: 청산가
            - pnl: 실현 손익
            - return_pct: 수익률 (%)
            - holding_days: 보유 기간
            - reason: 청산 사유

    Raises:
        ValueError: 포지션이 없거나 청산 수량이 보유량 초과 시
    """
    if ticker not in self.positions:
        raise ValueError(f"포지션이 없습니다: {ticker}")

    position = self.positions[ticker]

    if shares is None:
        shares = position.shares

    if shares > position.shares:
        raise ValueError(
            f"청산 수량 초과: 요청={shares}, 보유={position.shares}"
        )

    # 손익 계산
    pnl = position.realized_pnl(exit_price, shares)
    return_pct = (exit_price / position.entry_price - 1) * 100

    # 현금 회수 (매도 대금 - 수수료)
    proceeds = shares * exit_price
    commission = proceeds * self.commission_rate
    self.cash += (proceeds - commission)

    # 포지션 업데이트 또는 제거
    if shares == position.shares:
        # 전체 청산
        closed_position = self.positions.pop(ticker)
        self.closed_positions.append(closed_position)
    else:
        # 부분 청산
        position.shares -= shares
        position.units = int(position.units * (position.shares / (position.shares + shares)))

    # 거래 기록
    trade_result = {
        'ticker': ticker,
        'action': 'sell',
        'shares': shares,
        'entry_price': position.entry_price,
        'exit_price': exit_price,
        'pnl': pnl,
        'return_pct': return_pct,
        'holding_days': (datetime.now() - position.entry_date).days,
        'reason': reason,
        'commission': commission
    }

    self.record_trade(trade_result)

    return trade_result
```

#### Portfolio.calculate_equity()

```python
def calculate_equity(
    self,
    current_prices: Dict[str, float]
) -> float:
    """
    총 자산 계산

    Args:
        current_prices: 현재가 딕셔너리 {ticker: price}

    Returns:
        float: 총 자산 (현금 + 포지션 평가액)

    Examples:
        >>> portfolio.calculate_equity({'005930': 52000, '000660': 105000})
        10500000
    """
    positions_value = sum(
        position.current_value(current_prices.get(ticker, position.entry_price))
        for ticker, position in self.positions.items()
    )
    return self.cash + positions_value
```

#### Portfolio.check_stop_losses()

```python
def check_stop_losses(
    self,
    current_prices: Dict[str, float],
    market_data: Dict[str, pd.DataFrame]
) -> List[Dict[str, Any]]:
    """
    모든 포지션의 손절가 체크

    Args:
        current_prices: 현재가 딕셔너리
        market_data: 시장 데이터 딕셔너리 (ATR, MA 등 포함)

    Returns:
        List[Dict]: 손절 발동 포지션 리스트
            각 항목: {
                'ticker': str,
                'stop_price': float,
                'current_price': float,
                'stop_type': str
            }

    Notes:
        Level 5-2의 check_stop_loss_triggered() 활용
    """
    from src.analysis.risk.stop_loss import check_stop_loss_triggered

    triggered = []

    for ticker, position in self.positions.items():
        current_price = current_prices.get(ticker)
        if current_price is None:
            continue

        # 손절 발동 체크
        is_triggered = check_stop_loss_triggered(
            current_price=current_price,
            stop_price=position.stop_price,
            position_type=position.position_type
        )

        if is_triggered:
            triggered.append({
                'ticker': ticker,
                'stop_price': position.stop_price,
                'current_price': current_price,
                'stop_type': position.stop_type
            })

    return triggered
```

#### Portfolio.update_trailing_stops()

```python
def update_trailing_stops(
    self,
    current_prices: Dict[str, float],
    market_data: Dict[str, pd.DataFrame]
) -> None:
    """
    트레일링 스톱 업데이트

    Args:
        current_prices: 현재가 딕셔너리
        market_data: 시장 데이터 딕셔너리 (ATR 포함)

    Notes:
        - 각 포지션의 최고가/최저가 업데이트
        - Level 5-2의 update_trailing_stop() 활용하여 손절가 조정
    """
    from src.analysis.risk.stop_loss import update_trailing_stop

    for ticker, position in self.positions.items():
        current_price = current_prices.get(ticker)
        if current_price is None:
            continue

        # 최고가/최저가 업데이트
        position.update_extremes(current_price)

        # ATR 조회
        data = market_data.get(ticker)
        if data is None or 'ATR' not in data.columns:
            continue

        latest_atr = data['ATR'].iloc[-1]

        # 트레일링 스톱 계산
        if position.position_type == 'long' and position.highest_price:
            new_stop = update_trailing_stop(
                entry_price=position.entry_price,
                highest_price=position.highest_price,
                current_stop=position.stop_price,
                atr=latest_atr,
                position_type='long'
            )
            position.stop_price = max(position.stop_price, new_stop)

        elif position.position_type == 'short' and position.lowest_price:
            new_stop = update_trailing_stop(
                entry_price=position.entry_price,
                highest_price=position.lowest_price,  # 매도는 lowest 사용
                current_stop=position.stop_price,
                atr=latest_atr,
                position_type='short'
            )
            position.stop_price = min(position.stop_price, new_stop)
```

#### Portfolio.get_position_dict()

```python
def get_position_dict(self) -> Dict[str, int]:
    """
    리스크 관리용 포지션 딕셔너리 반환

    Returns:
        Dict[str, int]: {ticker: units}

    Notes:
        Level 5의 apply_risk_management()에 전달하기 위한 형식
    """
    return {
        ticker: position.units
        for ticker, position in self.positions.items()
    }
```

---

## Level 6-2: 주문 실행 시뮬레이션 (execution.py)

### 핵심 개념

백테스팅에서는 실제 주문 체결을 시뮬레이션해야 합니다. 슬리피지(가격 미끄러짐)와 수수료를 반영하여
현실적인 체결 가격을 계산합니다.

---

### 클래스 1: Order

```python
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

@dataclass
class Order:
    """
    주문 정보

    Attributes:
        ticker: 종목코드
        action: 'buy' 또는 'sell'
        shares: 주식 수
        order_type: 주문 유형 ('market', 'limit')
        limit_price: 지정가 (limit 주문 시)
        timestamp: 주문 시각
        position_type: 포지션 유형 ('long', 'short')
        units: 유닛 수
        stop_price: 손절가
        signal_strength: 신호 강도
        reason: 주문 사유
    """
    ticker: str
    action: str  # 'buy' or 'sell'
    shares: int
    order_type: str = 'market'  # 'market' or 'limit'
    limit_price: Optional[float] = None
    timestamp: datetime = None
    position_type: str = 'long'  # 'long' or 'short'
    units: int = 0
    stop_price: float = 0.0
    signal_strength: int = 0
    reason: str = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()
```

---

### 클래스 2: ExecutionEngine

```python
class ExecutionEngine:
    """
    주문 실행 엔진

    백테스팅에서 주문 체결을 시뮬레이션합니다.
    슬리피지와 수수료를 반영한 실제 체결가를 계산합니다.

    Attributes:
        commission_rate: 수수료율 (기본값: 0.00015 = 0.015%)
        slippage_pct: 슬리피지 비율 (기본값: 0.001 = 0.1%)

    Methods:
        execute(order, market_price): 주문 실행
        calculate_fill_price(order, market_price): 체결가 계산
        calculate_commission(fill_price, shares): 수수료 계산
        calculate_total_cost(fill_price, shares, commission): 총 비용 계산
    """

    def __init__(
        self,
        commission_rate: float = 0.00015,
        slippage_pct: float = 0.001
    ):
        self.commission_rate = commission_rate
        self.slippage_pct = slippage_pct
```

**메서드 명세**:

#### ExecutionEngine.execute()

```python
def execute(
    self,
    order: Order,
    market_price: float
) -> Dict[str, Any]:
    """
    주문 실행

    Args:
        order: Order 객체
        market_price: 시장가 (현재가)

    Returns:
        Dict: 체결 결과
            - filled: 체결 여부 (bool)
            - fill_price: 체결가
            - shares: 체결 수량
            - commission: 수수료
            - total_cost: 총 비용 (매수) 또는 총 수령액 (매도)
            - slippage: 슬리피지 금액

    Examples:
        >>> engine = ExecutionEngine()
        >>> order = Order(ticker='005930', action='buy', shares=100)
        >>> result = engine.execute(order, 50000)
        >>> result
        {
            'filled': True,
            'fill_price': 50050.0,  # 0.1% 슬리피지
            'shares': 100,
            'commission': 7.5,      # 0.015%
            'total_cost': 5005007.5,
            'slippage': 50.0
        }
    """
    # 체결가 계산 (슬리피지 포함)
    fill_price = self.calculate_fill_price(order, market_price)

    # 수수료 계산
    commission = self.calculate_commission(fill_price, order.shares)

    # 총 비용/수령액 계산
    if order.action == 'buy':
        total_cost = fill_price * order.shares + commission
    else:  # sell
        total_cost = fill_price * order.shares - commission

    # 슬리피지 금액
    slippage = abs(fill_price - market_price) * order.shares

    return {
        'filled': True,
        'fill_price': fill_price,
        'shares': order.shares,
        'commission': commission,
        'total_cost': total_cost if order.action == 'buy' else -total_cost,
        'slippage': slippage,
        'ticker': order.ticker,
        'action': order.action,
        'timestamp': order.timestamp
    }
```

#### ExecutionEngine.calculate_fill_price()

```python
def calculate_fill_price(
    self,
    order: Order,
    market_price: float
) -> float:
    """
    체결가 계산 (슬리피지 반영)

    Args:
        order: Order 객체
        market_price: 시장가

    Returns:
        float: 체결가

    Notes:
        매수: 시장가 + 슬리피지 (불리하게)
        매도: 시장가 - 슬리피지 (불리하게)

    Examples:
        >>> engine = ExecutionEngine(slippage_pct=0.001)
        >>> order = Order(action='buy', ...)
        >>> engine.calculate_fill_price(order, 50000)
        50050.0

        >>> order = Order(action='sell', ...)
        >>> engine.calculate_fill_price(order, 50000)
        49950.0
    """
    if order.action == 'buy':
        # 매수: 시장가보다 높게 체결 (불리)
        return market_price * (1 + self.slippage_pct)
    else:  # sell
        # 매도: 시장가보다 낮게 체결 (불리)
        return market_price * (1 - self.slippage_pct)
```

#### ExecutionEngine.calculate_commission()

```python
def calculate_commission(
    self,
    fill_price: float,
    shares: int
) -> float:
    """
    수수료 계산

    Args:
        fill_price: 체결가
        shares: 주식 수

    Returns:
        float: 수수료 (원)

    Notes:
        한국 증권사 수수료율: 약 0.015% (온라인)
        최소 수수료: 없음 (소액 거래도 비율만 적용)

    Examples:
        >>> engine = ExecutionEngine(commission_rate=0.00015)
        >>> engine.calculate_commission(50000, 100)
        7.5
    """
    return fill_price * shares * self.commission_rate
```

---

## Level 6-3: 데이터 관리 (data_manager.py)

### 핵심 개념

**전체 시장 스캔 방식**:
- 코스피/코스닥 전체 종목 코드를 조회하여 모든 종목의 과거 데이터를 로드
- 약 2,400개 종목의 데이터를 병렬 처리로 효율적으로 로딩
- 지표 계산 결과를 캐싱하여 반복 실행 시 성능 향상
- 데이터 로딩 실패 종목(상장폐지, 데이터 없음 등)은 자동 제외

---

### 클래스: DataManager

```python
class DataManager:
    """
    전체 시장 데이터 관리

    Attributes:
        cache_dir: 캐시 디렉토리 경로
        use_cache: 캐시 사용 여부

    Methods:
        get_all_market_tickers(market): 전체 시장 종목 코드 조회
        load_market_data(start_date, end_date, market): 전체 시장 데이터 로드
        load_data(tickers, start_date, end_date): 특정 종목 데이터 로드
        calculate_indicators(data_dict): 모든 종목의 지표 계산
        align_dates(data_dict): 날짜 정렬
        cache_data(ticker, data): 데이터 캐싱
        load_cached_data(ticker, start_date, end_date): 캐시 로드
        clear_cache(ticker): 캐시 삭제
    """
```

**메서드 명세**:

#### DataManager.get_all_market_tickers()

```python
def get_all_market_tickers(
    self,
    market: str = 'ALL'
) -> List[str]:
    """
    전체 시장 종목 코드 조회

    Args:
        market: 시장 구분
            - 'KOSPI': 코스피만
            - 'KOSDAQ': 코스닥만
            - 'ALL': 코스피 + 코스닥 (기본값)

    Returns:
        List[str]: 종목코드 리스트

    Notes:
        - pykrx 또는 FinanceDataReader 활용
        - 상장폐지 종목 제외
        - ETF, ETN 등 제외 가능 (옵션)

    Examples:
        >>> manager = DataManager()
        >>> tickers = manager.get_all_market_tickers('KOSPI')
        >>> len(tickers)
        900  # 대략적인 숫자

        >>> all_tickers = manager.get_all_market_tickers('ALL')
        >>> len(all_tickers)
        2400  # 코스피 + 코스닥
    """
    import FinanceDataReader as fdr

    if market == 'KOSPI':
        df = fdr.StockListing('KOSPI')
    elif market == 'KOSDAQ':
        df = fdr.StockListing('KOSDAQ')
    else:  # 'ALL'
        kospi = fdr.StockListing('KOSPI')
        kosdaq = fdr.StockListing('KOSDAQ')
        df = pd.concat([kospi, kosdaq], ignore_index=True)

    # 종목코드만 추출
    tickers = df['Code'].tolist()

    logger.info(f"{market} 시장 종목 수: {len(tickers)}개")

    return tickers
```

---

#### DataManager.load_market_data()

```python
def load_market_data(
    self,
    start_date: str,
    end_date: str,
    market: str = 'ALL',
    max_workers: int = 10
) -> Dict[str, pd.DataFrame]:
    """
    전체 시장 데이터 로드 (병렬 처리)

    Args:
        start_date: 시작일 (YYYY-MM-DD)
        end_date: 종료일 (YYYY-MM-DD)
        market: 시장 구분 ('KOSPI', 'KOSDAQ', 'ALL')
        max_workers: 병렬 처리 워커 수 (기본값: 10)

    Returns:
        Dict[str, pd.DataFrame]: {ticker: DataFrame}
            - 데이터 로딩에 실패한 종목은 제외됨
            - 각 DataFrame은 OHLCV + 지표 + 스테이지 포함

    Notes:
        - concurrent.futures.ThreadPoolExecutor 활용
        - 진행 상황 로깅 (매 100개마다)
        - 실패한 종목은 경고 로그 후 제외

    Examples:
        >>> manager = DataManager()
        >>> data = manager.load_market_data(
        ...     start_date='2020-01-01',
        ...     end_date='2023-12-31',
        ...     market='ALL'
        ... )
        >>> len(data)
        2156  # 실제 데이터가 있는 종목만 (2400개 중)
    """
    from concurrent.futures import ThreadPoolExecutor, as_completed
    from tqdm import tqdm

    # 전체 종목 코드 조회
    tickers = self.get_all_market_tickers(market)

    logger.info(f"데이터 로딩 시작: {len(tickers)}개 종목")

    result = {}
    failed = []

    # 병렬 처리
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        # 각 종목별로 load_data 태스크 제출
        future_to_ticker = {
            executor.submit(self.load_data, [ticker], start_date, end_date): ticker
            for ticker in tickers
        }

        # 진행 상황 표시
        with tqdm(total=len(tickers), desc="데이터 로딩") as pbar:
            for future in as_completed(future_to_ticker):
                ticker = future_to_ticker[future]
                try:
                    data_dict = future.result()
                    if ticker in data_dict and not data_dict[ticker].empty:
                        result[ticker] = data_dict[ticker]
                    else:
                        failed.append(ticker)
                except Exception as e:
                    logger.warning(f"데이터 로딩 실패: {ticker} - {e}")
                    failed.append(ticker)
                finally:
                    pbar.update(1)

    logger.info(f"데이터 로딩 완료: 성공 {len(result)}개, 실패 {len(failed)}개")

    if failed:
        logger.debug(f"실패 종목 샘플: {failed[:10]}")

    return result
```

---

#### DataManager.load_data()

```python
def load_data(
    self,
    tickers: List[str],
    start_date: str,
    end_date: str,
    calculate_indicators: bool = True
) -> Dict[str, pd.DataFrame]:
    """
    멀티 종목 데이터 로드

    Args:
        tickers: 종목코드 리스트
        start_date: 시작일 (YYYY-MM-DD)
        end_date: 종료일 (YYYY-MM-DD)
        calculate_indicators: 지표 계산 여부

    Returns:
        Dict[str, pd.DataFrame]: {ticker: DataFrame}
            각 DataFrame은 OHLCV + 지표 + 스테이지 포함

    Notes:
        - Level 1의 get_multiple_stocks() 활용
        - Level 2의 calculate_all_indicators() 활용
        - Level 3의 determine_stage() 활용
        - 캐시가 있으면 캐시에서 로드

    Examples:
        >>> manager = DataManager()
        >>> data = manager.load_data(
        ...     ['005930', '000660'],
        ...     '2020-01-01',
        ...     '2023-12-31'
        ... )
        >>> data['005930'].columns
        Index(['Open', 'High', 'Low', 'Close', 'Volume',
               'EMA_5', 'EMA_20', 'EMA_40', 'MACD_상', ..., 'Stage'])
    """
    from src.data.collector import get_multiple_stocks
    from src.analysis.technical.indicators import calculate_all_indicators
    from src.analysis.stage import determine_stage, detect_stage_transition

    result = {}

    for ticker in tickers:
        # 캐시 확인
        if self.use_cache:
            cached = self.load_cached_data(ticker, start_date, end_date)
            if cached is not None:
                result[ticker] = cached
                continue

        # 데이터 로드
        data = get_stock_data(
            ticker=ticker,
            start_date=start_date,
            end_date=end_date
        )

        if calculate_indicators:
            # 지표 계산
            data = calculate_all_indicators(data)

            # 스테이지 분석
            data['Stage'] = determine_stage(data)
            data['Stage_Transition'] = detect_stage_transition(data)

        # 캐싱
        if self.use_cache:
            self.cache_data(ticker, data)

        result[ticker] = data

    return result
```

---

## Level 6-4: 백테스팅 엔진 (engine.py)

### 핵심 개념

백테스팅 엔진은 모든 컴포넌트를 조합하여 과거 데이터 기반 시뮬레이션을 실행합니다.
매 거래일마다 신호 생성 → 리스크 관리 → 주문 실행 프로세스를 반복합니다.

---

### 클래스: BacktestEngine

```python
class BacktestEngine:
    """
    백테스팅 메인 엔진

    Attributes:
        config: 백테스팅 설정
        portfolio: Portfolio 객체
        execution_engine: ExecutionEngine 객체
        data_manager: DataManager 객체
        market_data: 시장 데이터 딕셔너리
        current_date: 현재 시뮬레이션 날짜

    Methods:
        run_backtest(tickers, start_date, end_date, initial_capital): 백테스팅 실행
        process_day(date): 특정 날짜 처리
        check_and_execute_stops(date): 손절 체크 및 실행
        generate_and_execute_exits(date): 청산 신호 생성 및 실행
        generate_and_execute_entries(date): 진입 신호 생성 및 실행
        get_results(): 백테스팅 결과 반환
    """
```

**메서드 명세**:

#### BacktestEngine.run_backtest()

```python
def run_backtest(
    self,
    start_date: str,
    end_date: str,
    initial_capital: float,
    market: str = 'ALL',
    config: Dict[str, Any] = None
) -> 'BacktestResult':
    """
    백테스팅 실행 (전체 시장 스캔 방식)

    Args:
        start_date: 시작일 (YYYY-MM-DD)
        end_date: 종료일 (YYYY-MM-DD)
        initial_capital: 초기 자본금
        market: 시장 구분 ('KOSPI', 'KOSDAQ', 'ALL')
        config: 백테스팅 설정

    Returns:
        BacktestResult: 백테스팅 결과 객체

    Process:
        1. 전체 시장 데이터 로드 (코스피/코스닥 전체)
        2. 포트폴리오 초기화
        3. 날짜별 루프:
            a. 손절 체크 → 청산
            b. 청산 신호 → 청산 (보유 종목만)
            c. 진입 신호 → 전체 종목 스캔 → 리스크 관리 → 진입
            d. 포트폴리오 스냅샷 기록
        4. 성과 분석

    Examples:
        >>> engine = BacktestEngine()
        >>> result = engine.run_backtest(
        ...     start_date='2020-01-01',
        ...     end_date='2023-12-31',
        ...     initial_capital=100_000_000,
        ...     market='ALL'  # 코스피 + 코스닥 전체
        ... )
        >>> print(result.summary())
        ========================================
        백테스팅 결과 요약
        ========================================
        시장: KOSPI + KOSDAQ (2,156개 종목)
        기간: 2020-01-01 ~ 2023-12-31
        초기 자본: 100,000,000원
        ...
    """
    logger.info(f"백테스팅 시작: {start_date} ~ {end_date}")
    logger.info(f"시장: {market}")
    logger.info(f"초기 자본: {initial_capital:,.0f}원")

    # 1. 전체 시장 데이터 로드
    self.market_data = self.data_manager.load_market_data(
        start_date=start_date,
        end_date=end_date,
        market=market
    )

    logger.info(f"데이터 로딩 완료: {len(self.market_data)}개 종목")

    # 2. 포트폴리오 초기화
    self.portfolio = Portfolio(
        initial_capital=initial_capital,
        commission_rate=config.get('commission_rate', 0.00015)
    )

    # 3. 날짜 리스트 생성 (모든 종목 데이터의 교집합)
    dates = self._get_common_dates()

    # 4. 날짜별 루프
    for date in dates:
        self.current_date = date
        self.process_day(date)

    # 5. 성과 분석
    result = self.get_results()

    logger.info("백테스팅 완료")
    logger.info(f"총 수익률: {result.total_return:.2%}")
    logger.info(f"최대 낙폭: {result.max_drawdown:.2%}")

    return result
```

#### BacktestEngine.process_day()

```python
def process_day(self, date: datetime) -> None:
    """
    특정 날짜 처리

    Args:
        date: 거래일

    Process:
        1. 포트폴리오 가치 업데이트
        2. 트레일링 스톱 업데이트
        3. 손절 체크 및 실행
        4. 청산 신호 처리
        5. 진입 신호 처리
        6. 스냅샷 기록
    """
    logger.debug(f"\n{'='*60}")
    logger.debug(f"날짜: {date.strftime('%Y-%m-%d')}")

    # 현재가 딕셔너리
    current_prices = self._get_current_prices(date)

    # 1. 포트폴리오 가치 업데이트
    equity = self.portfolio.calculate_equity(current_prices)
    logger.debug(f"총 자산: {equity:,.0f}원")

    # 2. 트레일링 스톱 업데이트
    self.portfolio.update_trailing_stops(current_prices, self.market_data)

    # 3. 손절 체크 및 실행
    self.check_and_execute_stops(date, current_prices)

    # 4. 청산 신호 처리
    self.generate_and_execute_exits(date, current_prices)

    # 5. 진입 신호 처리
    self.generate_and_execute_entries(date, current_prices)

    # 6. 스냅샷 기록
    self.portfolio.record_snapshot(date, current_prices)
```

#### BacktestEngine.check_and_execute_stops()

```python
def check_and_execute_stops(
    self,
    date: datetime,
    current_prices: Dict[str, float]
) -> None:
    """
    손절 체크 및 실행

    Args:
        date: 거래일
        current_prices: 현재가 딕셔너리
    """
    # 손절 발동 체크
    triggered = self.portfolio.check_stop_losses(
        current_prices=current_prices,
        market_data=self.market_data
    )

    if not triggered:
        return

    logger.info(f"손절 발동: {len(triggered)}건")

    # 손절 주문 실행
    for item in triggered:
        ticker = item['ticker']
        stop_price = item['stop_price']

        # 주문 생성
        position = self.portfolio.get_position(ticker)
        order = Order(
            ticker=ticker,
            action='sell',
            shares=position.shares,
            reason=f"stop_loss ({item['stop_type']})"
        )

        # 실행 (손절가로 체결)
        execution_result = self.execution_engine.execute(
            order=order,
            market_price=stop_price
        )

        # 포지션 청산
        close_result = self.portfolio.close_position(
            ticker=ticker,
            exit_price=execution_result['fill_price'],
            reason=order.reason
        )

        logger.info(
            f"손절 청산: {ticker} "
            f"손익={close_result['pnl']:,.0f}원 "
            f"({close_result['return_pct']:.2f}%)"
        )
```

#### BacktestEngine.generate_and_execute_entries()

```python
def generate_and_execute_entries(
    self,
    date: datetime,
    current_prices: Dict[str, float]
) -> None:
    """
    진입 신호 생성 및 실행 (전체 시장 스캔)

    Args:
        date: 거래일
        current_prices: 현재가 딕셔너리

    Process:
        1. 전체 종목(~2,400개)에 대해 진입 신호 생성 (Level 4)
           - 이미 보유 중인 종목은 스킵 (추가 매수 금지)
        2. 신호 강도 평가 및 필터링 (Level 4)
        3. 리스크 관리 적용 (Level 5, 포트폴리오 제한 제외)
           - 포지션 사이징 (Level 5-1)
           - 손절가 계산 (Level 5-2)
           - 리스크 평가 (Level 5-4)
        4. 승인된 주문 실행

    Notes:
        - 포트폴리오 제한(Level 5-3)은 적용하지 않음
        - 자본이 허락하는 한 무제한 보유 가능
    """
    from src.analysis.signal.entry import generate_entry_signals
    from src.analysis.signal.strength import evaluate_signal_strength
    from src.analysis.signal.filter import filter_signals_by_stage
    from src.analysis.risk import apply_risk_management

    signals = []

    # 1. 각 종목별 진입 신호 생성
    for ticker in self.market_data.keys():
        # 이미 보유 중이면 스킵 (추가 매수 금지)
        if ticker in self.portfolio.positions:
            continue

        data = self.market_data[ticker]
        date_idx = data.index.get_loc(date)

        # 해당 날짜까지의 데이터만 사용 (미래 데이터 사용 방지)
        historical_data = data.iloc[:date_idx + 1]

        # 진입 신호 생성
        entry_signals = generate_entry_signals(
            data=historical_data,
            enable_early=self.config.get('enable_early_signals', False)
        )

        latest_signal = entry_signals.iloc[-1]

        if latest_signal['Entry_Signal'] == 0:
            continue

        # 신호 강도 평가
        strength = evaluate_signal_strength(historical_data).iloc[-1]

        signals.append({
            'ticker': ticker,
            'action': 'buy' if latest_signal['Entry_Signal'] > 0 else 'sell',
            'signal_type': latest_signal['Signal_Type'],
            'signal_strength': int(strength),
            'current_price': current_prices[ticker],
            'stage': historical_data['Stage'].iloc[-1]
        })

    if not signals:
        return

    logger.debug(f"진입 신호 {len(signals)}건 발생")

    # 2. 각 신호에 대해 리스크 관리 적용 (포트폴리오 제한 제외)
    for signal in signals:
        ticker = signal['ticker']

        # 리스크 관리 적용
        # NOTE: 포트폴리오 제한(Level 5-3)은 체크하지 않음
        # config에서 skip_portfolio_limits=True로 설정하거나
        # apply_risk_management() 내부에서 조건부 스킵
        risk_result = apply_risk_management(
            signal=signal,
            account_balance=self.portfolio.calculate_equity(current_prices),
            positions=self.portfolio.get_position_dict(),
            market_data=self.market_data[ticker],
            config=self.config.get('risk_config')
        )

        # 승인되지 않으면 스킵
        if not risk_result['approved']:
            logger.debug(
                f"진입 거부: {ticker} - {risk_result.get('reason', 'unknown')}"
            )
            continue

        # 3. 주문 실행
        order = Order(
            ticker=ticker,
            action='buy',
            shares=risk_result['position_size'],
            position_type='long',
            units=risk_result['units'],
            stop_price=risk_result['stop_price'],
            signal_strength=signal['signal_strength'],
            reason=f"{signal['signal_type']} (Stage {signal['stage']})"
        )

        execution_result = self.execution_engine.execute(
            order=order,
            market_price=signal['current_price']
        )

        # 4. 포트폴리오에 포지션 추가
        position = Position(
            ticker=ticker,
            position_type='long',
            entry_date=date,
            entry_price=execution_result['fill_price'],
            shares=risk_result['position_size'],
            units=risk_result['units'],
            stop_price=risk_result['stop_price'],
            stop_type=risk_result['stop_type'],
            signal_strength=signal['signal_strength'],
            stage_at_entry=signal['stage']
        )

        self.portfolio.add_position(
            position=position,
            cost=execution_result['total_cost']
        )

        logger.info(
            f"진입: {ticker} "
            f"{risk_result['position_size']}주 @ {execution_result['fill_price']:,.0f}원 "
            f"(손절가: {risk_result['stop_price']:,.0f}원)"
        )
```

---

## Level 6-5: 성과 분석 (analytics.py)

### 핵심 개념

백테스팅 결과를 분석하여 전략의 수익성과 리스크를 평가합니다.

---

### 클래스: PerformanceAnalyzer

```python
class PerformanceAnalyzer:
    """
    성과 분석 클래스

    Attributes:
        portfolio_history: 포트폴리오 스냅샷 히스토리
        trades: 거래 내역
        initial_capital: 초기 자본

    Methods:
        calculate_returns(): 수익률 계산
        calculate_sharpe_ratio(): 샤프 비율
        calculate_max_drawdown(): 최대 낙폭
        calculate_win_rate(): 승률
        calculate_profit_factor(): 손익비
        generate_report(): 종합 리포트
        plot_equity_curve(): 자산곡선 차트
        plot_drawdown(): 낙폭 차트
        export_trades(filepath): 거래 내역 export
    """
```

**주요 메서드**:

#### PerformanceAnalyzer.calculate_returns()

```python
def calculate_returns(self) -> Dict[str, float]:
    """
    수익률 계산

    Returns:
        Dict: 수익률 지표
            - total_return: 총 수익률
            - cagr: 연환산 수익률
            - daily_return_mean: 일평균 수익률
            - daily_return_std: 일수익률 표준편차
            - monthly_returns: 월별 수익률
    """
```

#### PerformanceAnalyzer.calculate_sharpe_ratio()

```python
def calculate_sharpe_ratio(
    self,
    risk_free_rate: float = 0.03
) -> float:
    """
    샤프 비율 계산

    Args:
        risk_free_rate: 무위험 수익률 (연율)

    Returns:
        float: 샤프 비율

    Notes:
        Sharpe Ratio = (수익률 - 무위험수익률) / 변동성

        해석:
        - > 2.0: 매우 우수
        - 1.0 ~ 2.0: 우수
        - 0.5 ~ 1.0: 양호
        - < 0.5: 개선 필요
    """
```

#### PerformanceAnalyzer.calculate_max_drawdown()

```python
def calculate_max_drawdown(self) -> Dict[str, Any]:
    """
    최대 낙폭 계산

    Returns:
        Dict: MDD 정보
            - max_drawdown: 최대 낙폭 (%)
            - peak_date: 고점 날짜
            - trough_date: 저점 날짜
            - recovery_date: 회복 날짜 (None이면 미회복)
            - duration_days: 낙폭 기간 (일)

    Notes:
        MDD = (고점 - 저점) / 고점 × 100

        권장 기준:
        - < 10%: 매우 우수
        - 10% ~ 20%: 우수
        - 20% ~ 30%: 양호
        - > 30%: 개선 필요
    """
```

---

## 구현 순서

### Phase 1: 기본 인프라 (1주차)

**목표**: 포트폴리오와 주문 실행 기능 구현

1. **portfolio.py 구현**
   - Position 클래스 (2-3시간)
   - Portfolio 클래스 기본 기능 (4-5시간)
   - 테스트 작성 (~10개)

2. **execution.py 구현**
   - Order 클래스 (1시간)
   - ExecutionEngine 클래스 (2-3시간)
   - 테스트 작성 (~8개)

**예상 시간**: 9-12시간

---

### Phase 2: 데이터 관리 (1주차)

**목표**: 멀티 종목 데이터 로딩 및 캐싱

3. **data_manager.py 구현**
   - DataManager 클래스 (3-4시간)
   - 캐싱 로직 (2-3시간)
   - 테스트 작성 (~6개)

**예상 시간**: 5-7시간

---

### Phase 3: 백테스팅 엔진 (2주차)

**목표**: 메인 백테스팅 로직 구현

4. **engine.py 구현**
   - BacktestEngine 클래스 기본 구조 (3-4시간)
   - 날짜별 루프 로직 (4-5시간)
   - 신호 처리 및 실행 (4-5시간)
   - 테스트 작성 (~12개)

**예상 시간**: 11-14시간

---

### Phase 4: 성과 분석 (1주차)

**목표**: 백테스팅 결과 분석 및 리포트

5. **analytics.py 구현**
   - PerformanceAnalyzer 클래스 (4-5시간)
   - 차트 생성 (2-3시간)
   - 리포트 생성 (2-3시간)
   - 테스트 작성 (~8개)

**예상 시간**: 8-11시간

---

### Phase 5: 통합 및 검증 (1주차)

**목표**: 전체 시스템 통합 테스트 및 검증

6. **통합 테스트**
   - 샘플 데이터로 전체 백테스팅 실행
   - 수동 계산과 비교 검증
   - 엣지 케이스 테스트

7. **문서화**
   - 사용 가이드 작성
   - 예제 코드 작성
   - API 문서 정리

**예상 시간**: 6-8시간

---

**총 예상 시간**: 39-52시간 (약 5-7주)

---

## 테스트 전략

### 단위 테스트

**portfolio.py**:
- Position 생성 및 메서드 테스트
- Portfolio 포지션 추가/청산 테스트
- 손절가 체크 테스트
- 트레일링 스톱 업데이트 테스트

**execution.py**:
- 체결가 계산 (슬리피지 반영)
- 수수료 계산
- 총 비용 계산

**data_manager.py**:
- 데이터 로딩
- 캐싱 및 로드
- 날짜 정렬

**engine.py**:
- 일별 처리 로직
- 신호 생성 및 실행
- 손절 처리

**analytics.py**:
- 수익률 계산
- 샤프 비율 계산
- MDD 계산
- 승률/손익비 계산

---

### 통합 테스트

**시나리오 1: 단순 매수/매도**
- 1종목, 1번 매수 → 1번 매도
- 수익 발생 확인
- 수수료/슬리피지 반영 확인

**시나리오 2: 손절 발동**
- 매수 후 손절가 도달
- 자동 청산 확인

**시나리오 3: 멀티 종목**
- 3종목 동시 보유
- 포트폴리오 제한 준수 확인

**시나리오 4: 트레일링 스톱**
- 수익 발생 시 손절가 상향 조정
- 이익 보호 확인

---

### 스트레스 테스트

**극단 시나리오**:
- 연속 손실 (10번 연속 손절)
- 급등/급락 장세
- 거래 정지 (데이터 없음)

---

## 품질 기준

### 코드 품질
- ✅ Type hints 100%
- ✅ Docstrings 100%
- ✅ 테스트 커버리지 > 90%
- ✅ 로깅 상세 (DEBUG/INFO 레벨)

### 백테스팅 정확성
- 💡 슬리피지 반영 (보수적 추정)
- 💡 수수료 반영 (실제 증권사 수준)
- 💡 미래 데이터 사용 금지 (Look-ahead bias 방지)
- 💡 생존자 편향 제거 (상장폐지 종목 포함)

### 성과 지표
- 📊 총 수익률 및 CAGR
- 📊 최대 낙폭 (MDD)
- 📊 샤프 비율
- 📊 승률 및 손익비
- 📊 거래 횟수 및 평균 보유 기간

---

## 핵심 설계 결정

### 1. 종목 선정 방식

**결정**: 전체 시장 스캔 방식

**이유**:
- 실제 트레이딩 환경을 정확히 시뮬레이션
- 미리 종목을 선정하는 것은 생존자 편향(Survivorship Bias)을 발생시킴
- 매일 신호가 발생하는 종목이 달라지는 실제 상황 반영

**구현**:
- 매 거래일마다 코스피/코스닥 전체 종목(약 2,400개) 스캔
- 진입/청산 신호가 발생한 종목만 거래
- 데이터 로딩 실패 종목은 자동 제외

**장점**:
- 현실적인 백테스팅 결과
- 전략의 실제 적용 가능성 검증
- 다양한 시장 상황에서의 전략 성과 확인

**단점**:
- 대량 데이터 로딩으로 인한 초기 로딩 시간 증가
- 메모리 사용량 증가

**대응**:
- 병렬 처리로 로딩 시간 최소화
- 캐싱으로 반복 실행 시 성능 향상
- 필요시 시장 필터링 옵션 제공 (KOSPI만, KOSDAQ만)

---

### 2. 포트폴리오 제한

**결정**: Level 5-3 포트폴리오 제한 체크 제외

**이유**:
- 초기 백테스팅에서는 전략 자체의 성과에 집중
- 제한 없이 자본이 허락하는 한 최대한 활용
- 추후 필요시 제한 추가 가능

**적용**:
- ✅ 포지션 사이징 (Level 5-1): 적용
- ✅ 손절 관리 (Level 5-2): 적용
- ❌ 포트폴리오 제한 (Level 5-3): 제외
  - 단일 종목 최대 4유닛 제한 없음
  - 상관관계 그룹 제한 없음
  - 전체 포트폴리오 12유닛 제한 없음
- ✅ 리스크 노출 (Level 5-4): 추적만 (제한 없이)

**영향**:
- 더 공격적인 포지션 가능
- 동시 보유 종목 수 증가 가능
- 자본 제약만 유일한 제한

---

### 3. 벡터화 방식 vs 이벤트 기반

**결정**: 벡터화 방식 사용

**이유**:
- Level 1-5 함수들이 모두 DataFrame 기반
- 기존 코드와의 통합 용이
- 구현이 간단하고 빠름

**단점**:
- 이벤트 기반보다는 덜 현실적
- 실시간 거래에는 부적합

**대응**:
- 백테스팅 단계에서는 벡터화 방식으로 빠르게 검증
- Level 7 (실거래)에서는 이벤트 기반으로 재구현

---

### 2. 신호 처리 순서

**결정**: 손절 → 청산 신호 → 진입 신호

**이유**:
- 손절은 최우선 (리스크 관리)
- 청산 후 진입 (포지션 공간 확보)
- 같은 날 청산과 진입 가능

---

### 3. 슬리피지 모델

**결정**: 고정 비율 (0.1%)

**이유**:
- 단순하고 이해하기 쉬움
- 보수적 추정 (실제보다 불리)

**개선 가능**:
- 거래량 기반 슬리피지
- 시간대별 슬리피지 차등

---

### 4. 수수료 모델

**결정**: 고정 비율 (0.015%)

**이유**:
- 온라인 증권사 평균 수수료
- 단순 계산

**참고**:
- 한국투자증권: 0.015%
- 미래에셋: 0.014%
- 키움증권: 0.015%

---

### 5. 포지션 관리

**결정**: 평균가 계산 방식

**이유**:
- 추가 매수 시 평균 진입가로 통합
- 부분 청산 시 유닛 비율로 조정

**예시**:
```
1차 매수: 100주 @ 50,000원
2차 매수: 50주 @ 52,000원
평균가 = (100×50,000 + 50×52,000) / 150 = 50,667원
```

---

### 6. 데이터 캐싱

**결정**: JSON 파일 기반 캐싱

**이유**:
- 프로젝트 데이터 저장 전략과 일치
- 간단하고 디버깅 용이
- 반복 실행 시 성능 향상

**캐시 구조**:
```
data/backtest_cache/
├── 005930_2020-01-01_2023-12-31.json
├── 000660_2020-01-01_2023-12-31.json
└── ...
```

---

## 위험 요소 및 대응

### 1. Look-ahead Bias (미래 데이터 사용)

⚠️ **위험**: 신호 생성 시 미래 데이터 사용으로 과적합

✅ **대응**:
- 각 날짜마다 해당 날짜까지의 데이터만 사용
- `data.iloc[:date_idx + 1]` 슬라이싱
- 엄격한 코드 리뷰

---

### 2. Survivorship Bias (생존자 편향)

⚠️ **위험**: 상장폐지 종목 제외로 수익률 과대평가

✅ **대응**:
- 현재 단계: 인지하고 해석 시 고려
- 향후 개선: 상장폐지 종목 데이터 포함

---

### 3. 슬리피지 과소평가

⚠️ **위험**: 실제 체결가가 더 불리할 수 있음

✅ **대응**:
- 보수적 슬리피지 사용 (0.1%)
- 대량 주문 시 슬리피지 증가 고려

---

### 4. 데이터 품질

⚠️ **위험**: 잘못된 데이터로 인한 오류

✅ **대응**:
- Level 1의 `validate_data()` 활용
- 이상치 탐지 및 제거
- 로깅으로 추적

---

### 5. 성능 문제 (전체 시장 스캔)

⚠️ **위험**: 약 2,400개 종목의 데이터 로딩 및 처리로 인한 성능 저하

**구체적 문제**:
- 초기 데이터 로딩 시간: 예상 5-10분 (종목당 평균 0.2초)
- 메모리 사용량: 약 2-4GB (종목당 1-2MB)
- 매일 전체 종목 스캔으로 인한 처리 시간 증가

✅ **대응**:

**1. 데이터 로딩 최적화**:
- ThreadPoolExecutor로 병렬 로딩 (10-20 workers)
- 진행 상황 표시 (tqdm)
- 로딩 실패 종목은 스킵

**2. 캐싱 전략**:
- 지표 계산 결과를 JSON 파일로 캐싱
- 캐시 키: `{ticker}_{start_date}_{end_date}`
- 반복 실행 시 캐시에서 로드 (10배 이상 빠름)

**3. 메모리 관리**:
- 필요 없는 컬럼 제거
- 데이터 타입 최적화 (float64 → float32)
- 필요시 청크 단위 처리

**4. 실행 시간 단축**:
- 시장 필터링 옵션 (KOSPI만, KOSDAQ만)
- 시총/거래량 필터링 (예: 시총 1000억 이상)
- 백테스팅 기간 단축 테스트

---

## 설정 예시 (config.yaml)

```yaml
backtesting:
  # 기본 설정
  initial_capital: 100_000_000  # 1억원
  commission_rate: 0.00015      # 0.015% (한국투자증권)
  slippage_pct: 0.001           # 0.1% 슬리피지
  market: 'ALL'                 # 시장 선택: 'KOSPI', 'KOSDAQ', 'ALL'

  # 신호 설정
  signal_config:
    enable_early_signals: false  # 조기 진입 신호 비활성화
    signal_strength_threshold: 80  # 신호 강도 80점 이상

  # 리스크 관리 설정
  risk_config:
    risk_percentage: 0.01  # 1%
    desired_units_per_signal: 2
    atr_multiplier: 2.0
    stop_ma: 'EMA_20'

    # 포트폴리오 제한 설정 (백테스팅에서는 비활성화)
    skip_portfolio_limits: true  # ★ 포트폴리오 제한 체크 제외

    # 아래 설정들은 skip_portfolio_limits=true일 때 무시됨
    limits:
      single: 4              # 단일 종목 최대 유닛 (사용 안 함)
      correlated: 6          # 상관관계 그룹 최대 유닛 (사용 안 함)
      diversified: 10        # 분산 투자 최대 유닛 (사용 안 함)
      total: 12              # 전체 최대 유닛 (사용 안 함)

    correlation_groups:      # 상관관계 그룹 (사용 안 함)
      반도체:
        - '005930'  # 삼성전자
        - '000660'  # SK하이닉스

    max_risk_percentage: 0.02  # 최대 총 리스크 (추적만, 제한 없음)
    max_single_risk: 0.01      # 최대 단일 리스크 (추적만, 제한 없음)

  # 데이터 관리
  data_config:
    cache_dir: 'data/backtest_cache'
    use_cache: true
    max_workers: 10         # 병렬 로딩 워커 수

    # 시장 필터 (옵션)
    # market_cap_min: 100_000_000_000  # 최소 시가총액 (1000억)
    # volume_min: 100_000              # 최소 거래량

  # 성과 분석
  analytics_config:
    risk_free_rate: 0.03  # 무위험 수익률 3%
    benchmark: 'KOSPI'    # 벤치마크 지수

# 로깅
logging:
  backtest:
    level: 'INFO'  # DEBUG, INFO, WARNING
    file: 'log/backtest/backtest.log'
```

---

## 사용 예시

### 기본 백테스팅 (전체 시장 스캔)

```python
from src.backtest.engine import BacktestEngine
from src.config.config_loader import load_config

# 설정 로드
config = load_config()

# 엔진 생성
engine = BacktestEngine(config=config['backtesting'])

# 백테스팅 실행 (코스피 + 코스닥 전체)
result = engine.run_backtest(
    start_date='2020-01-01',
    end_date='2023-12-31',
    initial_capital=100_000_000,
    market='ALL'  # 'KOSPI', 'KOSDAQ', 'ALL'
)

# 결과 출력
print(result.summary())
```

**출력 예시**:
```
========================================
백테스팅 결과 요약
========================================
시장: KOSPI + KOSDAQ (2,156개 종목 스캔)
기간: 2020-01-01 ~ 2023-12-31
초기 자본: 100,000,000원
최종 자산: 125,600,000원

성과 지표:
- 총 수익률: +25.6%
- CAGR: +7.9%
- 최대 낙폭: -12.3%
- 샤프 비율: 1.35

거래 통계:
- 총 거래: 48건 (32개 종목)
- 승률: 62.5%
- 손익비: 1.8
- 평균 보유 기간: 15일
- 최대 동시 보유: 8개 종목

리스크 관리:
- 평균 포지션 크기: 2.3유닛
- 손절 발동: 18건 (37.5%)
- 포트폴리오 제한: 없음 (자본 제약만)
========================================
```

---

### 차트 생성

```python
# 자산곡선 차트
result.plot_equity_curve(save_path='log/backtest/equity_curve.png')

# 낙폭 차트
result.plot_drawdown(save_path='log/backtest/drawdown.png')

# 월별 수익률 히트맵
result.plot_monthly_returns(save_path='log/backtest/monthly_returns.png')
```

---

### 거래 내역 Export

```python
# CSV 파일로 저장
result.export_trades('log/backtest/trades.csv')

# JSON 파일로 저장
result.export_trades('log/backtest/trades.json', format='json')
```

**trades.csv 예시**:
```csv
date,ticker,action,shares,entry_price,exit_price,pnl,return_pct,holding_days,reason
2020-03-15,005930,buy,100,50000,,,,,Stage 6 entry
2020-03-30,005930,sell,100,50000,52000,200000,4.0,15,exit_signal (MACD cross)
2020-04-10,000660,buy,50,100000,,,,,Stage 6 entry
2020-04-25,000660,sell,50,100000,96000,-200000,-4.0,15,stop_loss (volatility)
...
```

---

## 다음 단계 (Level 7~8)

### Level 7: 실거래 연동

백테스팅 검증 완료 후 실거래 연동 구현

**주요 기능**:
- 한국투자증권 API 연동
- 실시간 시세 조회 (웹소켓)
- 주문 실행 (시장가/지정가)
- 체결 확인 및 관리
- 일일 거래 한도 관리

---

### Level 8: 모니터링 & 알림

실시간 모니터링 및 Slack 알림 시스템

**주요 기능**:
- 매매 신호 발생 알림
- 체결 알림
- 손절 발동 알림
- 일일 성과 리포트
- 리스크 경고 알림

---

## 참고 자료

- [이동평균선 투자법](../../Moving_Average_Investment_Strategy_Summary.md)
- [Level 1: 데이터 수집](../2025-10-30_collector_implementation_complete.md)
- [Level 2: 기술적 지표](../2025-11-13_technical_indicators_all.md)
- [Level 3: 스테이지 분석](../2025-11-14_stage_level3_2_determine_stage_and_transition.md)
- [Level 4: 매매 신호](./2025-11-14_signal_level4_plan.md)
- [Level 5: 리스크 관리](./2025-11-14_risk_level5_plan.md)
- [Vectorized Backtesting in Python](https://www.quantstart.com/articles/Vectorized-Backtesting-in-Python/)
- [Backtrader Documentation](https://www.backtrader.com/)

---

## 작성자
- seunghakim
- AI Assistant (Claude)

## 작성 일자
2025-11-16

---

## 검토 체크리스트

- [x] 전체 아키텍처 설계
- [x] 데이터 흐름 정의
- [x] 모든 클래스 및 함수 명세 작성
- [x] 구현 순서 정리
- [x] 테스트 전략 수립
- [x] 위험 요소 식별 및 대응
- [x] 예상 시간 산정
- [x] 설정 예시 작성
- [x] 사용 예시 작성
- [x] Level 7~8 개요 작성

---
