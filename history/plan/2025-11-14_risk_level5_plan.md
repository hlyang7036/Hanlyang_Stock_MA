# Level 5 리스크 관리 모듈 계획

## 날짜
2025-11-14

## 계획 개요
터틀 트레이딩의 리스크 관리 기법을 기반으로 체계적인 포지션 관리 시스템을 구현합니다.
변동성(ATR) 기반 포지션 사이징, 다층 손절 시스템, 포트폴리오 제한, 리스크 노출 관리를 통해 
안정적이고 지속 가능한 매매 시스템을 구축합니다.

---

## 모듈 구조

```
src/risk/
├── __init__.py              # 통합 리스크 관리
├── position_sizing.py       # 포지션 사이징 (4개 함수)
├── stop_loss.py             # 손절 관리 (5개 함수)
├── portfolio.py             # 포트폴리오 제한 (5개 함수)
└── exposure.py              # 리스크 노출 관리 (4개 함수)
```

**총 18개 함수 + 1개 통합 함수**

---

## Level 5-1: 포지션 사이징 (position_sizing.py)

### 핵심 개념: 터틀 트레이딩

```
1유닛 = (계좌잔고 × 리스크비율) / ATR

기본 설정:
- 리스크비율: 1% (계좌의 1%만 리스크에 노출)
- ATR: 변동성 지표

예시:
- 계좌잔고: 10,000,000원
- 리스크비율: 1%
- ATR: 1,000원
→ 1유닛 = (10,000,000 × 0.01) / 1,000 = 100주
```

---

### 구현 함수 (4개)

#### 1. calculate_unit_size()

```python
def calculate_unit_size(
    account_balance: float,
    atr: float,
    risk_percentage: float = 0.01
) -> int:
    """
    기본 유닛 크기 계산 (터틀 트레이딩 방식)
    
    Args:
        account_balance: 계좌 잔고 (원)
        atr: Average True Range (원)
        risk_percentage: 리스크 비율 (기본값: 0.01 = 1%)
    
    Returns:
        int: 1유닛 크기 (주 단위)
    
    Raises:
        ValueError: account_balance나 atr이 0 이하일 때
        ValueError: risk_percentage가 0~1 범위 밖일 때
    
    Notes:
        1유닛 = (계좌잔고 × 리스크비율) / ATR
        
        계좌의 1%만 리스크에 노출하는 보수적 전략
        ATR이 크면 (변동성 높음) → 유닛이 작아짐
        ATR이 작으면 (변동성 낮음) → 유닛이 커짐
    
    Examples:
        >>> calculate_unit_size(10_000_000, 1_000, 0.01)
        100
        
        >>> calculate_unit_size(10_000_000, 2_000, 0.01)
        50
    """
```

**구현 로직**:
```python
def calculate_unit_size(
    account_balance: float,
    atr: float,
    risk_percentage: float = 0.01
) -> int:
    # 1. 입력 검증
    if account_balance <= 0:
        raise ValueError(f"계좌 잔고는 양수여야 합니다: {account_balance}")
    
    if atr <= 0:
        raise ValueError(f"ATR은 양수여야 합니다: {atr}")
    
    if not 0 < risk_percentage <= 1:
        raise ValueError(f"리스크 비율은 0~1 사이여야 합니다: {risk_percentage}")
    
    logger.debug(f"유닛 계산: 잔고={account_balance:,.0f}, ATR={atr:,.0f}, 리스크={risk_percentage:.2%}")
    
    # 2. 유닛 계산
    risk_amount = account_balance * risk_percentage
    unit_size = risk_amount / atr
    
    # 3. 정수로 반올림 (주식은 정수 단위)
    unit_size_int = int(round(unit_size))
    
    logger.debug(f"계산 결과: {unit_size_int}주")
    
    return unit_size_int
```

---

#### 2. adjust_by_signal_strength()

```python
def adjust_by_signal_strength(
    base_units: int,
    signal_strength: int,
    strength_threshold: int = 80
) -> int:
    """
    신호 강도에 따른 포지션 조정
    
    Args:
        base_units: 기본 유닛 크기
        signal_strength: 신호 강도 (0-100)
        strength_threshold: 기준 강도 (기본값: 80)
    
    Returns:
        int: 조정된 유닛 크기
    
    Notes:
        신호 강도 조정 규칙:
        - 80점 이상: 기본 유닛 (100%)
        - 70-80점: 0.75배
        - 60-70점: 0.5배
        - 50-60점: 0.25배
        - 50점 미만: 진입 안 함 (0)
    
    Examples:
        >>> adjust_by_signal_strength(100, 85, 80)
        100
        
        >>> adjust_by_signal_strength(100, 75, 80)
        75
        
        >>> adjust_by_signal_strength(100, 45, 80)
        0
    """
```

