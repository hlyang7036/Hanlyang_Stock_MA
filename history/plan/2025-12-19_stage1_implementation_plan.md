# Stage 1 진입 로직 구현 계획

**작성일**: 2025-12-19
**목표**: 안정 상승기(Stage 1) 진입 로직 구현 및 백테스팅 검증
**기대 효과**: Stage 6 (25% 승률) 대비 Stage 1 (예상 60%+ 승률) 개선

---

## 배경

### 문제 인식

1. **Stage 6의 낮은 승률**: 24.2% (8/33건) - 변화기의 불확실성
2. **안정기 미활용**: Stage 1/4 진입 로직 미구현
3. **전략 문서 불일치**: 문서는 Stage 1 공격적 매수 권장, 현재는 미구현

### Stage 1의 우월성

| 비교 항목 | Stage 6 (변화기) | Stage 1 (안정기) |
|----------|----------------|----------------|
| 시장 국면 | 상승장의 "입구" | 상승장 "확정" |
| 배열 | 단기>장기>중기 (불완전) | 단기>중기>장기 (완전 정배열) |
| MACD 신호 | MACD(중) -→0 | MACD(하) -→0 |
| 추세 강도 | 약함 | 강함 |
| 불확실성 | 높음 | 낮음 |
| 문서 권고 | "무리한 확대 금지" | "공격적 매수" |
| 예상 승률 | 25% (실제) | 60%+ (예상) |

---

## Phase 1: Stage 1 진입 신호 구현

**목표**: `entry.py`에 Stage 1 매수 신호 함수 추가

### 1.1 함수 설계

**파일**: `src/analysis/signal/entry.py`

```python
def generate_stage1_buy_signal(
    data: pd.DataFrame
) -> pd.DataFrame:
    """
    Stage 1 안정 상승기 매수 신호 생성

    Stage 1 특징:
    - 완전 정배열 (단기 > 중기 > 장기)
    - MACD(하) 골든크로스 완료 (중기선이 장기선을 상향 돌파)
    - 상승 추세 확정 단계

    Args:
        data: DataFrame (Stage, Dir_MACD_상, Dir_MACD_중, Dir_MACD_하, MACD_하, Close 필요)

    Returns:
        pd.DataFrame: 신호 정보
            - Buy_Signal: 매수 신호 (0: 없음, 3: Stage 1 매수)
            - Signal_Reason: 신호 발생 이유

    Notes:
        진입 조건:
        1. Stage == 1 (완전 정배열)
        2. 3개 MACD 모두 우상향 (상승 추세 확인)
        3. MACD(하) >= 0 (골든크로스3 이후 확인)

        신호 값:
        - 3: Stage 1 매수 (가장 강력한 신호)

        전략 문서 근거:
        - "제1스테이지 진입: 상승 확정 시점, 놓치지 말아야 할 매수 기회"
        - "이 시기가 가장 큰 수익을 낼 수 있는 구간"

    Examples:
        >>> df_with_signal = generate_stage1_buy_signal(df)
        >>> stage1_signals = df_with_signal[df_with_signal['Buy_Signal'] == 3]
    """
    # 입력 검증
    if not isinstance(data, pd.DataFrame):
        raise TypeError(f"DataFrame이 필요합니다. 입력 타입: {type(data)}")

    required_columns = ['Stage', 'Dir_MACD_상', 'Dir_MACD_중', 'Dir_MACD_하', 'MACD_하', 'Close']
    missing_columns = [col for col in required_columns if col not in data.columns]
    if missing_columns:
        raise ValueError(f"필수 컬럼이 없습니다: {missing_columns}")

    logger.debug(f"Stage 1 매수 신호 생성 시작: {len(data)}개 데이터")

    # 결과 DataFrame 초기화
    result = pd.DataFrame(index=data.index)
    result['Buy_Signal'] = 0
    result['Signal_Reason'] = ''

    # 조건 1: Stage 1 (완전 정배열)
    stage_condition = (data['Stage'] == 1)

    # 조건 2: MACD 방향 (3개 모두 우상향)
    macd_direction_condition = (
        (data['Dir_MACD_상'] == 'up') &
        (data['Dir_MACD_중'] == 'up') &
        (data['Dir_MACD_하'] == 'up')
    )

    # 조건 3: MACD(하) >= 0 (골든크로스3 완료 확인)
    macd_below_positive = (data['MACD_하'] >= 0)

    # 신호 생성
    signal_mask = stage_condition & macd_direction_condition & macd_below_positive
    result.loc[signal_mask, 'Buy_Signal'] = 3
    result.loc[signal_mask, 'Signal_Reason'] = (
        "Stage 1 매수: 안정 상승기 + 3개 MACD 상승 + 완전 정배열"
    )

    # 통계 로깅
    signal_count = signal_mask.sum()
    if signal_count > 0:
        logger.info(f"Stage 1 매수 신호 발생: {signal_count}회")
        avg_price = data.loc[signal_mask, 'Close'].mean()
        logger.debug(f"신호 발생 평균 가격: {avg_price:,.0f}원")
    else:
        logger.debug("Stage 1 매수 신호 없음")

    logger.debug("Stage 1 매수 신호 생성 완료")

    return result
```

