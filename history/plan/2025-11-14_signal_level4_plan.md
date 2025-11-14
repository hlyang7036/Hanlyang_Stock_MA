# Level 4 매매 신호 생성 모듈 계획

## 날짜
2025-11-14

## 계획 개요
Level 3에서 완성한 스테이지 분석 모듈을 활용하여 실제 매매 신호를 생성하는 시스템을 구현합니다. 
진입 신호, 청산 신호, 신호 강도 평가, 신호 필터링 기능을 체계적으로 구축합니다.

---

## 모듈 구조

```
src/analysis/signal/
├── __init__.py           # 패키지 초기화 및 주요 함수 export
├── entry.py              # 진입 신호 생성
├── exit.py               # 청산 신호 생성
├── strength.py           # 신호 강도 평가
└── filter.py             # 신호 필터링
```

---

## Level 4-1: 진입 신호 생성 (entry.py)

### 구현 함수 (4개)

#### 1. generate_buy_signal()
```python
def generate_buy_signal(
    data: pd.DataFrame,
    signal_type: str = 'normal'  # 'normal' or 'early'
) -> pd.DataFrame:
    """
    매수 진입 신호 생성
    
    Args:
        data: DataFrame (Stage, Dir_MACD_상, Dir_MACD_중, Dir_MACD_하 필요)
        signal_type: 'normal' (통상 매수) 또는 'early' (조기 매수)
    
    Returns:
        pd.DataFrame: 신호 정보
            - Buy_Signal: 매수 신호 (0: 없음, 1: 통상, 2: 조기)
            - Signal_Strength: 신호 강도 (0-100)
            - Entry_Price: 권장 진입가
            - Reason: 신호 발생 이유
    
    Notes:
        통상 매수: 제6스테이지 + 3개 MACD 모두 우상향
        조기 매수: 제5스테이지 + 3개 MACD 모두 우상향 (리스크 높음)
    """
```

**로직**:
1. 현재 스테이지 확인
2. MACD 3종 방향 확인 (모두 'up'인지)
3. 조건 충족 시 신호 생성
4. 신호 강도 계산 (strength.py 활용)

#### 2. generate_sell_signal()
```python
def generate_sell_signal(
    data: pd.DataFrame,
    signal_type: str = 'normal'  # 'normal' or 'early'
) -> pd.DataFrame:
    """
    매도 진입 신호 생성
    
    Args:
        data: DataFrame (Stage, Dir_MACD_상, Dir_MACD_중, Dir_MACD_하 필요)
        signal_type: 'normal' (통상 매도) 또는 'early' (조기 매도)
    
    Returns:
        pd.DataFrame: 신호 정보
            - Sell_Signal: 매도 신호 (0: 없음, 1: 통상, 2: 조기)
            - Signal_Strength: 신호 강도 (0-100)
            - Entry_Price: 권장 진입가
            - Reason: 신호 발생 이유
    
    Notes:
        통상 매도: 제3스테이지 + 3개 MACD 모두 우하향
        조기 매도: 제2스테이지 + 3개 MACD 모두 우하향 (리스크 높음)
    """
```

#### 3. check_entry_conditions()
```python
def check_entry_conditions(
    data: pd.DataFrame,
    position_type: str  # 'buy' or 'sell'
) -> Dict[str, Any]:
    """
    진입 조건 상세 체크
    
    Args:
        data: DataFrame (전체 지표 데이터)
        position_type: 'buy' 또는 'sell'
    
    Returns:
        Dict: 조건 체크 결과
            - stage_ok: 스테이지 조건 충족 여부
            - macd_ok: MACD 조건 충족 여부
            - trend_ok: 추세 조건 충족 여부
            - all_ok: 모든 조건 충족 여부
            - details: 상세 정보
    """
```

#### 4. generate_entry_signals()
```python
def generate_entry_signals(
    data: pd.DataFrame,
    enable_early: bool = False
) -> pd.DataFrame:
    """
    통합 진입 신호 생성 (매수 + 매도)
    
    Args:
        data: DataFrame (전체 지표 데이터)
        enable_early: 조기 진입 신호 활성화 여부
    
    Returns:
        pd.DataFrame: 통합 신호
            - Entry_Signal: 진입 신호 (-2: 조기매도, -1: 통상매도, 
                                        0: 없음, 1: 통상매수, 2: 조기매수)
            - Signal_Strength: 신호 강도
            - Position_Type: 포지션 타입 ('long', 'short', None)
    """
```