**구현 로직**:
```python
def adjust_by_signal_strength(
    base_units: int,
    signal_strength: int,
    strength_threshold: int = 80
) -> int:
    # 입력 검증
    if base_units < 0:
        raise ValueError(f"기본 유닛은 음수일 수 없습니다: {base_units}")
    
    if not 0 <= signal_strength <= 100:
        raise ValueError(f"신호 강도는 0-100 사이여야 합니다: {signal_strength}")
    
    logger.debug(f"강도 조정: 기본={base_units}주, 강도={signal_strength}점")
    
    # 신호 강도에 따른 배율 결정
    if signal_strength >= strength_threshold:
        multiplier = 1.0  # 100%
    elif signal_strength >= 70:
        multiplier = 0.75  # 75%
    elif signal_strength >= 60:
        multiplier = 0.5   # 50%
    elif signal_strength >= 50:
        multiplier = 0.25  # 25%
    else:
        multiplier = 0.0   # 진입 안 함
    
    adjusted = int(base_units * multiplier)
    
    logger.debug(f"조정 결과: {adjusted}주 (배율={multiplier:.2f})")
    
    return adjusted
```

---

#### 3. calculate_position_size()

```python
def calculate_position_size(
    account_balance: float,
    current_price: float,
    atr: float,
    signal_strength: int = 80,
    risk_percentage: float = 0.01
) -> Dict[str, Any]:
    """
    최종 포지션 크기 계산
    
    Args:
        account_balance: 계좌 잔고
        current_price: 현재가
        atr: ATR
        signal_strength: 신호 강도
        risk_percentage: 리스크 비율
    
    Returns:
        Dict: 포지션 정보
            - units: 유닛 수
            - shares: 주식 수
            - total_value: 총 금액
            - risk_amount: 리스크 금액
            - position_percentage: 계좌 대비 포지션 비율
    
    Examples:
        >>> calculate_position_size(10_000_000, 50_000, 1_000, 85)
        {
            'units': 1,
            'shares': 100,
            'total_value': 5_000_000,
            'risk_amount': 100_000,
            'position_percentage': 0.5
        }
    """
```

---

#### 4. get_max_position_by_capital()

```python
def get_max_position_by_capital(
    account_balance: float,
    current_price: float,
    max_capital_ratio: float = 0.25
) -> int:
    """
    자본 제약에 따른 최대 포지션
    
    Args:
        account_balance: 계좌 잔고
        current_price: 현재가
        max_capital_ratio: 최대 자본 비율 (기본값: 0.25 = 25%)
    
    Returns:
        int: 최대 매수 가능 주식 수
    
    Notes:
        단일 종목에 계좌의 25% 이상 투자 방지
    """
```

---

## Level 5-2: 손절 관리 (stop_loss.py)

### 핵심 개념: 2가지 손절 방식

**1. 추세 기반 손절**
- 매수 포지션: 데드크로스 발생 시
- 매도 포지션: 골든크로스 발생 시

**2. 변동성 기반 손절**
- 매수 포지션: 진입가 - 2ATR
- 매도 포지션: 진입가 + 2ATR

**최종 손절가**: 두 방식 중 더 가까운 것 선택

---

### 구현 함수 (5개)

#### 1. calculate_volatility_stop()

```python
def calculate_volatility_stop(
    entry_price: float,
    atr: float,
    position_type: str,  # 'long' or 'short'
    atr_multiplier: float = 2.0
) -> float:
    """
    변동성 기반 손절가 계산
    
    Args:
        entry_price: 진입가
        atr: ATR
        position_type: 'long' (매수) 또는 'short' (매도)
        atr_multiplier: ATR 배수 (기본값: 2.0)
    
    Returns:
        float: 손절가
    
    Notes:
        매수 포지션: 진입가 - (ATR × 배수)
        매도 포지션: 진입가 + (ATR × 배수)
        
        ATR 2배를 사용하여 정상적인 변동성은 허용
    
    Examples:
        >>> calculate_volatility_stop(50_000, 1_000, 'long', 2.0)
        48000.0
        
        >>> calculate_volatility_stop(50_000, 1_000, 'short', 2.0)
        52000.0
    """
```