### 1.2 generate_entry_signals() 통합

**수정 위치**: `entry.py` lines 297-398

```python
def generate_entry_signals(
    data: pd.DataFrame,
    enable_early: bool = False,
    enable_stage1: bool = True  # 신규 파라미터
) -> pd.DataFrame:
    """
    통합 진입 신호 생성 (매수 + 매도)

    Args:
        data: DataFrame (전체 지표 데이터)
        enable_early: 조기 진입 신호 활성화 여부
        enable_stage1: Stage 1 진입 신호 활성화 여부 (신규)

    Returns:
        pd.DataFrame: 통합 신호
            - Entry_Signal: 진입 신호
                (-2: 조기매도, -1: 통상매도, 0: 없음, 1: 통상매수, 2: 조기매수, 3: Stage1매수)
            - Signal_Type: 신호 타입 ('buy', 'sell', None)
            - Signal_Reason: 신호 발생 이유
    """
    # ... 기존 코드 ...

    # Stage 1 매수 신호 (신규)
    if enable_stage1:
        stage1_buy = generate_stage1_buy_signal(data)
        stage1_buy_mask = stage1_buy['Buy_Signal'] > 0
        # 다른 신호가 없는 곳에만 Stage 1 신호 적용
        stage1_buy_only = stage1_buy_mask & (result['Entry_Signal'] == 0)
        result.loc[stage1_buy_only, 'Entry_Signal'] = 3
        result.loc[stage1_buy_only, 'Signal_Type'] = 'buy'
        result.loc[stage1_buy_only, 'Signal_Reason'] = stage1_buy.loc[stage1_buy_only, 'Signal_Reason']

    # ... 통계 로깅 ...

    return result
```

### 1.3 신호 우선순위 정의

**현재**:
- Buy_Signal: 1 (통상), 2 (조기)
- Sell_Signal: -1 (통상), -2 (조기)

**변경 후**:
```python
# 매수 신호
1: Stage 6 통상 매수 (변화기)
2: Stage 5 조기 매수 (변화기)
3: Stage 1 안정기 매수 (안정기) ← 신규

# 매도 신호
-1: Stage 3 통상 매도 (변화기)
-2: Stage 2 조기 매도 (변화기)
-3: Stage 4 안정기 매도 (안정기) ← 향후 추가 가능
```

**처리 우선순위**:
- 같은 날짜에 여러 신호 발생 시: 절댓값이 큰 신호 우선
- Stage 1 (3) > Stage 5 (2) > Stage 6 (1)

---

## Phase 2: 테스트 코드 작성

**목표**: `test_entry.py`에 Stage 1 신호 테스트 추가

### 2.1 테스트 케이스 설계

**파일**: `src/tests/analysis/signal/test_entry.py`

