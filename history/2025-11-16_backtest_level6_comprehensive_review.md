# Level 6: 백테스팅 엔진 종합 리뷰

## 날짜
2025-11-16

## 목차
1. [개요](#개요)
2. [전체 아키텍처](#전체-아키텍처)
3. [Phase별 구현 내용](#phase별-구현-내용)
4. [모듈 통합 및 데이터 흐름](#모듈-통합-및-데이터-흐름)
5. [테스트 요약](#테스트-요약)
6. [성능 고려사항](#성능-고려사항)
7. [사용 예제](#사용-예제)
8. [향후 개선 방향](#향후-개선-방향)

---

## 개요

### 프로젝트 목표
백테스팅 엔진(Level 6)은 이동평균선 투자 전략의 과거 성과를 검증하기 위한 시뮬레이션 프레임워크입니다.
전체 시장(KOSPI + KOSDAQ ~2,400개 종목)을 일별로 스캔하여 Level 1-5 모듈을 통합 실행하고,
거래 신호 생성, 리스크 관리, 주문 체결, 성과 분석까지 전 과정을 자동화합니다.

### 핵심 특징
- **시장 전체 스캔**: 사전 선정이 아닌 전체 시장 일별 스캔
- **Look-ahead Bias 방지**: 철저한 시점별 데이터 격리
- **병렬 처리**: ThreadPoolExecutor를 통한 데이터 로딩 최적화
- **캐싱**: pickle 기반 데이터 재사용
- **포트폴리오 제한 제외**: 자본 제약만 적용 (Level 5-3 제외)
- **실전 수수료/슬리피지**: 한국 시장 기준 (수수료 0.015%, 슬리피지 0.1%)
- **종합 성과 분석**: 수익률, 리스크, 거래 통계, 시각화

### 개발 기간 및 규모
- **개발 기간**: 2025-11-16 (1일)
- **총 라인 수**: ~3,000 lines (주석 포함)
- **테스트 커버리지**: 6개 모듈, 97개 테스트, 100% 통과
- **문서화**: 5개 상세 개발 이력 + 1개 종합 리뷰

---

## 전체 아키텍처

### 시스템 구성도

```
┌─────────────────────────────────────────────────────────────────┐
│                       BacktestEngine                            │
│  (src/backtest/engine.py)                                       │
│                                                                 │
│  - run_backtest(): 전체 프로세스 오케스트레이션                 │
│  - process_day(): 일별 시뮬레이션 루프                         │
│  - generate_and_execute_entries(): 진입 신호 처리               │
│  - generate_and_execute_exits(): 청산 신호 처리                 │
│  - check_and_execute_stops(): 손절 체크 및 실행                │
└────────────────┬────────────────────────────────────────────────┘
                 │
     ┌───────────┼───────────┬───────────────┬──────────────┐
     │           │           │               │              │
     ▼           ▼           ▼               ▼              ▼
┌─────────┐ ┌─────────┐ ┌──────────┐ ┌───────────┐ ┌────────────┐
│  Data   │ │Portfolio│ │Execution │ │  Signal   │ │  Analytics │
│ Manager │ │         │ │  Engine  │ │ Generator │ │            │
└─────────┘ └─────────┘ └──────────┘ └───────────┘ └────────────┘
     │           │           │               │              │
     │           │           │               │              │
  (Level 6-2) (Level 6-1) (Level 6-1)   (Level 4)     (Level 6-4)
```

### 모듈별 책임

| 모듈 | 파일 | 주요 역할 | Phase |
|------|------|-----------|-------|
| **Portfolio** | portfolio.py | 포지션 추적, 손익 계산, 손절 관리 | 1-1 |
| **ExecutionEngine** | execution.py | 주문 체결, 수수료/슬리피지 적용 | 1-2 |
| **DataManager** | data_manager.py | 시장 데이터 로딩, 병렬 처리, 캐싱 | 2 |
| **BacktestEngine** | engine.py | 메인 엔진, 일별 루프, 신호 통합 | 3 |
| **PerformanceAnalyzer** | analytics.py | 성과 분석, 리포트, 시각화 | 4 |

---

## Phase별 구현 내용

### Phase 1-1: Portfolio 관리 (portfolio.py)

**주요 클래스**:
1. **Position** - 개별 포지션 정보
   - 진입가, 보유 수량, 유닛 수
   - 손절가 및 유형 (변동성/추세)
   - 트레일링 스톱용 최고가/최저가
   - 미실현/실현 손익 계산

2. **Portfolio** - 전체 포트폴리오 관리
   - 현금 관리 (`cash`, `initial_capital`)
   - 포지션 관리 (`positions`, `closed_positions`)
   - 히스토리 추적 (`history`, `take_snapshot()`)
   - 트레일링 스톱 업데이트

**테스트**: 20개, 0.19s, 100% 통과

**참고 문서**: `history/2025-11-16_backtest_level6_1_portfolio.md`

---

### Phase 1-2: Execution 엔진 (execution.py)

**주요 기능**:
- 시장가 매수/매도 체결
- 수수료 계산: 0.015% (한국 시장 기준)
- 슬리피지 적용: 0.1% (불리한 방향)
  - 매수 시: `실제가 = 주문가 × (1 + 0.001)`
  - 매도 시: `실제가 = 주문가 × (1 - 0.001)`
- 부분 청산 지원
- 자본 부족 시 주문 거부

**테스트**: 15개, 0.18s, 100% 통과

**참고 문서**: `history/2025-11-16_backtest_level6_1_execution.md`

---

### Phase 2: Data Manager (data_manager.py)

**주요 기능**:
1. **전체 시장 종목 조회**
   - `get_all_market_tickers(market)`: KOSPI/KOSDAQ/ALL
   - FinanceDataReader.StockListing() 사용

2. **병렬 데이터 로딩**
   - ThreadPoolExecutor (10 workers)
   - tqdm 진행률 표시
   - 개별 종목별 에러 핸들링

3. **기술적 지표 자동 계산**
   - EMA (5, 20, 40), MACD (상/중/하), ATR, RSI
   - Stage 판단 (Level 3 통합)

4. **캐싱 시스템**
   - pickle 기반 저장/로드
   - 시작일+종료일+시장 기반 캐시 키

**성능**:
- 첫 로딩: ~20분 (2,400개 종목)
- 캐시 사용: ~1분

**테스트**: 18개, 1.90s, 100% 통과

**참고 문서**: `history/2025-11-16_backtest_level6_2_data_manager.md`

---

### Phase 3: Backtest Engine (engine.py)

**주요 클래스**:
1. **BacktestResult** - 결과 데이터 클래스
   - 수익률, MDD, 승률, 거래 통계
   - `summary()`: 요약 리포트 생성

2. **BacktestEngine** - 메인 엔진
   - `run_backtest()`: 전체 프로세스 실행
   - `process_day()`: 일별 시뮬레이션
   - 신호 생성 + 리스크 관리 + 주문 실행 통합

**일별 처리 순서**:
```python
for date in trading_dates:
    1. 트레일링 스톱 업데이트
    2. 손절 체크 및 실행 (check_and_execute_stops)
    3. 청산 신호 처리 (보유 종목만)
    4. 진입 신호 처리 (전체 시장 스캔)
    5. 포트폴리오 스냅샷 기록
```

**Look-ahead Bias 방지**:
```python
# 현재 날짜까지의 데이터만 사용
date_idx = data.index.get_loc(date)
historical_data = data.iloc[:date_idx + 1]

# 신호 생성에 historical_data만 전달
entry_signals = generate_entry_signals(data=historical_data, ...)
```

**테스트**: 17개, 0.25s, 100% 통과

**참고 문서**: `history/2025-11-16_backtest_level6_3_engine.md`

---

### Phase 4: Performance Analytics (analytics.py)

**주요 기능**:

1. **수익률 분석**
   - 총 수익률, CAGR (연환산)
   - 일별/월별 수익률
   - 평균, 표준편차

2. **리스크 분석**
   - 샤프 비율 (리스크 조정 수익률)
   - 최대 낙폭 (MDD) + 회복 기간

3. **거래 통계**
   - 승률, 평균 수익/손실
   - 손익비 (Profit Factor)

4. **시각화 및 리포트**
   - 자산곡선 차트 (matplotlib)
   - 낙폭 차트
   - 종합 텍스트 리포트
   - CSV export

**주요 메트릭 계산**:
```python
# CAGR
years = days / 252
cagr = ((final / initial) ** (1 / years) - 1) * 100

# Sharpe Ratio
sharpe = (excess_return / volatility) * sqrt(252)

# MDD
drawdown = (equity - cummax) / cummax * 100
max_dd = drawdown.min()

# Profit Factor
pf = total_profit / total_loss
```

**테스트**: 31개, 0.48s, 100% 통과

**참고 문서**: `history/2025-11-16_backtest_level6_4_analytics.md`

---

## 모듈 통합 및 데이터 흐름

### 전체 실행 흐름

```
1. 백테스트 시작 (BacktestEngine.run_backtest)
   ├─ DataManager.load_market_data()
   │  ├─ 캐시 확인
   │  ├─ 없으면 병렬 로딩 (ThreadPoolExecutor)
   │  └─ 기술적 지표 계산 (Level 2, 3)
   │
   ├─ Portfolio 초기화
   │
   └─ 일별 루프 (process_day)
      │
      ├─ 트레일링 스톱 업데이트
      │  └─ Portfolio.update_trailing_stops()
      │
      ├─ 손절 체크 (check_and_execute_stops)
      │  ├─ Level 5: calculate_stop_loss()
      │  └─ ExecutionEngine.execute_sell()
      │
      ├─ 청산 신호 처리 (보유 종목만)
      │  ├─ Level 4: generate_exit_signal()
      │  └─ ExecutionEngine.execute_sell()
      │
      ├─ 진입 신호 처리 (전체 시장)
      │  ├─ Level 4: generate_entry_signals()
      │  ├─ Level 4: evaluate_signal_strength()
      │  ├─ Level 5: apply_risk_management()
      │  │  ├─ calculate_position_size()
      │  │  ├─ calculate_stop_loss()
      │  │  └─ check_capital_limit()
      │  └─ ExecutionEngine.execute_buy()
      │
      └─ Portfolio.take_snapshot()

2. 성과 분석 (PerformanceAnalyzer)
   ├─ calculate_returns()
   ├─ calculate_sharpe_ratio()
   ├─ calculate_max_drawdown()
   ├─ calculate_win_rate()
   ├─ calculate_profit_factor()
   └─ generate_report()
```

### 모듈 간 인터페이스

#### DataManager → BacktestEngine
```python
market_data = data_manager.load_market_data(
    start_date='2020-01-01',
    end_date='2023-12-31',
    market='ALL'
)
# Returns: Dict[ticker, DataFrame]
# DataFrame columns: OHLCV + EMA_5/20/40 + MACD + ATR + Stage
```

#### BacktestEngine → Level 4 (Signals)
```python
# 진입 신호 생성
entry_signals = generate_entry_signals(
    data=historical_data,  # 과거 데이터만
    enable_early_signals=True
)

# 청산 신호 생성
exit_signal = generate_exit_signal(
    data=historical_data,
    position_type='long'
)
```

#### Level 4 → Level 5 (Risk Management)
```python
approved_signals = apply_risk_management(
    signals=entry_signals,
    data=historical_data,
    portfolio=self.portfolio,
    config=self.config
)
```

#### BacktestEngine → ExecutionEngine
```python
result = execution_engine.execute_buy(
    ticker='005930',
    price=50000,
    shares=100,
    units=1,
    stop_price=48000,
    stop_type='volatility'
)
```

#### BacktestEngine → PerformanceAnalyzer
```python
analyzer = PerformanceAnalyzer(
    portfolio_history=self.portfolio.history,
    trades=self.portfolio.closed_positions,
    initial_capital=initial_capital
)

report = analyzer.generate_report()
analyzer.plot_equity_curve('equity_curve.png')
```

---

## 테스트 요약

### 전체 테스트 통계

| 모듈 | 테스트 수 | 실행 시간 | 성공률 | 파일 |
|------|-----------|-----------|--------|------|
| Portfolio | 20 | 0.19s | 100% | test_portfolio.py |
| ExecutionEngine | 15 | 0.18s | 100% | test_execution.py |
| DataManager | 18 | 1.90s | 100% | test_data_manager.py |
| BacktestEngine | 17 | 0.25s | 100% | test_backtest_engine.py |
| PerformanceAnalyzer | 31 | 0.48s | 100% | test_analytics.py |
| **합계** | **101** | **3.00s** | **100%** | - |

### 테스트 커버리지 상세

#### Portfolio (20 tests)
- Position 생성 및 속성 (3)
- 평가액 및 손익 계산 (5)
- 극값 업데이트 (2)
- Portfolio 초기화 및 스냅샷 (4)
- 트레일링 스톱 (3)
- 통계 및 요약 (3)

#### ExecutionEngine (15 tests)
- 엔진 초기화 (2)
- 매수 주문 (5)
- 매도 주문 (5)
- 부분 청산 (2)
- 에러 처리 (1)

#### DataManager (18 tests)
- 초기화 (2)
- 종목 조회 (4)
- 데이터 로딩 (6)
- 캐싱 (3)
- 통합 테스트 (3)

#### BacktestEngine (17 tests)
- BacktestResult (2)
- 엔진 초기화 (2)
- 헬퍼 메서드 (6)
- 신호 처리 (4)
- 통합 테스트 (3)

#### PerformanceAnalyzer (31 tests)
- 초기화 (2)
- 수익률 계산 (3)
- 샤프 비율 (4)
- 최대 낙폭 (4)
- 승률 (4)
- 손익비 (4)
- 리포트 (2)
- 시각화 (5)
- Export (2)
- 통합 테스트 (1)

### 테스트 전략

1. **단위 테스트**: 각 메서드 개별 검증
2. **통합 테스트**: 모듈 간 연동 검증
3. **엣지 케이스**: 빈 데이터, 0값, 극값 등
4. **모킹**: 외부 의존성 격리 (FinanceDataReader, matplotlib)
5. **실제 시나리오**: 실전 데이터와 유사한 테스트

---

## 성능 고려사항

### 1. 데이터 로딩 최적화

**병렬 처리**:
```python
with ThreadPoolExecutor(max_workers=10) as executor:
    futures = {
        executor.submit(load_data, ticker): ticker
        for ticker in tickers
    }
    for future in as_completed(futures):
        result = future.result()
```

**성능 측정**:
- 순차 로딩 (예상): ~80분 (2,400 종목 × 2초)
- 병렬 로딩 (10 workers): ~20분 (4배 향상)
- 캐시 사용: ~1분 (20배 향상)

### 2. 캐싱 전략

**캐시 키 생성**:
```python
cache_key = f"{start_date}_{end_date}_{market}"
cache_file = f"backtest_data_{cache_key}.pkl"
```

**캐시 사용 조건**:
- 동일한 start_date, end_date, market
- 캐시 파일 존재
- `use_cache=True` 설정

**캐시 무효화**:
- 날짜 범위 변경
- 시장 변경
- 수동 삭제

### 3. 메모리 관리

**메모리 사용량 (추정)**:
- 1개 종목 데이터: ~50KB (252일 × 15 columns)
- 2,400개 종목: ~120MB
- 포트폴리오 히스토리: ~5MB (252일 × 100 스냅샷)
- **총**: ~125MB (합리적 수준)

**메모리 절감 방법**:
- 불필요한 컬럼 제거
- 데이터 타입 최적화 (float64 → float32)
- 청크 단위 처리 (필요 시)

### 4. 실행 시간 분석

**1년 백테스트 (252일) 예상 시간**:
```
데이터 로딩 (첫 실행): 20분
데이터 로딩 (캐시):     1분
일별 루프:             5분
  ├─ 손절 체크:         0.5분
  ├─ 청산 신호:         1분
  ├─ 진입 신호:         3분 (2,400 종목 스캔)
  └─ 스냅샷:            0.5분
성과 분석:             0.5분
────────────────────────────
총 (첫 실행):         25.5분
총 (캐시 사용):        6.5분
```

### 5. 최적화 기회

**단기 개선**:
- [ ] 신호 생성 벡터화 (apply → vectorized ops)
- [ ] 불필요한 재계산 제거 (indicators)
- [ ] 병렬 신호 생성 (종목별 독립)

**중기 개선**:
- [ ] Numba JIT 컴파일 (핫스팟 함수)
- [ ] Cython 변환 (계산 집약적 부분)
- [ ] HDF5 포맷 전환 (pickle → HDF5)

**장기 개선**:
- [ ] 분산 처리 (Dask, Ray)
- [ ] GPU 가속 (CuPy, Rapids)
- [ ] 스트리밍 처리 (대용량 데이터)

---

## 사용 예제

### 기본 사용법

```python
from src.backtest.engine import BacktestEngine
from src.backtest.analytics import PerformanceAnalyzer

# 1. 백테스팅 엔진 초기화
config = {
    'use_cache': True,                  # 캐시 사용
    'commission_rate': 0.00015,         # 수수료 0.015%
    'slippage_pct': 0.001,             # 슬리피지 0.1%
    'enable_early_signals': True        # 조기 신호 허용
}

engine = BacktestEngine(config=config)

# 2. 백테스팅 실행
result = engine.run_backtest(
    start_date='2020-01-01',
    end_date='2023-12-31',
    initial_capital=100_000_000,        # 1억원
    market='ALL'                        # KOSPI + KOSDAQ
)

# 3. 결과 요약 출력
print(result.summary())

# 4. 성과 분석
analyzer = PerformanceAnalyzer(
    portfolio_history=result.portfolio_history,
    trades=result.trades,
    initial_capital=result.initial_capital
)

# 5. 상세 리포트 생성
report = analyzer.generate_report()
print(report)

# 6. 차트 저장
analyzer.plot_equity_curve('equity_curve.png')
analyzer.plot_drawdown('drawdown.png')

# 7. 거래 내역 export
analyzer.export_trades('trades.csv')
```

### 고급 사용 예제

```python
# 1. 여러 기간 비교
periods = [
    ('2018-01-01', '2019-12-31', '2년_전'),
    ('2020-01-01', '2021-12-31', '코로나'),
    ('2022-01-01', '2023-12-31', '최근')
]

results = {}
for start, end, label in periods:
    result = engine.run_backtest(
        start_date=start,
        end_date=end,
        initial_capital=100_000_000,
        market='ALL'
    )
    results[label] = result
    print(f"\n=== {label} ===")
    print(result.summary())

# 2. 시장별 비교 (KOSPI vs KOSDAQ)
markets = ['KOSPI', 'KOSDAQ', 'ALL']
for market in markets:
    result = engine.run_backtest(
        start_date='2020-01-01',
        end_date='2023-12-31',
        initial_capital=100_000_000,
        market=market
    )
    print(f"\n=== {market} ===")
    print(f"총 수익률: {result.total_return:.2f}%")
    print(f"승률: {result.win_rate:.2f}%")
    print(f"거래 수: {result.total_trades}건")

# 3. 파라미터 최적화 (Grid Search)
configs = []
for early in [True, False]:
    for risk_pct in [0.01, 0.015, 0.02]:
        for atr_mult in [1.5, 2.0, 2.5]:
            configs.append({
                'enable_early_signals': early,
                'risk_percentage': risk_pct,
                'atr_multiplier': atr_mult
            })

best_result = None
best_sharpe = -float('inf')

for config in configs:
    engine = BacktestEngine(config=config)
    result = engine.run_backtest(
        start_date='2020-01-01',
        end_date='2023-12-31',
        initial_capital=100_000_000,
        market='ALL'
    )

    analyzer = PerformanceAnalyzer(
        portfolio_history=result.portfolio_history,
        trades=result.trades,
        initial_capital=result.initial_capital
    )

    sharpe = analyzer.calculate_sharpe_ratio()

    if sharpe > best_sharpe:
        best_sharpe = sharpe
        best_result = (config, result, sharpe)

print("\n=== 최적 파라미터 ===")
print(f"Config: {best_result[0]}")
print(f"Sharpe: {best_result[2]:.2f}")
print(best_result[1].summary())
```

### 사용 시 주의사항

1. **캐시 관리**:
   ```python
   # 캐시 사용 (빠른 실행)
   engine = BacktestEngine(config={'use_cache': True})

   # 캐시 무시 (최신 데이터 반영)
   engine = BacktestEngine(config={'use_cache': False})
   ```

2. **메모리 부족 시**:
   ```python
   # 시장을 나눠서 실행
   result_kospi = engine.run_backtest(..., market='KOSPI')
   result_kosdaq = engine.run_backtest(..., market='KOSDAQ')
   ```

3. **긴 백테스트 기간**:
   ```python
   # 연도별로 나눠서 실행
   for year in range(2018, 2024):
       result = engine.run_backtest(
           start_date=f'{year}-01-01',
           end_date=f'{year}-12-31',
           ...
       )
   ```

---

## 향후 개선 방향

### 단기 (1-2주)

#### 1. Walk-Forward Optimization
- **목적**: 과적합 방지
- **방법**: In-sample 최적화 → Out-of-sample 검증
- **구현**:
  ```python
  train_period = 1년
  test_period = 3개월
  step = 1개월

  for start in date_range:
      train_data = data[start:start+train_period]
      test_data = data[start+train_period:start+train_period+test_period]

      # Train에서 최적 파라미터 찾기
      best_params = optimize(train_data)

      # Test에서 검증
      result = backtest(test_data, best_params)
  ```

#### 2. 몬테카를로 시뮬레이션
- **목적**: 성과의 확률 분포 파악
- **방법**: 거래 순서를 무작위로 섞어 재시뮬레이션
- **출력**: 수익률 분포, 신뢰구간

#### 3. 상관관계 분석
- **목적**: 포트폴리오 다각화 검증
- **구현**:
  ```python
  # 보유 종목 간 상관계수 계산
  correlation_matrix = calculate_correlation(portfolio_positions)

  # 높은 상관관계 경고
  if correlation > 0.7:
      logger.warning("높은 상관관계 감지")
  ```

### 중기 (1-2개월)

#### 4. 벤치마크 비교
- **벤치마크**: KOSPI 지수, KOSDAQ 지수
- **메트릭**:
  - 초과 수익률 (Alpha)
  - 베타 (시장 민감도)
  - 정보 비율 (Information Ratio)

#### 5. 섹터/산업별 분석
- **데이터**: 업종 정보 추가
- **분석**:
  - 섹터별 수익률 기여도
  - 섹터 로테이션 패턴
  - 섹터 집중도 리스크

#### 6. 신호 품질 분석
- **목적**: 어떤 신호가 수익성이 높은지 분석
- **메트릭**:
  - 신호별 승률
  - 신호 강도 vs 수익률 상관관계
  - Stage별 수익률 차이

### 장기 (3-6개월)

#### 7. 실전 자동매매 연동
- **구현**: 백테스팅 → 페이퍼 트레이딩 → 실전
- **기능**:
  - 실시간 신호 생성
  - 자동 주문 실행
  - 리스크 모니터링
  - Slack 알림

#### 8. 머신러닝 통합
- **모델**: 신호 강도 예측, 손절가 최적화
- **데이터**: 백테스팅 결과를 학습 데이터로 활용

#### 9. 웹 대시보드
- **기술**: Streamlit, Dash
- **기능**:
  - 실시간 백테스팅 실행
  - 인터랙티브 차트
  - 파라미터 조정 UI
  - 리포트 다운로드

---

## 결론

### 성과 요약

Level 6 백테스팅 엔진 개발을 통해 다음을 달성했습니다:

✅ **완전한 백테스팅 프레임워크**
- 전체 시장 스캔 방식 (2,400개 종목)
- Look-ahead bias 완전 방지
- Level 1-5 완전 통합

✅ **실전 수준의 정확성**
- 수수료 0.015%, 슬리피지 0.1%
- 손절 및 트레일링 스톱
- 자본 제약

✅ **종합적인 성과 분석**
- 수익률, 리스크, 거래 통계
- 시각화 및 리포트
- CSV export

✅ **고품질 코드**
- 101개 테스트, 100% 통과
- 상세한 문서화
- 확장 가능한 아키텍처

### 프로젝트 의의

이 백테스팅 엔진은 단순한 시뮬레이터를 넘어:
1. **전략 검증 도구**: 과거 데이터로 전략 유효성 검증
2. **파라미터 최적화**: Grid search, walk-forward 등
3. **실전 준비**: 실전 자동매매의 기반
4. **교육 자료**: 백테스팅 베스트 프랙티스 예시

### 다음 단계

1. **실전 검증**: 페이퍼 트레이딩으로 실시간 성능 확인
2. **파라미터 최적화**: Walk-forward로 최적 설정 탐색
3. **성과 개선**: 신호 품질 분석 및 개선
4. **자동화**: 실전 자동매매 시스템 구축

---

## 참고 자료

### 개발 이력 문서
1. `2025-11-16_backtest_level6_1_portfolio.md` - Portfolio 관리
2. `2025-11-16_backtest_level6_1_execution.md` - Execution 엔진
3. `2025-11-16_backtest_level6_2_data_manager.md` - Data Manager
4. `2025-11-16_backtest_level6_3_engine.md` - Backtest Engine
5. `2025-11-16_backtest_level6_4_analytics.md` - Performance Analytics

### 소스 코드
- `src/backtest/portfolio.py` - Portfolio, Position
- `src/backtest/execution.py` - ExecutionEngine
- `src/backtest/data_manager.py` - DataManager
- `src/backtest/engine.py` - BacktestEngine, BacktestResult
- `src/backtest/analytics.py` - PerformanceAnalyzer

### 테스트 코드
- `src/tests/backtest/test_portfolio.py` (20 tests)
- `src/tests/backtest/test_execution.py` (15 tests)
- `src/tests/backtest/test_data_manager.py` (18 tests)
- `src/tests/backtest/test_backtest_engine.py` (17 tests)
- `src/tests/backtest/test_analytics.py` (31 tests)

### 관련 Level
- **Level 1**: 데이터 수집 (`src/data/collector.py`)
- **Level 2**: 기술적 지표 (`src/analysis/technical/indicators.py`)
- **Level 3**: Stage 분석 (`src/analysis/stage.py`)
- **Level 4**: 신호 생성 (`src/analysis/signal/`)
- **Level 5**: 리스크 관리 (`src/analysis/risk/`)
- **Level 6**: 백테스팅 (`src/backtest/`) ← 현재

---

**문서 버전**: 1.0
**최종 수정**: 2025-11-16
**작성자**: Claude Code
**프로젝트**: Hanlyang Stock MA Trading System