---

#### 2. calculate_trend_stop()

```python
def calculate_trend_stop(
    data: pd.DataFrame,
    position_type: str,
    stop_ma: str = 'EMA_20'
) -> pd.Series:
    """
    추세 기반 손절가 계산
    
    Args:
        data: DataFrame (이동평균선 포함)
        position_type: 'long' or 'short'
        stop_ma: 손절 기준선 (기본값: 'EMA_20')
    
    Returns:
        pd.Series: 추세 기반 손절가
    
    Notes:
        매수 포지션: 중기 이동평균선(EMA_20) 하단
        매도 포지션: 중기 이동평균선(EMA_20) 상단
        
        추세가 꺾이면 즉시 손절
    
    Examples:
        >>> df['Trend_Stop'] = calculate_trend_stop(df, 'long')
    """
```

---

#### 3. get_stop_loss_price()

```python
def get_stop_loss_price(
    entry_price: float,
    current_price: float,
    atr: float,
    trend_stop: float,
    position_type: str
) -> Dict[str, Any]:
    """
    최종 손절가 결정
    
    Args:
        entry_price: 진입가
        current_price: 현재가
        atr: ATR
        trend_stop: 추세 기반 손절가
        position_type: 'long' or 'short'
    
    Returns:
        Dict: 손절 정보
            - stop_price: 최종 손절가
            - stop_type: 손절 유형 ('volatility' or 'trend')
            - distance: 현재가와의 거리 (%)
            - risk_amount: 리스크 금액 (1주당)
    
    Notes:
        두 손절가 중 현재가에 더 가까운 것 선택
        (더 보수적인 손절)
    """
```

---

#### 4. check_stop_loss_triggered()

```python
def check_stop_loss_triggered(
    current_price: float,
    stop_price: float,
    position_type: str
) -> bool:
    """
    손절 발동 체크
    
    Args:
        current_price: 현재가
        stop_price: 손절가
        position_type: 'long' or 'short'
    
    Returns:
        bool: 손절 발동 여부
    
    Notes:
        매수 포지션: 현재가 <= 손절가
        매도 포지션: 현재가 >= 손절가
    """
```

---

#### 5. update_trailing_stop()

```python
def update_trailing_stop(
    entry_price: float,
    highest_price: float,  # 또는 lowest_price
    current_stop: float,
    atr: float,
    position_type: str
) -> float:
    """
    트레일링 스톱 업데이트
    
    Args:
        entry_price: 진입가
        highest_price: 최고가 (매수) 또는 최저가 (매도)
        current_stop: 현재 손절가
        atr: ATR
        position_type: 'long' or 'short'
    
    Returns:
        float: 업데이트된 손절가
    
    Notes:
        수익이 나면 손절가를 올려서 이익 보호
        
        매수 포지션:
        - 신고가 경신 시 손절가 상향 조정
        - 손절가 = max(현재 손절가, 최고가 - 2ATR)
        
        매도 포지션:
        - 신저가 경신 시 손절가 하향 조정
        - 손절가 = min(현재 손절가, 최저가 + 2ATR)
    """
```

---

## Level 5-3: 포트폴리오 제한 (portfolio.py)

### 핵심 개념: 다층 리스크 제어

```
제한 레벨:
1. 단일 종목:          최대 4유닛
2. 상관관계 높은 그룹: 최대 6유닛 (합계)
3. 상관관계 낮은 그룹: 최대 10유닛 (합계)
4. 전체 포트폴리오:    최대 12유닛 (합계)
```

---

### 구현 함수 (5개)

#### 1. check_single_position_limit()

```python
def check_single_position_limit(
    current_units: int,
    additional_units: int,
    max_units_per_position: int = 4
) -> Dict[str, Any]:
    """
    단일 종목 포지션 제한 체크
    
    Args:
        current_units: 현재 보유 유닛
        additional_units: 추가 유닛
        max_units_per_position: 단일 종목 최대 유닛 (기본값: 4)
    
    Returns:
        Dict: 체크 결과
            - allowed: 허용 여부 (bool)
            - available_units: 추가 가능 유닛 수
            - current_units: 현재 유닛
            - limit: 최대 한도
            - reason: 거부 사유 (불허 시)
    
    Examples:
        >>> check_single_position_limit(3, 2, 4)
        {
            'allowed': False,
            'available_units': 1,
            'current_units': 3,
            'limit': 4,
            'reason': '단일 종목 최대 4유닛 초과'
        }
    """
```