```python
class TestGenerateStage1BuySignal:
    """Stage 1 매수 신호 생성 테스트"""

    def test_stage1_signal_basic(self):
        """Stage 1 기본 신호 생성 테스트"""
        # Stage 1 조건 충족 데이터
        data = pd.DataFrame({
            'Stage': [1, 1, 1],
            'Dir_MACD_상': ['up', 'up', 'up'],
            'Dir_MACD_중': ['up', 'up', 'up'],
            'Dir_MACD_하': ['up', 'up', 'up'],
            'MACD_하': [0.5, 1.0, 1.5],  # 양수
            'Close': [10000, 10100, 10200]
        })

        result = generate_stage1_buy_signal(data)

        assert all(result['Buy_Signal'] == 3)
        assert all('Stage 1' in reason for reason in result['Signal_Reason'])

    def test_stage1_no_signal_wrong_stage(self):
        """Stage가 1이 아닐 때 신호 없음"""
        data = pd.DataFrame({
            'Stage': [6, 6, 6],  # Stage 6
            'Dir_MACD_상': ['up', 'up', 'up'],
            'Dir_MACD_중': ['up', 'up', 'up'],
            'Dir_MACD_하': ['up', 'up', 'up'],
            'MACD_하': [0.5, 1.0, 1.5],
            'Close': [10000, 10100, 10200]
        })

        result = generate_stage1_buy_signal(data)

        assert all(result['Buy_Signal'] == 0)

    def test_stage1_no_signal_macd_negative(self):
        """MACD(하)가 음수일 때 신호 없음"""
        data = pd.DataFrame({
            'Stage': [1, 1, 1],
            'Dir_MACD_상': ['up', 'up', 'up'],
            'Dir_MACD_중': ['up', 'up', 'up'],
            'Dir_MACD_하': ['up', 'up', 'up'],
            'MACD_하': [-0.5, -0.1, -0.01],  # 음수
            'Close': [10000, 10100, 10200]
        })

        result = generate_stage1_buy_signal(data)

        assert all(result['Buy_Signal'] == 0)

    def test_stage1_no_signal_macd_down(self):
        """MACD 방향이 하락일 때 신호 없음"""
        data = pd.DataFrame({
            'Stage': [1, 1, 1],
            'Dir_MACD_상': ['down', 'down', 'down'],  # 하락
            'Dir_MACD_중': ['up', 'up', 'up'],
            'Dir_MACD_하': ['up', 'up', 'up'],
            'MACD_하': [0.5, 1.0, 1.5],
            'Close': [10000, 10100, 10200]
        })

        result = generate_stage1_buy_signal(data)

        assert all(result['Buy_Signal'] == 0)
```

### 2.2 통합 테스트

```python
def test_generate_entry_signals_with_stage1():
    """Stage 1 신호 포함 통합 테스트"""
    data = pd.DataFrame({
        'Stage': [6, 1, 3],
        'Dir_MACD_상': ['up', 'up', 'down'],
        'Dir_MACD_중': ['up', 'up', 'down'],
        'Dir_MACD_하': ['up', 'up', 'down'],
        'MACD_하': [-0.1, 0.5, 0.3],
        'Close': [10000, 10100, 10200]
    })

    result = generate_entry_signals(data, enable_early=False, enable_stage1=True)

    # Stage 6: Entry_Signal = 1
    assert result.iloc[0]['Entry_Signal'] == 1

    # Stage 1: Entry_Signal = 3
    assert result.iloc[1]['Entry_Signal'] == 3

    # Stage 3: Entry_Signal = -1
    assert result.iloc[2]['Entry_Signal'] == -1
```

---

## Phase 3: 백테스팅 엔진 수정

**목표**: `engine.py`에서 Stage 1 신호 처리

### 3.1 BacktestEngine 설정 추가

**파일**: `src/backtest/engine.py`

```python
class BacktestEngine:
    def __init__(self, config: Dict[str, Any]):
        # ... 기존 설정 ...

        # Stage 1 신호 활성화 여부
        self.enable_stage1 = config.get('enable_stage1_signals', True)

        logger.info(f"백테스트 설정: enable_stage1={self.enable_stage1}")
```

