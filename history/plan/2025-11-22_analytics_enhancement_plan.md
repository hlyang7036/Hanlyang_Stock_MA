# Analytics.py 분석 기능 확장 계획

**작성일**: 2025-11-22
**대상 모듈**: `src/backtest/analytics.py`
**현재 상태**: 기본 분석 기능 구현 완료

---

## 1. 현재 구현된 기능

### PerformanceAnalyzer 클래스

| 메서드 | 설명 | 반환값 |
|--------|------|--------|
| `calculate_returns()` | 수익률 계산 | total_return, cagr, daily_return_mean/std, monthly_returns |
| `calculate_sharpe_ratio()` | 샤프 비율 | float |
| `calculate_max_drawdown()` | 최대 낙폭 | max_drawdown, peak/trough/recovery_date, duration_days |
| `calculate_win_rate()` | 승률 및 거래 통계 | total_trades, winning/losing_trades, win_rate, avg_win/loss |
| `calculate_profit_factor()` | 손익비 | float (총수익/총손실) |
| `generate_report()` | 종합 리포트 | str (텍스트 리포트) |
| `plot_equity_curve()` | 자산곡선 차트 | matplotlib 차트 |
| `plot_drawdown()` | 낙폭 차트 | matplotlib 차트 |
| `export_trades()` | 거래 내역 CSV | CSV 파일 |

---

## 2. 추가 구현 필요 기능

### 2.1 리스크 지표 확장 (우선순위: 높음)

#### 2.1.1 `calculate_sortino_ratio()`
**목적**: 하방 리스크만 고려한 위험조정 수익률

```python
def calculate_sortino_ratio(self, risk_free_rate: float = 0.03, target_return: float = 0.0) -> float:
    """
    소르티노 비율 계산

    샤프 비율과 달리 하방 변동성(downside deviation)만 고려합니다.
    손실 위험에 대한 보상을 더 정확하게 측정합니다.

    공식: (수익률 - 목표수익률) / 하방편차

    해석:
    - > 2.0: 매우 우수
    - 1.0 ~ 2.0: 우수
    - 0.5 ~ 1.0: 양호
    - < 0.5: 개선 필요
    """
```

#### 2.1.2 `calculate_calmar_ratio()`
**목적**: 연환산 수익률 대비 최대 낙폭 비율

```python
def calculate_calmar_ratio(self) -> float:
    """
    칼마 비율 계산

    공식: CAGR / MDD

    해석:
    - > 3.0: 매우 우수
    - 1.0 ~ 3.0: 우수
    - 0.5 ~ 1.0: 양호
    - < 0.5: 개선 필요
    """
```

#### 2.1.3 `calculate_recovery_factor()`
**목적**: 순이익 대비 최대 낙폭 비율

```python
def calculate_recovery_factor(self) -> float:
    """
    회복 팩터 계산

    공식: 순이익(원) / 최대낙폭금액(원)

    전략이 MDD에서 얼마나 빠르게 회복하는지 측정
    """
```

---

### 2.2 거래 심화 분석 (우선순위: 높음)

#### 2.2.1 `calculate_risk_reward_ratio()`
**목적**: 평균 수익/손실 비율 (손익비와 구분)

```python
def calculate_risk_reward_ratio(self) -> float:
    """
    위험보상비율 계산

    공식: |평균 수익| / |평균 손실|

    해석:
    - > 2.0: 우수 (손실 대비 수익이 2배 이상)
    - 1.5 ~ 2.0: 양호
    - 1.0 ~ 1.5: 보통
    - < 1.0: 개선 필요 (손실이 수익보다 큼)
    """
```

#### 2.2.2 `calculate_expected_value()`
**목적**: 거래당 기대값 계산

```python
def calculate_expected_value(self) -> float:
    """
    기대값 계산

    공식: (승률 × 평균수익) - (패률 × |평균손실|)

    양수면 장기적으로 수익, 음수면 장기적으로 손실
    """
```

#### 2.2.3 `calculate_consecutive_stats()`
**목적**: 연속 승패 통계