---

#### 2. check_correlated_group_limit()

```python
def check_correlated_group_limit(
    positions: Dict[str, int],
    correlation_groups: Dict[str, List[str]],
    ticker: str,
    additional_units: int,
    max_correlated_units: int = 6
) -> Dict[str, Any]:
    """
    상관관계 그룹 제한 체크
    
    Args:
        positions: 현재 포지션 딕셔너리 {종목코드: 유닛수}
        correlation_groups: 상관관계 그룹 {그룹명: [종목코드 리스트]}
            예: {'반도체': ['005930', '000660'], 
                 '자동차': ['005380', '000270']}
        ticker: 추가하려는 종목코드
        additional_units: 추가 유닛
        max_correlated_units: 상관관계 그룹 최대 유닛 (기본값: 6)
    
    Returns:
        Dict: 체크 결과
            - allowed: 허용 여부
            - available_units: 추가 가능 유닛
            - group_name: 해당 그룹명
            - group_total: 그룹 총 유닛
            - limit: 최대 한도
    
    Notes:
        같은 섹터/산업군 종목들의 합계 제한
        예: 삼성전자 + SK하이닉스 합계 최대 6유닛
    """
```

---

#### 3. check_diversified_limit()

```python
def check_diversified_limit(
    positions: Dict[str, int],
    correlation_groups: Dict[str, List[str]],
    ticker: str,
    additional_units: int,
    max_diversified_units: int = 10
) -> Dict[str, Any]:
    """
    분산 투자 제한 체크 (상관관계 낮은 종목)
    
    Args:
        positions: 현재 포지션
        correlation_groups: 상관관계 그룹
        ticker: 추가 종목
        additional_units: 추가 유닛
        max_diversified_units: 최대 유닛 (기본값: 10)
    
    Returns:
        Dict: 체크 결과
    
    Notes:
        서로 다른 섹터 종목들의 합계 제한
        예: 반도체(6) + 자동차(4) = 10유닛
    """
```

---

#### 4. check_total_exposure_limit()

```python
def check_total_exposure_limit(
    positions: Dict[str, int],
    additional_units: int,
    max_total_units: int = 12
) -> Dict[str, Any]:
    """
    전체 포트폴리오 노출 제한 체크
    
    Args:
        positions: 현재 포지션
        additional_units: 추가 유닛
        max_total_units: 전체 최대 유닛 (기본값: 12)
    
    Returns:
        Dict: 체크 결과
            - allowed: 허용 여부
            - available_units: 추가 가능 유닛
            - total_units: 현재 총 유닛
            - limit: 최대 한도
    
    Notes:
        전체 포트폴리오의 절대 한도
        계좌의 12% 이상 리스크에 노출 금지
    """
```

---

#### 5. get_available_position_size()

```python
def get_available_position_size(
    ticker: str,
    desired_units: int,
    positions: Dict[str, int],
    correlation_groups: Dict[str, List[str]],
    limits: Dict[str, int] = None
) -> Dict[str, Any]:
    """
    실제 추가 가능한 포지션 크기 계산
    
    모든 제한 조건을 종합하여 실제로 추가할 수 있는
    최대 유닛 수를 계산합니다.
    
    Args:
        ticker: 종목코드
        desired_units: 희망 유닛
        positions: 현재 포지션
        correlation_groups: 상관관계 그룹
        limits: 제한 설정 (None이면 기본값 사용)
            예: {
                'single': 4,
                'correlated': 6,
                'diversified': 10,
                'total': 12
            }
    
    Returns:
        Dict: 최종 결과
            - allowed_units: 실제 허용 유닛
            - limiting_factor: 제한 요인
            - checks: 각 제한 체크 결과
    
    Examples:
        >>> get_available_position_size(
        ...     '005930',  # 삼성전자
        ...     2,  # 2유닛 추가 희망
        ...     {'005930': 3, '000660': 2},  # 삼성 3, SK하이닉스 2
        ...     {'반도체': ['005930', '000660']}
        ... )
        {
            'allowed_units': 1,  # 1유닛만 가능
            'limiting_factor': 'correlated_group',  # 반도체 그룹 제한
            'checks': {...}
        }
    """
```