---

## Level 4-2: 청산 신호 생성 (exit.py)

### 구현 함수 (4개)

#### 1. generate_exit_signal()
```python
def generate_exit_signal(
    data: pd.DataFrame,
    position_type: str  # 'long' or 'short'
) -> pd.DataFrame:
    """
    청산 신호 생성 (3단계)
    
    Args:
        data: DataFrame (MACD, Histogram, Peakout 정보 필요)
        position_type: 'long' (매수 포지션) 또는 'short' (매도 포지션)
    
    Returns:
        pd.DataFrame: 청산 신호
            - Exit_Level: 청산 레벨 (0: 없음, 1: 경계, 2: 50%, 3: 100%)
            - Exit_Percentage: 청산 비율 (0, 0, 50, 100)
            - Exit_Reason: 청산 이유
            - Should_Exit: 청산 여부 (boolean)
    
    Notes:
        청산 3단계:
        1. 히스토그램 피크아웃 → 경계 태세 (0% 청산)
        2. MACD선 피크아웃 → 50% 청산
        3. MACD-시그널 교차 → 100% 청산
    """
```

**로직**:
1. 히스토그램 피크아웃 감지 (Level 2의 detect_peakout 활용)
2. MACD선 피크아웃 감지
3. MACD-시그널 교차 감지
4. 청산 레벨 및 비율 결정

#### 2. check_histogram_peakout()
```python
def check_histogram_peakout(
    data: pd.DataFrame,
    position_type: str
) -> pd.Series:
    """
    히스토그램 피크아웃 확인 (1단계)
    
    Args:
        data: DataFrame (Histogram 컬럼 필요)
        position_type: 'long' or 'short'
    
    Returns:
        pd.Series: 피크아웃 발생 여부 (boolean)
    
    Notes:
        - 매수 포지션: 히스토그램이 고점 대비 하락
        - 매도 포지션: 히스토그램이 저점 대비 상승
    """
```

#### 3. check_macd_peakout()
```python
def check_macd_peakout(
    data: pd.DataFrame,
    position_type: str
) -> pd.Series:
    """
    MACD선 피크아웃 확인 (2단계)
    
    Args:
        data: DataFrame (MACD 컬럼 필요)
        position_type: 'long' or 'short'
    
    Returns:
        pd.Series: 피크아웃 발생 여부 (boolean)
    """
```

#### 4. check_macd_cross()
```python
def check_macd_cross(
    data: pd.DataFrame,
    position_type: str
) -> pd.Series:
    """
    MACD-시그널 교차 확인 (3단계)
    
    Args:
        data: DataFrame (MACD, Signal 컬럼 필요)
        position_type: 'long' or 'short'
    
    Returns:
        pd.Series: 교차 발생 여부 (boolean)
    
    Notes:
        - 매수 포지션: 데드크로스 발생
        - 매도 포지션: 골든크로스 발생
    """
```

---

## Level 4-3: 신호 강도 평가 (strength.py)

### 구현 함수 (4개)

#### 1. evaluate_signal_strength()
```python
def evaluate_signal_strength(
    data: pd.DataFrame,
    signal_type: str  # 'entry' or 'exit'
) -> pd.Series:
    """
    신호 강도 평가 (0-100 점수)
    
    Args:
        data: DataFrame (전체 지표 데이터)
        signal_type: 'entry' (진입) 또는 'exit' (청산)
    
    Returns:
        pd.Series: 신호 강도 점수 (0-100)
    
    Notes:
        평가 요소:
        - MACD 방향 일치도 (30점)
        - 이동평균선 배열 (20점)
        - 이동평균선 간격 (20점)
        - 이동평균선 기울기 (20점)
        - ATR 변동성 (10점)
    """
```

#### 2. calculate_macd_alignment_score()
```python
def calculate_macd_alignment_score(
    data: pd.DataFrame
) -> pd.Series:
    """
    MACD 방향 일치도 점수 (0-30점)
    
    Returns:
        pd.Series: 점수
            - 3개 모두 일치: 30점
            - 2개 일치: 20점
            - 1개 일치: 10점
            - 모두 불일치: 0점
    """
```