### 3.2 신호 생성 시 Stage 1 활성화

**수정 위치**: `engine.py` line 467

```python
entry_signals = generate_entry_signals(
    data=historical_data,
    enable_early=self.config.get('enable_early_signals', False),
    enable_stage1=self.config.get('enable_stage1_signals', True)  # 신규
)
```

### 3.3 신호 타입 매핑

```python
# 신호 분류
signals.append({
    'ticker': ticker,
    'action': 'buy' if latest_signal['Entry_Signal'] > 0 else 'sell',
    'signal_type': self._map_signal_type(latest_signal['Entry_Signal']),
    'signal_strength': int(strength),
    'current_price': current_prices.get(ticker, historical_data['Close'].iloc[-1]),
    'stage': historical_data['Stage'].iloc[-1],
    'entry_signal_value': latest_signal['Entry_Signal']  # 신규
})

def _map_signal_type(self, signal_value: int) -> str:
    """신호 값을 타입 문자열로 매핑"""
    mapping = {
        3: 'stage1_buy',    # 신규
        2: 'early_buy',
        1: 'normal_buy',
        -1: 'normal_sell',
        -2: 'early_sell'
    }
    return mapping.get(signal_value, 'unknown')
```

---

## Phase 4: 백테스팅 실행 및 분석

**목표**: Stage 1 vs Stage 6 vs 조합 전략 성과 비교

### 4.1 백테스팅 시나리오

**시나리오 1: Stage 1 단독**
```python
config = {
    'enable_early_signals': False,
    'enable_stage1_signals': True,
    'enable_stage6_signals': False  # Stage 6 비활성화
}
```

**시나리오 2: Stage 6 단독 (기존)**
```python
config = {
    'enable_early_signals': False,
    'enable_stage1_signals': False,
    'enable_stage6_signals': True  # Stage 6만 활성화
}
```

**시나리오 3: Stage 1 + Stage 6 조합**
```python
config = {
    'enable_early_signals': False,
    'enable_stage1_signals': True,
    'enable_stage6_signals': True  # 둘 다 활성화
}
```

### 4.2 비교 지표

| 지표 | Stage 6 | Stage 1 | Stage 1+6 |
|-----|---------|---------|-----------|
| **총 수익률** | ? | ? | ? |
| **승률** | 24.2% | ? | ? |
| **총 거래 수** | 33건 | ? | ? |
| **평균 수익** | ? | ? | ? |
| **최대 낙폭** | 2.33% | ? | ? |
| **샤프 비율** | ? | ? | ? |

### 4.3 분석 스크립트

**파일**: `scripts/compare_stage_strategies.py` (신규 생성)

```python
"""
Stage 1 vs Stage 6 전략 비교 백테스팅
"""
import sys
sys.path.append('/Users/seunghakim/projects/Hanlyang_Stock_MA')

from src.backtest.engine import BacktestEngine
from src.backtest.analytics import PerformanceAnalyzer

# 공통 설정
base_config = {
    'start_date': '2025-06-01',
    'end_date': '2025-10-31',
    'initial_capital': 10_000_000,
    'market_tickers': ['코스피 200 종목']  # 실제 종목 리스트
}

# 시나리오 1: Stage 1 단독
config_stage1 = {
    **base_config,
    'enable_stage1_signals': True,
    'enable_early_signals': False
}

engine1 = BacktestEngine(config_stage1)
result1 = engine1.run()

# 시나리오 2: Stage 6 단독
config_stage6 = {
    **base_config,
    'enable_stage1_signals': False,
    'enable_early_signals': False
}

engine6 = BacktestEngine(config_stage6)
result6 = engine6.run()

# 시나리오 3: 조합
config_combined = {
    **base_config,
    'enable_stage1_signals': True,
    'enable_early_signals': False
}

engine_combined = BacktestEngine(config_combined)
result_combined = engine_combined.run()

# 결과 비교
print("=" * 80)
print("전략 비교 분석")
print("=" * 80)

strategies = [
    ("Stage 1 단독", result1),
    ("Stage 6 단독", result6),
    ("Stage 1 + 6", result_combined)
]

for name, result in strategies:
    print(f"\n### {name}")
    print(f"총 수익률: {result.total_return:.2f}%")
    print(f"승률: {result.win_rate:.2f}%")
    print(f"총 거래: {result.total_trades}건")
    print(f"최대 낙폭: {result.max_drawdown:.2f}%")
```