---

## Level 5-4: 리스크 노출 관리 (exposure.py)

### 핵심 개념: 실시간 리스크 모니터링

총 리스크 = Σ (포지션 크기 × 손절 거리)

---

### 구현 함수 (4개)

#### 1. calculate_position_risk()

```python
def calculate_position_risk(
    position_size: int,
    entry_price: float,
    stop_price: float,
    position_type: str = 'long'
) -> Dict[str, Any]:
    """
    개별 포지션의 리스크 계산
    
    Args:
        position_size: 포지션 크기 (주)
        entry_price: 진입가
        stop_price: 손절가
        position_type: 'long' or 'short'
    
    Returns:
        Dict: 리스크 정보
            - risk_per_share: 주당 리스크
            - total_risk: 총 리스크 금액
            - risk_percentage: 리스크 비율 (진입가 대비)
            - position_value: 포지션 가치
    
    Examples:
        >>> calculate_position_risk(100, 50_000, 48_000, 'long')
        {
            'risk_per_share': 2000,
            'total_risk': 200_000,
            'risk_percentage': 0.04,
            'position_value': 5_000_000
        }
    """
```

---

#### 2. calculate_total_portfolio_risk()

```python
def calculate_total_portfolio_risk(
    positions: List[Dict[str, Any]],
    account_balance: float
) -> Dict[str, Any]:
    """
    전체 포트폴리오 리스크 계산
    
    Args:
        positions: 포지션 리스트
            각 포지션: {
                'ticker': str,
                'size': int,
                'entry_price': float,
                'stop_price': float,
                'type': str
            }
        account_balance: 계좌 잔고
    
    Returns:
        Dict: 포트폴리오 리스크
            - total_risk: 총 리스크 금액
            - risk_percentage: 계좌 대비 리스크 비율
            - positions_at_risk: 리스크 있는 포지션 수
            - largest_risk: 최대 리스크 포지션
            - risk_by_ticker: 종목별 리스크 딕셔너리
    
    Examples:
        >>> positions = [
        ...     {'ticker': '005930', 'size': 100, 
        ...      'entry_price': 50000, 'stop_price': 48000, 'type': 'long'},
        ...     {'ticker': '000660', 'size': 50, 
        ...      'entry_price': 100000, 'stop_price': 96000, 'type': 'long'}
        ... ]
        >>> calculate_total_portfolio_risk(positions, 10_000_000)
        {
            'total_risk': 400_000,
            'risk_percentage': 0.04,
            'positions_at_risk': 2,
            ...
        }
    """
```

---

#### 3. check_risk_limits()

```python
def check_risk_limits(
    total_risk: float,
    account_balance: float,
    max_risk_percentage: float = 0.02,
    max_single_risk: float = 0.01
) -> Dict[str, Any]:
    """
    리스크 한도 체크
    
    Args:
        total_risk: 총 리스크
        account_balance: 계좌 잔고
        max_risk_percentage: 최대 리스크 비율 (기본값: 2%)
        max_single_risk: 단일 포지션 최대 리스크 (기본값: 1%)
    
    Returns:
        Dict: 한도 체크 결과
            - within_limits: 한도 내 여부
            - total_risk_ok: 총 리스크 OK
            - risk_percentage: 현재 리스크 비율
            - available_risk: 남은 리스크 여유
            - warnings: 경고 메시지 리스트
    
    Notes:
        권장 한도:
        - 총 리스크: 계좌의 2% 이하
        - 단일 포지션: 계좌의 1% 이하
    """
```

---

#### 4. generate_risk_report()

```python
def generate_risk_report(
    positions: List[Dict[str, Any]],
    account_balance: float,
    correlation_groups: Dict[str, List[str]] = None
) -> Dict[str, Any]:
    """
    포괄적 리스크 리포트 생성
    
    Args:
        positions: 포지션 리스트
        account_balance: 계좌 잔고
        correlation_groups: 상관관계 그룹 (선택)
    
    Returns:
        Dict: 리스크 리포트
            - summary: 요약 정보
                - total_positions: 총 포지션 수
                - total_value: 총 포지션 가치
                - total_risk: 총 리스크
                - risk_percentage: 리스크 비율
            - by_ticker: 종목별 리스크
            - by_group: 그룹별 리스크 (상관관계 그룹 제공 시)
            - warnings: 경고 및 권장사항
            - metrics: 주요 지표
                - sharpe_ratio: 샤프 비율 (예상)
                - max_drawdown: 최대 낙폭 (예상)
    
    Notes:
        대시보드/알림 시스템에서 활용
    """
```