#### 3. calculate_trend_strength_score()
```python
def calculate_trend_strength_score(
    data: pd.DataFrame
) -> pd.Series:
    """
    추세 강도 점수 (0-40점)
    
    평가 항목:
    - 이동평균선 배열 (0-20점)
    - 이동평균선 간격 (0-20점)
    
    Returns:
        pd.Series: 추세 강도 점수
    """
```

#### 4. calculate_momentum_score()
```python
def calculate_momentum_score(
    data: pd.DataFrame
) -> pd.Series:
    """
    모멘텀 점수 (0-30점)
    
    평가 항목:
    - 이동평균선 기울기 (0-20점)
    - ATR 변동성 (0-10점)
    
    Returns:
        pd.Series: 모멘텀 점수
    """
```

---

## Level 4-4: 신호 필터링 (filter.py)

### 구현 함수 (5개)

#### 1. apply_signal_filters()
```python
def apply_signal_filters(
    data: pd.DataFrame,
    min_strength: int = 50,
    enable_filters: Dict[str, bool] = None
) -> pd.DataFrame:
    """
    신호 필터링 적용
    
    Args:
        data: DataFrame (신호 및 지표 데이터)
        min_strength: 최소 신호 강도 (0-100)
        enable_filters: 필터 활성화 설정
            예: {'volatility': True, 'trend': True, 'volume': False}
    
    Returns:
        pd.DataFrame: 필터링된 신호
            - Filtered_Signal: 필터링 후 신호
            - Filter_Passed: 필터 통과 여부
            - Filter_Reasons: 필터링 이유
    """
```

#### 2. check_strength_filter()
```python
def check_strength_filter(
    data: pd.DataFrame,
    min_strength: int = 50
) -> pd.Series:
    """
    신호 강도 필터
    
    Args:
        min_strength: 최소 신호 강도
    
    Returns:
        pd.Series: 필터 통과 여부 (boolean)
    """
```

#### 3. check_volatility_filter()
```python
def check_volatility_filter(
    data: pd.DataFrame,
    max_atr_percentile: float = 90
) -> pd.Series:
    """
    변동성 필터 (과도한 변동성 제외)
    
    Args:
        data: DataFrame (ATR 필요)
        max_atr_percentile: ATR 최대 백분위수
    
    Returns:
        pd.Series: 필터 통과 여부 (boolean)
    
    Notes:
        ATR이 너무 높으면 (상위 10%) 신호 제외
    """
```

#### 4. check_trend_filter()
```python
def check_trend_filter(
    data: pd.DataFrame,
    min_slope: float = 0.1
) -> pd.Series:
    """
    추세 필터 (약한 추세 제외)
    
    Args:
        data: DataFrame (Slope 필요)
        min_slope: 최소 기울기 절댓값
    
    Returns:
        pd.Series: 필터 통과 여부 (boolean)
    
    Notes:
        장기선(EMA_40) 기울기가 너무 작으면 신호 제외
    """
```

#### 5. check_conflicting_signals()
```python
def check_conflicting_signals(
    data: pd.DataFrame
) -> pd.Series:
    """
    상충 신호 체크
    
    Args:
        data: DataFrame (Entry_Signal, Exit_Signal 필요)
    
    Returns:
        pd.Series: 신호 상충 여부 (boolean)
    
    Notes:
        진입 신호와 청산 신호가 동시 발생 시 제외
    """
```

---

## 통합 신호 생성 함수 (__init__.py)

```python
def generate_trading_signals(
    data: pd.DataFrame,
    config: Dict[str, Any] = None
) -> pd.DataFrame:
    """
    통합 매매 신호 생성
    
    전체 프로세스:
    1. 진입 신호 생성 (entry.py)
    2. 청산 신호 생성 (exit.py)
    3. 신호 강도 평가 (strength.py)
    4. 신호 필터링 (filter.py)
    
    Args:
        data: DataFrame (전체 지표 데이터)
        config: 설정
            예: {
                'enable_early_entry': False,
                'min_signal_strength': 50,
                'filters': {
                    'volatility': True,
                    'trend': True
                }
            }
    
    Returns:
        pd.DataFrame: 최종 매매 신호
            - Entry_Signal: 진입 신호
            - Exit_Signal: 청산 신호
            - Signal_Strength: 신호 강도
            - Action: 권장 액션 ('buy', 'sell', 'exit', 'hold')
            - Reason: 신호 발생 이유
    """
```