---

## Phase 5: 신호 필터 최적화

**목표**: Stage별 맞춤형 필터 적용

### 5.1 Stage별 임계값 조정

**파일**: `src/analysis/signal/filter.py`

```python
def check_strength_filter(
    data: pd.DataFrame,
    min_strength: int = 50,
    stage_based_threshold: bool = True
) -> pd.Series:
    """
    신호 강도 필터 (Stage별 임계값)

    Stage별 권장 임계값:
    - Stage 1: 30점 (안정기, 완화)
    - Stage 3: 30점 (하락 반전, 완화)
    - Stage 5: 50점 (변화기, 기본)
    - Stage 6: 50점 (변화기, 기본)
    """
    if not stage_based_threshold or 'Stage' not in data.columns:
        # 기존 로직
        return data['Signal_Strength'] >= min_strength

    # Stage별 임계값
    stage_thresholds = {
        1: 30,  # Stage 1: 완화 (안정기)
        2: 50,  # Stage 2: 기본
        3: 30,  # Stage 3: 완화 (반전 포착)
        4: 30,  # Stage 4: 완화 (안정기, 향후)
        5: 50,  # Stage 5: 기본
        6: 50   # Stage 6: 기본
    }

    passed = pd.Series(False, index=data.index)

    for stage, threshold in stage_thresholds.items():
        is_stage = data['Stage'] == stage
        stage_passed = data['Signal_Strength'] >= threshold
        passed = passed | (is_stage & stage_passed)

    return passed
```

### 5.2 추세 필터 Stage별 조정

```python
def check_trend_filter(
    data: pd.DataFrame,
    min_slope: float = 0.1,
    stage_based_slope: bool = True
) -> pd.Series:
    """
    추세 필터 (Stage별 기울기 임계값)

    Stage별 권장 기울기:
    - Stage 1: 0.05 (완만한 추세도 허용)
    - Stage 6: 0.1 (변화기, 명확한 추세 요구)
    """
    if not stage_based_slope or 'Stage' not in data.columns:
        return data['Slope_EMA_40'].abs() >= min_slope

    stage_slopes = {
        1: 0.05,  # Stage 1: 완화
        3: 0.05,  # Stage 3: 완화
        5: 0.1,   # Stage 5: 기본
        6: 0.1    # Stage 6: 기본
    }

    passed = pd.Series(False, index=data.index)

    for stage, slope_threshold in stage_slopes.items():
        is_stage = data['Stage'] == stage
        slope_passed = data['Slope_EMA_40'].abs() >= slope_threshold
        passed = passed | (is_stage & slope_passed)

    return passed
```

---

## Phase 6: 분석 및 리포트

**목표**: Stage 1 성과 분석 도구 추가

### 6.1 PerformanceAnalyzer 확장

**파일**: `src/backtest/analytics.py`

```python
def analyze_by_entry_signal(self) -> Dict[str, Dict[str, Any]]:
    """
    진입 신호별 성과 분석

    Returns:
        {
            'stage1_buy': {
                'count': int,
                'win_rate': float,
                'avg_pnl': float,
                'total_pnl': float
            },
            'normal_buy': {...},
            'early_buy': {...}
        }
    """
    if self.trades.empty:
        logger.warning("거래 내역이 없습니다")
        return {}

    # entry_signal_value 컬럼 활용
    signal_mapping = {
        3: 'stage1_buy',
        2: 'early_buy',
        1: 'normal_buy',
        -1: 'normal_sell',
        -2: 'early_sell'
    }

    results = {}

    for signal_value, signal_name in signal_mapping.items():
        signal_trades = self.trades[
            self.trades['entry_signal_value'] == signal_value
        ]

        if len(signal_trades) == 0:
            continue

        winning = signal_trades[signal_trades['pnl'] > 0]

        results[signal_name] = {
            'count': len(signal_trades),
            'win_rate': len(winning) / len(signal_trades) * 100,
            'avg_pnl': signal_trades['pnl'].mean(),
            'total_pnl': signal_trades['pnl'].sum(),
            'max_pnl': signal_trades['pnl'].max(),
            'min_pnl': signal_trades['pnl'].min()
        }

    return results
```