---

## 통합 리스크 관리 (__init__.py)

### 메인 함수

```python
def apply_risk_management(
    signal: Dict[str, Any],
    account_balance: float,
    positions: Dict[str, int],
    market_data: pd.DataFrame,
    config: Dict[str, Any] = None
) -> Dict[str, Any]:
    """
    통합 리스크 관리 적용
    
    전체 프로세스:
    1. 포지션 사이징 (Level 5-1)
    2. 포트폴리오 제한 체크 (Level 5-3)
    3. 손절가 계산 (Level 5-2)
    4. 리스크 평가 (Level 5-4)
    5. 최종 승인/거부 결정
    
    Args:
        signal: 매매 신호 (Level 4 출력)
            {
                'ticker': str,
                'action': str,  # 'buy', 'sell', 'exit'
                'signal_strength': int,
                'current_price': float
            }
        account_balance: 계좌 잔고
        positions: 현재 포지션 {종목: 유닛수}
        market_data: 시장 데이터 (ATR, 이동평균선 등)
        config: 설정
            {
                'risk_percentage': 0.01,
                'limits': {...},
                'correlation_groups': {...}
            }
    
    Returns:
        Dict: 리스크 관리 결과
            - approved: 승인 여부 (bool)
            - position_size: 권장 포지션 크기 (주)
            - stop_price: 손절가
            - risk_amount: 리스크 금액
            - warnings: 경고 메시지
            - reason: 거부 사유 (불승인 시)
    
    Examples:
        >>> signal = {
        ...     'ticker': '005930',
        ...     'action': 'buy',
        ...     'signal_strength': 85,
        ...     'current_price': 50_000
        ... }
        >>> result = apply_risk_management(
        ...     signal, 10_000_000, {'005930': 2}, market_data
        ... )
        >>> if result['approved']:
        ...     execute_trade(result['position_size'], result['stop_price'])
    """
```

---

## 데이터 흐름

```
매매 신호 (Level 4)
    ↓
[포지션 사이징]
1. 기본 유닛 계산 (터틀 방식)
2. 신호 강도 조정
3. 자본 제약 확인
    ↓
[포트폴리오 제한 체크]
1. 단일 종목 제한 (4유닛)
2. 상관관계 그룹 제한 (6유닛)
3. 분산 투자 제한 (10유닛)
4. 전체 노출 제한 (12유닛)
    ↓
[손절가 계산]
1. 변동성 기반 손절 (진입가 ± 2ATR)
2. 추세 기반 손절 (MA 기준)
3. 최종 손절가 결정
    ↓
[리스크 평가]
1. 포지션 리스크 계산
2. 총 리스크 계산
3. 한도 내 여부 확인
    ↓
승인/거부 결정
    ↓
주문 실행 (Level 7)
```

---

## 구현 순서

### Phase 1: 포지션 사이징 (1주차)
- **파일**: `position_sizing.py`
- **함수**: 4개
- **예상 시간**: 3-4시간
- **테스트**: ~12개

### Phase 2: 손절 관리 (1주차)
- **파일**: `stop_loss.py`
- **함수**: 5개
- **예상 시간**: 4-5시간
- **테스트**: ~15개

### Phase 3: 포트폴리오 제한 (1주차)
- **파일**: `portfolio.py`
- **함수**: 5개
- **예상 시간**: 4-5시간
- **테스트**: ~15개

### Phase 4: 리스크 노출 관리 (1주차)
- **파일**: `exposure.py`
- **함수**: 4개
- **예상 시간**: 3-4시간
- **테스트**: ~12개

### Phase 5: 통합 및 검증 (1주차)
- **파일**: `__init__.py`
- **통합 함수**: 1개
- **예상 시간**: 3-4시간
- **전체 통합 테스트**

**총 예상 시간**: 17-22시간 (약 3주)

---

## 테스트 전략

### 단위 테스트
- 각 함수별 독립 테스트
- 경계값 테스트 (0, 음수, 최댓값 등)
- 예외 처리 테스트