---

## 데이터 흐름

```
입력 데이터 (Level 2, 3 지표 포함)
    ↓
[Level 4-1] 진입 신호 생성
    ├─ 매수 신호
    └─ 매도 신호
    ↓
[Level 4-2] 청산 신호 생성
    ├─ 히스토그램 피크아웃 (1단계)
    ├─ MACD선 피크아웃 (2단계)
    └─ MACD-시그널 교차 (3단계)
    ↓
[Level 4-3] 신호 강도 평가
    ├─ MACD 일치도 점수
    ├─ 추세 강도 점수
    └─ 모멘텀 점수
    ↓
[Level 4-4] 신호 필터링
    ├─ 강도 필터
    ├─ 변동성 필터
    ├─ 추세 필터
    └─ 상충 신호 체크
    ↓
최종 매매 신호 출력
```

---

## 구현 순서

### Phase 1: 진입 신호 (1주차)
1. `entry.py` 구현 (4개 함수)
2. 테스트 코드 작성 (~15개)
3. 문서화

**예상 시간**: 4-5시간

### Phase 2: 청산 신호 (1주차)
1. `exit.py` 구현 (4개 함수)
2. 테스트 코드 작성 (~12개)
3. 문서화

**예상 시간**: 4시간

### Phase 3: 신호 강도 평가 (1주차)
1. `strength.py` 구현 (4개 함수)
2. 테스트 코드 작성 (~12개)
3. 문서화

**예상 시간**: 3-4시간

### Phase 4: 신호 필터링 (1주차)
1. `filter.py` 구현 (5개 함수)
2. 테스트 코드 작성 (~15개)
3. 문서화

**예상 시간**: 3-4시간

### Phase 5: 통합 및 검증 (1주차)
1. `__init__.py` 통합 함수 구현
2. 전체 통합 테스트
3. 실제 데이터 검증
4. 최종 문서화

**예상 시간**: 4-5시간

**총 예상 시간**: 18-22시간 (약 3주)

---

## 테스트 전략

### 단위 테스트
- 각 함수별 독립 테스트
- 엣지 케이스 커버리지 100%

### 통합 테스트
- 전체 신호 생성 파이프라인 테스트
- 다양한 시장 상황 시뮬레이션

### 성능 테스트
- 대용량 데이터 처리 속도
- 메모리 사용량 체크

---

## 품질 기준

### 코드 품질
- ✅ Type hints 100%
- ✅ Docstrings 100%
- ✅ 테스트 커버리지 > 90%

### 신호 품질
- 💡 승률 목표: > 60%
- 💡 평균 수익률: > 5%
- 💡 최대 손실: < 2 ATR

---

## 주요 의사결정

### 1. 조기 진입 신호 기본값
- **결정**: 기본적으로 비활성화
- **이유**: 리스크 관리 우선
- **옵션**: 사용자가 활성화 가능

### 2. 신호 강도 최소값
- **결정**: 기본값 50점
- **이유**: 품질 > 빈도
- **옵션**: 설정 파일에서 조정 가능

### 3. 필터 적용 전략
- **결정**: 선택적 필터 적용
- **이유**: 유연성 확보
- **옵션**: 개별 필터 on/off

---

## 위험 요소

### 기술적 위험
- ⚠️ 과적합 (overfitting): 백테스팅에서만 좋은 성과
- ⚠️ 지연 신호: 실시간 데이터에서 신호 지연

### 대응 방안
- ✅ 다양한 기간 데이터로 검증
- ✅ 실시간 데이터 스트리밍 최적화
- ✅ 신호 발생 지연 모니터링

---

## 참고 자료

- [이동평균선 투자법 전략](../../Moving_Average_Investment_Strategy_Summary.md)
- [Level 2: 기술적 지표](../2025-11-13_technical_indicators_all.md)
- [Level 3: 스테이지 분석](../2025-11-14_stage_level3_3_calculate_ma_spread_and_check_ma_slope.md)
- [README: 매매 신호](../../README.md#-핵심-전략)

---

## 다음 단계 (Level 5)

Level 4 완료 후:
- **백테스팅 엔진** (`src/backtest/`)
  - 성과 분석
  - 리스크 지표 계산
  - 보고서 생성

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