### 6.2 리포트 출력

```python
def generate_detailed_report(self) -> str:
    """
    상세 분석 리포트 (신호별 포함)
    """
    # ... 기존 리포트 ...

    # 신호별 분석 추가
    report_lines.append("\n=== 진입 신호별 분석 ===")

    signal_analysis = self.analyze_by_entry_signal()

    for signal_name, stats in signal_analysis.items():
        report_lines.append(f"\n{signal_name}:")
        report_lines.append(f"  거래 수: {stats['count']}건")
        report_lines.append(f"  승률: {stats['win_rate']:.2f}%")
        report_lines.append(f"  평균 손익: {stats['avg_pnl']:,.0f}원")
        report_lines.append(f"  총 손익: {stats['total_pnl']:,.0f}원")

    return "\n".join(report_lines)
```

---

## 구현 일정

| Phase | 작업 | 예상 시간 | 우선순위 |
|-------|------|----------|---------|
| **Phase 1** | Stage 1 진입 신호 구현 | 2시간 | 높음 |
| **Phase 2** | 테스트 코드 작성 | 1시간 | 높음 |
| **Phase 3** | 백테스트 엔진 수정 | 1시간 | 높음 |
| **Phase 4** | 백테스팅 실행 및 비교 | 1시간 | 높음 |
| **Phase 5** | 신호 필터 최적화 | 2시간 | 중간 |
| **Phase 6** | 분석 및 리포트 | 1시간 | 중간 |

**총 예상 시간**: 8시간

---

## 성공 기준

### 필수 기준

1. **구현 완료**:
   - ✅ `generate_stage1_buy_signal()` 함수 작성
   - ✅ `generate_entry_signals()`에 통합
   - ✅ 백테스트 엔진 연동

2. **테스트 통과**:
   - ✅ 모든 단위 테스트 통과
   - ✅ 통합 테스트 통과

3. **백테스팅 성공**:
   - ✅ Stage 1 신호 정상 생성
   - ✅ 거래 실행 및 결과 수집

### 성과 기준

1. **승률 개선**:
   - Stage 1 승률 > 50% (Stage 6 24.2% 대비)

2. **총 수익률**:
   - Stage 1 수익률 >= Stage 6 수익률

3. **위험 대비 수익**:
   - 샤프 비율 개선
   - MDD 유지 또는 개선

---

## 위험 요소 및 대응

### 위험 1: Stage 1 신호 부족

**원인**: Stage 1 진입 조건이 너무 엄격
**증상**: 백테스팅 기간 동안 신호 10건 미만
**대응**:
- MACD(하) >= 0 조건 완화 (제거 또는 음수 허용)
- 3개 MACD 조건 완화 (2개 이상 상승)

### 위험 2: Stage 1 승률 기대 미달

**원인**: Stage 1에서도 변동성 높은 구간 존재
**증상**: 승률 < 40%
**대응**:
- 추가 필터 적용 (변동성, 거래량)
- Stage 1 조기 진입 조건 추가 (MACD_하 > -0.1)

### 위험 3: 과최적화

**원인**: 특정 기간 데이터에 과적합
**증상**: 다른 기간 테스트 시 성과 급락
**대응**:
- 다양한 기간 백테스팅 (2024년, 2023년)
- 워크포워드 테스트

---

## 참고 자료

- 전략 문서: `Moving_Average_Investment_Strategy_Summary.md`
- 현재 코드: `src/analysis/signal/entry.py`
- 백테스트 엔진: `src/backtest/engine.py`
- 분석 도구: `src/backtest/analytics.py`