### 통합 테스트
- 전체 리스크 관리 파이프라인
- 다양한 시장 시나리오

### 스트레스 테스트
- 극단적 변동성 상황
- 다수 포지션 동시 보유
- 연쇄 손절 시나리오

---

## 품질 기준

### 코드 품질
- ✅ Type hints 100%
- ✅ Docstrings 100%
- ✅ 테스트 커버리지 > 95%
- ✅ 로깅 상세

### 리스크 관리 품질
- 💡 최대 계좌 리스크: < 2%
- 💡 단일 포지션 리스크: < 1%
- 💡 포트폴리오 분산도: > 3종목

---

## 핵심 설계 결정

### 1. 터틀 트레이딩 기반
- **결정**: 변동성(ATR) 기반 포지션 사이징
- **이유**: 검증된 리스크 관리 방법
- **참고**: 리처드 데니스의 터틀 트레이딩

### 2. 다층 리스크 제어
- **결정**: 4단계 제한 (단일/그룹/분산/전체)
- **이유**: 집중 리스크 방지
- **효과**: 블랙스완 이벤트 대응

### 3. 동적 손절
- **결정**: 추세 + 변동성 2가지 방식
- **이유**: 시장 상황에 맞는 유연한 대응
- **효과**: 불필요한 손절 최소화

### 4. 실시간 모니터링
- **결정**: 리스크 지표 실시간 계산
- **이유**: 조기 경보 시스템
- **효과**: 사전 예방적 관리

---

## 위험 요소 및 대응

### 1. 슬리피지 (Slippage)
- ⚠️ **위험**: 손절 주문이 손절가보다 불리하게 체결
- ✅ **대응**: 손절가에 여유분 추가 (0.5% 버퍼)

### 2. 갭 오픈 (Gap Opening)
- ⚠️ **위험**: 손절가를 뚫고 개장
- ✅ **대응**: 최대 리스크 2% 제한으로 손실 통제

### 3. 상관관계 변화
- ⚠️ **위험**: 위기 시 모든 자산 동시 하락
- ✅ **대응**: 상관관계 주기적 재계산, 전체 한도 12유닛

### 4. 연쇄 손절
- ⚠️ **위험**: 다수 포지션 동시 손절
- ✅ **대응**: 분산 투자 + 총 리스크 2% 제한

---

## 설정 예시 (config.yaml)

```yaml
risk_management:
  # 포지션 사이징
  risk_percentage: 0.01  # 1%
  strength_threshold: 80
  
  # 손절 설정
  atr_multiplier: 2.0
  stop_ma: 'EMA_20'
  enable_trailing_stop: true
  
  # 포트폴리오 제한
  limits:
    single_position: 4      # 단일 종목 최대 유닛
    correlated_group: 6     # 상관관계 그룹 최대 유닛
    diversified: 10         # 분산 투자 최대 유닛
    total_portfolio: 12     # 전체 최대 유닛
  
  # 상관관계 그룹
  correlation_groups:
    반도체:
      - '005930'  # 삼성전자
      - '000660'  # SK하이닉스
    자동차:
      - '005380'  # 현대차
      - '000270'  # 기아
    화학:
      - '051910'  # LG화학
      - '009830'  # 한화솔루션
  
  # 리스크 한도
  max_total_risk: 0.02      # 최대 총 리스크 2%
  max_single_risk: 0.01     # 최대 단일 리스크 1%
  max_capital_ratio: 0.25   # 단일 종목 최대 자본 25%
```

---

## 다음 단계 (Level 6~8)

### Level 6: 백테스팅 엔진

**목표**: 전략 성과 검증 및 최적화

**주요 기능**:
- 과거 데이터 기반 시뮬레이션
- 성과 지표 계산 (수익률, MDD, 샤프 비율 등)
- 거래 로그 및 분석
- 최적 파라미터 탐색

**모듈 구조**:
```
src/backtest/
├── __init__.py
├── engine.py          # 백테스팅 엔진
├── metrics.py         # 성과 지표
├── report.py          # 리포트 생성
└── optimizer.py       # 파라미터 최적화
```

**핵심 지표**:
- 총 수익률 / 연환산 수익률
- 최대 낙폭 (MDD)
- 샤프 비율
- 승률 / 손익비
- 거래 횟수 / 평균 보유 기간