```python
def calculate_consecutive_stats(self) -> Dict[str, Any]:
    """
    연속 거래 통계

    Returns:
        - max_consecutive_wins: 최대 연속 수익 거래
        - max_consecutive_losses: 최대 연속 손실 거래
        - avg_consecutive_wins: 평균 연속 수익 거래
        - avg_consecutive_losses: 평균 연속 손실 거래

    최대 연속 손실은 자금 관리에 매우 중요
    """
```

---

### 2.3 거래 패턴 분석 (우선순위: 중간)

#### 2.3.1 `calculate_holding_period()`
**목적**: 평균 보유 기간 분석

```python
def calculate_holding_period(self) -> Dict[str, Any]:
    """
    보유 기간 분석

    Returns:
        - avg_holding_days: 평균 보유 일수
        - min_holding_days: 최소 보유 일수
        - max_holding_days: 최대 보유 일수
        - avg_winning_holding_days: 수익 거래 평균 보유 일수
        - avg_losing_holding_days: 손실 거래 평균 보유 일수

    수익/손실 거래별 보유 기간 차이 분석
    """
```

**필요 데이터**: trades에 `entry_date`, `exit_date` 컬럼 추가 필요

#### 2.3.2 `analyze_by_exit_reason()`
**목적**: 청산 사유별 성과 분석

```python
def analyze_by_exit_reason(self) -> Dict[str, Dict[str, Any]]:
    """
    청산 사유별 성과 분석

    Returns:
        {
            'stop_loss': {
                'count': int,
                'total_pnl': float,
                'avg_pnl': float,
                'win_rate': float
            },
            'exit_signal': {
                'count': int,
                'total_pnl': float,
                'avg_pnl': float,
                'win_rate': float
            },
            'target_profit': {...}
        }

    손절 vs 신호청산 효과 비교
    """
```

**필요 데이터**: trades에 `reason` 컬럼 활용

#### 2.3.3 `analyze_by_entry_stage()`
**목적**: 진입 스테이지별 성과 분석

```python
def analyze_by_entry_stage(self) -> Dict[str, Dict[str, Any]]:
    """
    진입 스테이지별 성과 분석

    Returns:
        {
            'stage_5': {
                'count': int,
                'total_pnl': float,
                'avg_pnl': float,
                'win_rate': float
            },
            'stage_6': {...}
        }

    조기진입(Stage 5) vs 통상진입(Stage 6) 효과 비교
    """
```

**필요 데이터**: trades에 `entry_stage` 컬럼 추가 필요

---

### 2.4 포지션 분석 (우선순위: 중간)

#### 2.4.1 `analyze_position_stats()`
**목적**: 포지션 관련 통계

```python
def analyze_position_stats(self) -> Dict[str, Any]:
    """
    포지션 통계 분석

    Returns:
        - max_concurrent_positions: 최대 동시 보유 포지션 수
        - avg_concurrent_positions: 평균 동시 보유 포지션 수
        - max_position_value: 최대 단일 포지션 가치
        - avg_position_value: 평균 포지션 가치
        - max_exposure: 최대 노출도 (%)
        - avg_exposure: 평균 노출도 (%)
    """
```

**필요 데이터**: portfolio_history의 `positions` 데이터 활용

---

### 2.5 시각화 확장 (우선순위: 낮음)

#### 2.5.1 `plot_monthly_returns_heatmap()`
**목적**: 월별 수익률 히트맵

```python
def plot_monthly_returns_heatmap(self, filepath: Optional[str] = None) -> None:
    """
    월별 수익률 히트맵 (연도 × 월)

    시각적으로 월별/연도별 성과 패턴 파악
    """
```

#### 2.5.2 `plot_trade_distribution()`
**목적**: 거래 손익 분포 히스토그램

```python
def plot_trade_distribution(self, filepath: Optional[str] = None) -> None:
    """
    거래 손익 분포 히스토그램

    손익 분포의 정규성, 꼬리 리스크 확인
    """
```