---

### Level 7: 실거래 연동

**목표**: 한국투자증권 API 연동 및 자동 주문

**주요 기능**:
- 계좌 조회 (잔고, 보유 종목)
- 실시간 시세 조회
- 주문 실행 (시장가, 지정가, 조건부)
- 체결 확인 및 관리

**모듈 구조**:
```
src/trading/
├── __init__.py
├── broker.py          # 증권사 API 인터페이스
├── order.py           # 주문 관리
├── execution.py       # 체결 처리
└── monitor.py         # 실시간 모니터링
```

**API 기능**:
- OAuth 인증
- 계좌 잔고 조회
- 보유 종목 조회
- 실시간 시세 조회 (웹소켓)
- 매수/매도 주문
- 정정/취소 주문
- 체결 내역 조회

**안전 장치**:
- 주문 전 최종 확인
- 일일 최대 거래 횟수 제한
- 긴급 전체 청산 기능
- API 에러 핸들링

---

### Level 8: 모니터링 & 알림

**목표**: 실시간 모니터링 및 Slack 알림

**주요 기능**:
- 매매 신호 발생 알림
- 체결 알림
- 손절 발동 알림
- 일일 성과 리포트
- 리스크 경고 알림

**모듈 구조**:
```
src/notification/
├── __init__.py
├── slack.py           # Slack 알림
├── telegram.py        # 텔레그램 알림 (선택)
├── email.py           # 이메일 알림 (선택)
└── dashboard.py       # 대시보드 (웹 UI)
```

**알림 유형**:

**1. 매매 신호 알림**
```
🔔 매수 신호 발생
종목: 삼성전자 (005930)
신호: 통상 매수 (강도 85점)
현재가: 50,000원
권장 포지션: 100주
손절가: 48,000원
```

**2. 체결 알림**
```
✅ 매수 체결 완료
종목: 삼성전자 (005930)
수량: 100주 @ 50,000원
손절가: 48,000원
총 금액: 5,000,000원
```

**3. 손절 발동 알림**
```
⚠️ 손절 발동
종목: 삼성전자 (005930)
손절가: 48,000원 도달
현재 포지션: 100주
예상 손실: 200,000원
```

**4. 일일 성과 리포트**
```
📊 일일 성과 리포트 (2025-11-14)
─────────────────────────
수익률: +2.5% (250,000원)
거래 횟수: 3건 (매수 2, 매도 1)
승률: 100%
최대 낙폭: -0.8%
현재 포지션: 3종목 (7유닛)
총 리스크: 1.2%
```

**5. 리스크 경고**
```
🚨 리스크 경고
총 리스크: 2.1% (한도 초과)
권장 조치: 일부 포지션 청산
```

**대시보드 기능**:
- 실시간 계좌 현황
- 보유 포지션 목록
- 리스크 지표 시각화
- 최근 거래 내역
- 성과 차트

---

## 전체 시스템 통합

```
[데이터 수집]
    ↓
[Level 2: 기술적 지표]
    ↓
[Level 3: 스테이지 분석]
    ↓
[Level 4: 매매 신호 생성] ←─────────┐
    ↓                              │
[Level 5: 리스크 관리]              │
    ↓                              │
[Level 7: 주문 실행]                │
    ↓                              │
[Level 8: 모니터링 & 알림] ─────────┘
    ↓
[Level 6: 백테스팅] (병렬)
```

---

## 참고 자료

- [이동평균선 투자법](../../Moving_Average_Investment_Strategy_Summary.md)
- [터틀 트레이딩 기법](https://www.turtletrader.com/)
- [Level 2: 기술적 지표](../2025-11-13_technical_indicators_all.md)
- [Level 3: 스테이지 분석](../2025-11-14_stage_level3_3_calculate_ma_spread_and_check_ma_slope.md)
- [Level 4: 매매 신호](./2025-11-14_signal_level4_plan.md)

---

## 작성자
- seunghakim
- AI Assistant (Claude)

## 작성 일자
2025-11-14

---

## 검토 체크리스트

- [x] 모든 함수 명세 작성
- [x] 데이터 흐름 설계
- [x] 구현 순서 정리
- [x] 테스트 전략 수립
- [x] 위험 요소 식별
- [x] 예상 시간 산정
- [x] 설정 예시 작성
- [x] Level 6~8 개요 작성