#### 2.5.3 `plot_rolling_sharpe()`
**목적**: 롤링 샤프 비율 차트

```python
def plot_rolling_sharpe(self, window: int = 60, filepath: Optional[str] = None) -> None:
    """
    롤링 샤프 비율 차트

    시간에 따른 전략 성과 안정성 확인
    """
```

---

## 3. 데이터 요구사항

현재 `trades` 딕셔너리에 추가로 필요한 필드:

| 필드 | 타입 | 설명 | 추가 위치 |
|------|------|------|-----------|
| `entry_date` | datetime | 진입 날짜 | portfolio.py |
| `exit_date` | datetime | 청산 날짜 | portfolio.py |
| `entry_stage` | int | 진입 시 스테이지 | engine.py |
| `holding_days` | int | 보유 일수 | portfolio.py |

현재 `portfolio_history`에 추가로 필요한 필드:

| 필드 | 타입 | 설명 | 추가 위치 |
|------|------|------|-----------|
| `position_count` | int | 보유 포지션 수 | portfolio.py |
| `exposure` | float | 노출도 (%) | portfolio.py |

---

## 4. 구현 순서

### Phase 1: 핵심 리스크 지표 (1일)
1. `calculate_sortino_ratio()`
2. `calculate_calmar_ratio()`
3. `calculate_recovery_factor()`
4. `calculate_risk_reward_ratio()`
5. `calculate_expected_value()`
6. `calculate_consecutive_stats()`

### Phase 2: 거래 패턴 분석 (1일)
1. 데이터 구조 확장 (portfolio.py, engine.py)
2. `calculate_holding_period()`
3. `analyze_by_exit_reason()`
4. `analyze_by_entry_stage()`

### Phase 3: 포지션 및 시각화 (1일)
1. `analyze_position_stats()`
2. `plot_monthly_returns_heatmap()`
3. `plot_trade_distribution()`
4. `plot_rolling_sharpe()`

### Phase 4: 리포트 통합 (0.5일)
1. `generate_report()` 확장
2. `generate_detailed_report()` 신규 추가

---

## 5. 테스트 계획

각 함수별 테스트 케이스:

1. **정상 케이스**: 충분한 거래 데이터
2. **엣지 케이스**:
   - 거래 없음
   - 모두 수익/손실
   - 단일 거래
3. **예외 처리**:
   - 필수 컬럼 누락
   - 잘못된 데이터 타입

---

## 6. 예상 결과

확장 후 `generate_report()` 출력 예시:

```
======================================================================
백테스팅 성과 분석 리포트
======================================================================

=== 수익률 지표 ===
초기 자본: 100,000,000원
최종 자본: 120,853,488원
총 수익률: 20.85%
연환산 수익률(CAGR): 50.04%

=== 리스크 지표 ===
샤프 비율: 2.15
소르티노 비율: 3.42
칼마 비율: 8.61
최대 낙폭(MDD): 2.42%
회복 팩터: 8.61

=== 거래 통계 ===
총 거래 수: 51건
승률: 47.06%
손익비(Profit Factor): 2.34
위험보상비율(R/R): 1.85
기대값: 408,926원/거래

=== 연속 거래 분석 ===
최대 연속 수익: 5회
최대 연속 손실: 3회

=== 보유 기간 분석 ===
평균 보유 기간: 12.3일
수익 거래 평균: 15.2일
손실 거래 평균: 8.7일

=== 청산 사유별 분석 ===
손절 청산: 15건 (29.4%), 평균 손실 -125,000원
신호 청산: 36건 (70.6%), 평균 수익 +580,000원

=== 스테이지별 분석 ===
Stage 5 진입: 18건, 승률 44.4%, 평균 +320,000원
Stage 6 진입: 33건, 승률 48.5%, 평균 +450,000원

======================================================================
```

---

## 7. 참고 자료

- Turtle Trading: 연속 손실 관리
- 이동평균선 투자법: 스테이지별 성과 기대값
- 금융 공학 표준 지표: Sharpe, Sortino, Calmar
