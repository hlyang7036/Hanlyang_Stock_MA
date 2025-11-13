# Level 3-3단계 구현 계획 (보조 함수)

## 날짜
2025-11-14

## 계획 개요
Level 3 스테이지 분석 모듈의 마지막 단계로, 3개의 보조 함수를 구현합니다. 이 함수들은 스테이지 판단을 보조하고, 구체적인 매매 전략을 제공하는 역할을 합니다.

---

## 구현할 함수 목록

### 1. calculate_ma_spread() - 이동평균선 간격 계산
### 2. check_ma_slope() - 이동평균선 기울기 확인  
### 3. get_stage_strategy() - 스테이지별 권장 전략 제공

---

# 1. calculate_ma_spread() 함수

## 함수 명세

```python
def calculate_ma_spread(data: pd.DataFrame) -> pd.DataFrame:
    """
    이동평균선 간격 계산
    
    3개 이동평균선(5일, 20일, 40일) 간의 간격을 계산합니다.
    간격의 크기와 방향(양수/음수)으로 추세 강도와 배열 상태를 파악할 수 있습니다.
    
    Args:
        data: DataFrame (EMA_5, EMA_20, EMA_40 컬럼 필요)
    
    Returns:
        pd.DataFrame: 3개 컬럼
            Spread_5_20: 단기-중기 간격 (EMA_5 - EMA_20)
            Spread_20_40: 중기-장기 간격 (EMA_20 - EMA_40)
            Spread_5_40: 단기-장기 간격 (EMA_5 - EMA_40)
    
    Raises:
        TypeError: data가 DataFrame이 아닐 때
        ValueError: 필수 컬럼이 없을 때
    
    Examples:
        >>> df = pd.DataFrame({
        ...     'EMA_5': [110, 115, 120],
        ...     'EMA_20': [105, 108, 112],
        ...     'EMA_40': [100, 102, 105]
        ... })
        >>> spreads = calculate_ma_spread(df)
        >>> print(spreads['Spread_5_20'])
        0    5
        1    7
        2    8
        dtype: float64
    """
```

---

## 알고리즘

```python
def calculate_ma_spread(data: pd.DataFrame) -> pd.DataFrame:
    # 1. 입력 검증
    if not isinstance(data, pd.DataFrame):
        raise TypeError(f"DataFrame이 필요합니다. 입력 타입: {type(data)}")
    
    required_columns = ['EMA_5', 'EMA_20', 'EMA_40']
    missing_columns = [col for col in required_columns if col not in data.columns]
    if missing_columns:
        raise ValueError(f"필수 컬럼이 없습니다: {missing_columns}")
    
    logger.debug(f"이동평균선 간격 계산 시작: {len(data)}개 데이터")
    
    # 2. 간격 계산 (단순 뺄셈)
    spreads = pd.DataFrame(index=data.index)
    
    spreads['Spread_5_20'] = data['EMA_5'] - data['EMA_20']
    spreads['Spread_20_40'] = data['EMA_20'] - data['EMA_40']
    spreads['Spread_5_40'] = data['EMA_5'] - data['EMA_40']
    
    # 3. 통계 로깅
    logger.debug(f"Spread_5_20 평균: {spreads['Spread_5_20'].mean():.2f}")
    logger.debug(f"Spread_20_40 평균: {spreads['Spread_20_40'].mean():.2f}")
    logger.debug(f"Spread_5_40 평균: {spreads['Spread_5_40'].mean():.2f}")
    
    logger.debug("이동평균선 간격 계산 완료")
    
    return spreads
```

**핵심**: 매우 간단한 뺄셈 연산

---

## 간격의 의미

| 간격 | 의미 | 양수일 때 | 음수일 때 |
|------|------|----------|----------|
| **Spread_5_20** | 단기-중기 관계 | 단기선이 위 (상승 신호) | 단기선이 아래 (하락 신호) |
| **Spread_20_40** | 중기-장기 관계 | 중기선이 위 (중기 상승) | 중기선이 아래 (중기 하락) |
| **Spread_5_40** | 단기-장기 관계 | 단기선이 위 (강한 상승) | 단기선이 아래 (강한 하락) |

---

## 스테이지별 간격 패턴

| 스테이지 | Spread_5_20 | Spread_20_40 | Spread_5_40 | 특징 |
|---------|-------------|--------------|-------------|------|
| **1** | + (큼) | + (큼) | + (매우 큼) | 모든 간격 확대 |
| **2** | - (작음) | + | + | 5-20 역전 |
| **3** | - | - (작음) | - (작음) | 간격 축소 시작 |
| **4** | - (큼) | - (큼) | - (매우 큼) | 모든 간격 확대 (역방향) |
| **5** | + (작음) | - | - | 5-20 역전 |
| **6** | + | + (작음) | + (작음) | 간격 확대 시작 |

---

## 활용 방법

### 제2스테이지: 매수 포지션 유지 판단

```python
# 중기-장기 간격이 줄어들지 않으면 유지
if stage == 2:
    spread_20_40_current = spreads['Spread_20_40'].iloc[-1]
    spread_20_40_prev = spreads['Spread_20_40'].iloc[-2]
    
    if spread_20_40_current >= spread_20_40_prev:
        action = "매수 포지션 유지"
        reason = "중기-장기 간격 유지 또는 확대"
    else:
        action = "포지션 축소 검토"
        reason = "중기-장기 간격 축소 중"
    
    print(f"제2스테이지 판단:")
    print(f"  액션: {action}")
    print(f"  이유: {reason}")
    print(f"  현재 간격: {spread_20_40_current:.2f}")
    print(f"  이전 간격: {spread_20_40_prev:.2f}")
```

### 제5스테이지: 매도 포지션 유지 판단

```python
# 중기-장기 간격이 줄어들지 않으면 유지 (음수이므로 절댓값 비교)
if stage == 5:
    spread_20_40_current = spreads['Spread_20_40'].iloc[-1]
    spread_20_40_prev = spreads['Spread_20_40'].iloc[-2]
    
    if abs(spread_20_40_current) >= abs(spread_20_40_prev):
        action = "매도 포지션 유지"
        reason = "중기-장기 간격 유지 또는 확대"
    else:
        action = "포지션 축소 검토"
        reason = "중기-장기 간격 축소 중"
```

### 간격 확대/축소 추적

```python
# 간격 변화 추적
spreads['Spread_5_20_Change'] = spreads['Spread_5_20'].diff()

# 간격 확대 중
expanding = spreads[spreads['Spread_5_20_Change'] > 0]
print(f"간격 확대 발생: {len(expanding)}회")

# 간격 축소 중
contracting = spreads[spreads['Spread_5_20_Change'] < 0]
print(f"간격 축소 발생: {len(contracting)}회")
```

---

## 테스트 시나리오 (5개)

### 1. 기본 간격 계산

```python
def test_spread_calculation(self):
    """간격 계산 정확성"""
    df = pd.DataFrame({
        'EMA_5': [110, 115, 120],
        'EMA_20': [105, 108, 112],
        'EMA_40': [100, 102, 105]
    })
    
    spreads = calculate_ma_spread(df)
    
    # Spread_5_20 확인
    assert spreads['Spread_5_20'].iloc[0] == 5   # 110 - 105
    assert spreads['Spread_5_20'].iloc[1] == 7   # 115 - 108
    assert spreads['Spread_5_20'].iloc[2] == 8   # 120 - 112
    
    # Spread_20_40 확인
    assert spreads['Spread_20_40'].iloc[0] == 5  # 105 - 100
    
    # Spread_5_40 확인
    assert spreads['Spread_5_40'].iloc[0] == 10  # 110 - 100
    
    # 3개 컬럼 존재
    assert len(spreads.columns) == 3
```

### 2. 양수/음수 케이스

```python
def test_spread_positive_negative(self):
    """양수(정배열)/음수(역배열) 간격"""
    df = pd.DataFrame({
        'EMA_5': [110, 95],   # 정배열 → 역배열
        'EMA_20': [105, 100],
        'EMA_40': [100, 105]
    })
    
    spreads = calculate_ma_spread(df)
    
    # 첫 행: 정배열 (양수)
    assert spreads['Spread_5_20'].iloc[0] > 0
    assert spreads['Spread_20_40'].iloc[0] > 0
    assert spreads['Spread_5_40'].iloc[0] > 0
    
    # 둘째 행: 역배열 (음수)
    assert spreads['Spread_5_20'].iloc[1] < 0
    assert spreads['Spread_20_40'].iloc[1] < 0
    assert spreads['Spread_5_40'].iloc[1] < 0
```

### 3. 간격 변화 추적

```python
def test_spread_change_tracking(self):
    """간격 확대/축소 추적"""
    df = pd.DataFrame({
        'EMA_5': [110, 112, 115],   # 간격 확대
        'EMA_20': [105, 106, 107],
        'EMA_40': [100, 101, 102]
    })
    
    spreads = calculate_ma_spread(df)
    
    # Spread_5_20 확대 확인
    assert spreads['Spread_5_20'].iloc[0] == 5
    assert spreads['Spread_5_20'].iloc[1] == 6
    assert spreads['Spread_5_20'].iloc[2] == 8
    
    # 간격이 계속 확대됨
    assert spreads['Spread_5_20'].is_monotonic_increasing
```

### 4. NaN 처리

```python
def test_spread_with_nan(self):
    """NaN 포함 시 전파"""
    df = pd.DataFrame({
        'EMA_5': [110, np.nan, 120],
        'EMA_20': [105, 108, 112],
        'EMA_40': [100, 102, 105]
    })
    
    spreads = calculate_ma_spread(df)
    
    # NaN은 전파됨
    assert not pd.isna(spreads['Spread_5_20'].iloc[0])
    assert pd.isna(spreads['Spread_5_20'].iloc[1])
    assert not pd.isna(spreads['Spread_5_20'].iloc[2])
```

### 5. 에러 케이스

```python
def test_spread_missing_columns(self):
    """필수 컬럼 누락"""
    df = pd.DataFrame({
        'EMA_5': [110, 115],
        'EMA_20': [105, 108]
        # EMA_40 누락
    })
    
    with pytest.raises(ValueError, match="필수 컬럼이 없습니다"):
        calculate_ma_spread(df)

def test_spread_invalid_type(self):
    """잘못된 타입"""
    with pytest.raises(TypeError, match="DataFrame이 필요합니다"):
        calculate_ma_spread([1, 2, 3])
```

---

## 예상 구현 시간
- **난이도**: ⭐ (매우 쉬움)
- **구현**: 20분
- **테스트**: 10분
- **총**: 30분

---

# 2. check_ma_slope() 함수

## 함수 명세

```python
def check_ma_slope(data: pd.DataFrame, period: int = 5) -> pd.DataFrame:
    """
    이동평균선 기울기 확인
    
    3개 이동평균선(5일, 20일, 40일)의 기울기를 계산합니다.
    기울기를 통해 각 이동평균선의 방향성(우상향/평행/우하향)을 판단할 수 있습니다.
    
    Args:
        data: DataFrame (EMA_5, EMA_20, EMA_40 컬럼 필요)
        period: 기울기 계산 기간 (기본값: 5)
    
    Returns:
        pd.DataFrame: 3개 컬럼
            Slope_EMA_5: 단기선 기울기
            Slope_EMA_20: 중기선 기울기
            Slope_EMA_40: 장기선 기울기
    
    Raises:
        TypeError: data가 DataFrame이 아닐 때
        ValueError: 필수 컬럼 없거나 period가 2 미만일 때
    
    Notes:
        - Level 2의 calculate_slope() 함수를 재사용합니다
        - 기울기 > 0: 우상향 (상승 추세)
        - 기울기 ≈ 0: 평행 (추세 전환 임박)
        - 기울기 < 0: 우하향 (하락 추세)
    
    Examples:
        >>> df = pd.DataFrame({
        ...     'EMA_5': [100, 102, 105, 109, 114],
        ...     'EMA_20': [95, 97, 99, 102, 105],
        ...     'EMA_40': [90, 91, 93, 95, 97]
        ... })
        >>> slopes = check_ma_slope(df, period=3)
        >>> print(slopes['Slope_EMA_5'].iloc[-1] > 0)
        True
    """
```

---

## 알고리즘 (Level 2 함수 재사용)

```python
from src.analysis.technical.indicators import calculate_slope

def check_ma_slope(data: pd.DataFrame, period: int = 5) -> pd.DataFrame:
    # 1. 입력 검증
    if not isinstance(data, pd.DataFrame):
        raise TypeError(f"DataFrame이 필요합니다. 입력 타입: {type(data)}")
    
    required_columns = ['EMA_5', 'EMA_20', 'EMA_40']
    missing_columns = [col for col in required_columns if col not in data.columns]
    if missing_columns:
        raise ValueError(f"필수 컬럼이 없습니다: {missing_columns}")
    
    if period < 2:
        raise ValueError(f"period는 2 이상이어야 합니다. 입력값: {period}")
    
    logger.debug(f"이동평균선 기울기 계산 시작: {len(data)}개, period={period}")
    
    # 2. 각 이동평균선의 기울기 계산
    slopes = pd.DataFrame(index=data.index)
    
    # Level 2에서 구현한 calculate_slope 재사용
    slopes['Slope_EMA_5'] = calculate_slope(data['EMA_5'], period=period)
    slopes['Slope_EMA_20'] = calculate_slope(data['EMA_20'], period=period)
    slopes['Slope_EMA_40'] = calculate_slope(data['EMA_40'], period=period)
    
    # 3. 기울기 통계
    for col in ['Slope_EMA_5', 'Slope_EMA_20', 'Slope_EMA_40']:
        slope_mean = slopes[col].mean()
        slope_std = slopes[col].std()
        logger.debug(f"{col}: 평균={slope_mean:.4f}, 표준편차={slope_std:.4f}")
    
    logger.debug("이동평균선 기울기 계산 완료")
    
    return slopes
```

**핵심**: Level 2의 `calculate_slope()` 함수를 그대로 재사용!

---

## 기울기의 의미

| 기울기 값 | 의미 | 판단 기준 |
|----------|------|----------|
| **> 0** | 우상향 | 상승 추세 |
| **≈ 0** | 평행 | 추세 전환 임박 (±0.1 이내) |
| **< 0** | 우하향 | 하락 추세 |

---

## 스테이지별 기울기 패턴

| 스테이지 | EMA_5 | EMA_20 | EMA_40 | 특징 |
|---------|-------|--------|--------|------|
| **1** | ++ | ++ | ++ | 3개선 모두 급상승 |
| **2** | 0/- | + | + | 단기선 꺾임, 장기선 상승 |
| **3** | -- | 0/- | + | 단/중기 하락, 장기 상승 |
| **4** | -- | -- | -- | 3개선 모두 급하락 |
| **5** | 0/+ | - | - | 단기선 반등, 장기선 하락 |
| **6** | ++ | 0/+ | - | 단/중기 상승, 장기 하락 |

---

## 활용 방법

### 제2스테이지: 매수 포지션 유지 판단

```python
if stage == 2:
    slope_40 = slopes['Slope_EMA_40'].iloc[-1]
    
    if slope_40 > 0:
        action = "매수 포지션 유지"
        reason = "장기선이 여전히 상승 중"
        print(f"  장기선 기울기: {slope_40:.4f} (양수)")
    else:
        action = "포지션 청산 검토"
        reason = "장기선이 하락 전환"
        print(f"  장기선 기울기: {slope_40:.4f} (음수)")
```

### 제5스테이지: 매도 포지션 유지 판단

```python
if stage == 5:
    slope_40 = slopes['Slope_EMA_40'].iloc[-1]
    
    if slope_40 < 0:
        action = "매도 포지션 유지"
        reason = "장기선이 여전히 하락 중"
    else:
        action = "포지션 청산 검토"
        reason = "장기선이 상승 전환"
```

### 제6스테이지: 조기 매수 진입 판단

```python
if stage == 6:
    slope_5 = slopes['Slope_EMA_5'].iloc[-1]
    slope_20 = slopes['Slope_EMA_20'].iloc[-1]
    slope_40 = slopes['Slope_EMA_40'].iloc[-1]
    
    # 조기 매수 조건: 단기·중기 우상향, 장기 평행
    if slope_5 > 0 and slope_20 > 0 and abs(slope_40) < 0.1:
        action = "조기 매수 진입"
        signal_strength = "강함"
        print(f"✅ 조기 매수 신호")
        print(f"  단기선 기울기: {slope_5:.4f}")
        print(f"  중기선 기울기: {slope_20:.4f}")
        print(f"  장기선 기울기: {slope_40:.4f} (평행)")
    else:
        action = "통상 매수 대기"
        signal_strength = "약함"
```

### 3개선 방향 일치도 확인

```python
# 3개선 모두 우상향
all_uptrend = (slopes['Slope_EMA_5'] > 0) & \
              (slopes['Slope_EMA_20'] > 0) & \
              (slopes['Slope_EMA_40'] > 0)

# 3개선 모두 우하향
all_downtrend = (slopes['Slope_EMA_5'] < 0) & \
                (slopes['Slope_EMA_20'] < 0) & \
                (slopes['Slope_EMA_40'] < 0)

print(f"강한 상승 추세: {all_uptrend.sum()}일")
print(f"강한 하락 추세: {all_downtrend.sum()}일")
```

---

## 테스트 시나리오 (5개)

### 1. 우상향 판단

```python
def test_slope_uptrend(self):
    """우상향 기울기 판단"""
    df = pd.DataFrame({
        'EMA_5': [100, 102, 105, 109, 114],   # 증가
        'EMA_20': [95, 97, 99, 102, 105],
        'EMA_40': [90, 91, 93, 95, 97]
    })
    
    slopes = check_ma_slope(df, period=3)
    
    # 모든 기울기가 양수
    assert slopes['Slope_EMA_5'].iloc[-1] > 0
    assert slopes['Slope_EMA_20'].iloc[-1] > 0
    assert slopes['Slope_EMA_40'].iloc[-1] > 0
    
    # 3개 컬럼 존재
    assert len(slopes.columns) == 3
```

### 2. 우하향 판단

```python
def test_slope_downtrend(self):
    """우하향 기울기 판단"""
    df = pd.DataFrame({
        'EMA_5': [114, 109, 105, 102, 100],   # 감소
        'EMA_20': [105, 102, 99, 97, 95],
        'EMA_40': [97, 95, 93, 91, 90]
    })
    
    slopes = check_ma_slope(df, period=3)
    
    # 모든 기울기가 음수
    assert slopes['Slope_EMA_5'].iloc[-1] < 0
    assert slopes['Slope_EMA_20'].iloc[-1] < 0
    assert slopes['Slope_EMA_40'].iloc[-1] < 0
```

### 3. 평행(횡보) 판단

```python
def test_slope_flat(self):
    """평행 기울기 판단"""
    df = pd.DataFrame({
        'EMA_5': [100, 100.1, 99.9, 100.2, 100],   # 거의 변화 없음
        'EMA_20': [95, 95.1, 94.9, 95.1, 95],
        'EMA_40': [90, 90.05, 89.95, 90.1, 90]
    })
    
    slopes = check_ma_slope(df, period=3)
    
    # 기울기가 0에 가까움
    assert abs(slopes['Slope_EMA_5'].iloc[-1]) < 0.1
    assert abs(slopes['Slope_EMA_20'].iloc[-1]) < 0.1
    assert abs(slopes['Slope_EMA_40'].iloc[-1]) < 0.1
```

### 4. 커스텀 period

```python
def test_slope_custom_period(self):
    """커스텀 period 테스트"""
    df = pd.DataFrame({
        'EMA_5': range(100, 110),    # 10개 데이터
        'EMA_20': range(95, 105),
        'EMA_40': range(90, 100)
    })
    
    # period=3과 period=5 비교
    slopes_3 = check_ma_slope(df, period=3)
    slopes_5 = check_ma_slope(df, period=5)
    
    # 둘 다 양수이지만 값은 다름
    assert slopes_3['Slope_EMA_5'].iloc[-1] > 0
    assert slopes_5['Slope_EMA_5'].iloc[-1] > 0
    assert slopes_3['Slope_EMA_5'].iloc[-1] != slopes_5['Slope_EMA_5'].iloc[-1]
```

### 5. 에러 케이스

```python
def test_slope_invalid_period(self):
    """잘못된 period"""
    df = pd.DataFrame({
        'EMA_5': [100, 102],
        'EMA_20': [95, 97],
        'EMA_40': [90, 91]
    })
    
    with pytest.raises(ValueError, match="period는 2 이상"):
        check_ma_slope(df, period=1)

def test_slope_missing_columns(self):
    """필수 컬럼 누락"""
    df = pd.DataFrame({
        'EMA_5': [100, 102],
        'EMA_20': [95, 97]
        # EMA_40 누락
    })
    
    with pytest.raises(ValueError, match="필수 컬럼이 없습니다"):
        check_ma_slope(df, period=3)
```

---

## 예상 구현 시간
- **난이도**: ⭐ (쉬움, Level 2 재사용)
- **구현**: 20분
- **테스트**: 10분
- **총**: 30분

---

# 3. get_stage_strategy() 함수

## 함수 명세

```python
def get_stage_strategy(
    stage: int, 
    macd_directions: Optional[Dict[str, str]] = None
) -> Dict[str, Any]:
    """
    스테이지별 권장 전략 제공
    
    각 스테이지에 맞는 구체적인 매매 전략과 액션을 제공합니다.
    MACD 방향 정보를 추가로 제공하면 신호 강도를 함께 분석합니다.
    
    Args:
        stage: 현재 스테이지 (1~6)
        macd_directions: 3개 MACD 방향 (선택)
            예: {'상': 'up', '중': 'up', '하': 'up'}
    
    Returns:
        Dict: 전략 정보
            - stage: 스테이지 번호 (int)
            - name: 스테이지 이름 (str)
            - market_phase: 시장 국면 (str)
            - strategy: 권장 전략 (str)
            - action: 구체적 액션 (str)
            - position_size: 포지션 크기 (str)
            - risk_level: 리스크 레벨 (str)
            - description: 상세 설명 (str)
            - key_points: 핵심 포인트 리스트 (List[str])
            - macd_directions: MACD 방향 정보 (Dict, 선택)
            - macd_alignment: MACD 일치도 (Dict, 선택)
    
    Raises:
        TypeError: stage가 정수가 아닐 때
        ValueError: stage가 1~6 범위 밖일 때
    
    Examples:
        >>> strategy = get_stage_strategy(1)
        >>> print(strategy['name'])
        안정 상승기
        >>> print(strategy['action'])
        buy
        
        >>> # MACD 방향 포함
        >>> macd_dirs = {'상': 'up', '중': 'up', '하': 'up'}
        >>> strategy = get_stage_strategy(1, macd_directions=macd_dirs)
        >>> print(strategy['macd_alignment']['strength'])
        strong
    """
```

---

## 알고리즘 (딕셔너리 매핑)

```python
def get_stage_strategy(
    stage: int,
    macd_directions: Optional[Dict[str, str]] = None
) -> Dict[str, Any]:
    
    # 1. 입력 검증
    if not isinstance(stage, (int, np.integer)):
        raise TypeError(f"stage는 정수여야 합니다. 입력 타입: {type(stage)}")
    
    if stage < 1 or stage > 6:
        raise ValueError(f"stage는 1~6 사이여야 합니다. 입력값: {stage}")
    
    logger.debug(f"스테이지 {stage} 전략 조회")
    
    # 2. 스테이지별 전략 매핑 (딕셔너리)
    strategies = {
        1: {
            'stage': 1,
            'name': '안정 상승기',
            'market_phase': '강세장',
            'strategy': '공격적 매수',
            'action': 'buy',
            'position_size': '적극적 (80-100%)',
            'risk_level': 'low',
            'description': '완전 정배열, 강한 상승 추세. 매수 포지션 확대 최적기',
            'key_points': [
                '3개 이동평균선 모두 우상향',
                '이동평균선 간격 확대 중',
                '매수 포지션 확대 적기',
                'MACD(하) 골든크로스로 상승 확정',
                '추세 지속 기대'
            ]
        },
        2: {
            'stage': 2,
            'name': '하락 변화기1',
            'market_phase': '약세 전환 초기',
            'strategy': '포지션 유지 판단',
            'action': 'hold_or_exit',
            'position_size': '유지 또는 축소 (50-80%)',
            'risk_level': 'medium',
            'description': 'MACD(상) 데드크로스 발생. 단기선이 중기선 아래로 하락',
            'key_points': [
                '단기선이 중기선 아래로 하락',
                'MACD(상) 데드크로스 (주의 신호)',
                '중기-장기 간격 확인 필요',
                '장기선이 여전히 상승 중이면 유지',
                '장기선이 꺾이면 청산 검토'
            ]
        },
        3: {
            'stage': 3,
            'name': '하락 변화기2',
            'market_phase': '약세 가속',
            'strategy': '매수 청산, 매도 진입',
            'action': 'sell_or_short',
            'position_size': '전량 청산 또는 매도 진입',
            'risk_level': 'high',
            'description': 'MACD(중) 데드크로스. 단기선이 장기선 아래로 하락',
            'key_points': [
                '단기선이 장기선 아래로 하락',
                'MACD(중) 데드크로스 (강한 하락 신호)',
                '매수 포지션 전량 청산',
                '공격적 투자자는 매도 진입 고려',
                '하락 추세 시작'
            ]
        },
        4: {
            'stage': 4,
            'name': '안정 하락기',
            'market_phase': '약세장',
            'strategy': '공격적 매도 (또는 관망)',
            'action': 'short_or_wait',
            'position_size': '적극적 매도 (또는 현금 보유)',
            'risk_level': 'low',
            'description': '완전 역배열, 강한 하락 추세. 매도 포지션 확대 적기',
            'key_points': [
                '3개 이동평균선 모두 우하향',
                '이동평균선 간격 확대 중 (역방향)',
                '매도 포지션 확대 적기 (공격적 투자자)',
                'MACD(하) 데드크로스로 하락 확정',
                '보수적 투자자는 현금 보유 관망'
            ]
        },
        5: {
            'stage': 5,
            'name': '상승 변화기1',
            'market_phase': '강세 전환 초기',
            'strategy': '포지션 유지 판단',
            'action': 'hold_or_exit',
            'position_size': '유지 또는 축소 (50-80%)',
            'risk_level': 'medium',
            'description': 'MACD(상) 골든크로스 발생. 단기선이 중기선 위로 상승',
            'key_points': [
                '단기선이 중기선 위로 상승',
                'MACD(상) 골든크로스 (긍정 신호)',
                '중기-장기 간격 확인 필요',
                '장기선이 여전히 하락 중이면 유지',
                '장기선이 반등하면 청산 검토'
            ]
        },
        6: {
            'stage': 6,
            'name': '상승 변화기2',
            'market_phase': '강세 가속',
            'strategy': '매도 청산, 매수 진입',
            'action': 'cover_or_buy',
            'position_size': '전량 청산 또는 매수 진입',
            'risk_level': 'high',
            'description': 'MACD(중) 골든크로스. 단기선이 장기선 위로 상승',
            'key_points': [
                '단기선이 장기선 위로 상승',
                'MACD(중) 골든크로스 (강한 상승 신호)',
                '매도 포지션 전량 청산',
                '조기 매수 진입 고려',
                '상승 추세 시작 임박'
            ]
        }
    }
    
    # 3. 해당 스테이지 전략 가져오기
    strategy = strategies[stage].copy()
    
    # 4. MACD 방향 정보 추가 (선택)
    if macd_directions is not None:
        strategy['macd_directions'] = macd_directions
        
        # MACD 방향 일치도 계산
        up_count = sum(1 for d in macd_directions.values() if d == 'up')
        down_count = sum(1 for d in macd_directions.values() if d == 'down')
        neutral_count = sum(1 for d in macd_directions.values() if d == 'neutral')
        
        strategy['macd_alignment'] = {
            'up_count': up_count,
            'down_count': down_count,
            'neutral_count': neutral_count,
            'strength': 'strong' if (up_count == 3 or down_count == 3) else 'weak'
        }
        
        logger.debug(f"MACD 방향: 상승={up_count}, 하락={down_count}, 중립={neutral_count}")
    
    logger.debug(f"전략 조회 완료: {strategy['name']}")
    
    return strategy
```

---

## 스테이지별 전략 요약

| 스테이지 | 이름 | 전략 | 액션 | 포지션 | 리스크 |
|---------|------|------|------|--------|--------|
| **1** | 안정 상승기 | 공격적 매수 | buy | 80-100% | low |
| **2** | 하락 변화기1 | 유지 판단 | hold/exit | 50-80% | medium |
| **3** | 하락 변화기2 | 청산/매도 | sell/short | 전량 청산 | high |
| **4** | 안정 하락기 | 매도/관망 | short/wait | 매도 또는 현금 | low |
| **5** | 상승 변화기1 | 유지 판단 | hold/exit | 50-80% | medium |
| **6** | 상승 변화기2 | 청산/매수 | cover/buy | 전량 청산 | high |

---

## 활용 방법

### 기본 사용

```python
# 현재 스테이지 전략 조회
current_stage = df['Stage'].iloc[-1]
strategy = get_stage_strategy(current_stage)

print(f"=" * 50)
print(f"현재: 제{strategy['stage']}스테이지 - {strategy['name']}")
print(f"=" * 50)
print(f"시장 국면: {strategy['market_phase']}")
print(f"권장 전략: {strategy['strategy']}")
print(f"액션: {strategy['action']}")
print(f"포지션 크기: {strategy['position_size']}")
print(f"리스크: {strategy['risk_level']}")
print(f"\n설명: {strategy['description']}")
print(f"\n핵심 포인트:")
for i, point in enumerate(strategy['key_points'], 1):
    print(f"  {i}. {point}")
```

### MACD 방향 포함

```python
# MACD 방향 정보 포함
macd_dirs = {
    '상': df['Dir_MACD_상'].iloc[-1],
    '중': df['Dir_MACD_중'].iloc[-1],
    '하': df['Dir_MACD_하'].iloc[-1]
}

strategy = get_stage_strategy(current_stage, macd_directions=macd_dirs)

# MACD 일치도 확인
if 'macd_alignment' in strategy:
    alignment = strategy['macd_alignment']
    print(f"\n" + "=" * 50)
    print(f"MACD 방향 일치도:")
    print(f"=" * 50)
    print(f"  상승: {alignment['up_count']}개")
    print(f"  하락: {alignment['down_count']}개")
    print(f"  중립: {alignment['neutral_count']}개")
    print(f"  강도: {alignment['strength']}")
    
    if alignment['strength'] == 'strong':
        print(f"\n✅ 강한 신호 - 추세 확실")
    else:
        print(f"\n⚠️ 약한 신호 - 신중한 접근 필요")
```

### 알림 시스템

```python
# 스테이지 전환 시 알림
transition = df['Transition'].iloc[-1]

if transition != 0:
    current_stage = df['Stage'].iloc[-1]
    strategy = get_stage_strategy(current_stage)
    
    # 알림 발송
    send_notification(
        title=f"🔔 스테이지 전환: {strategy['name']}",
        message=f"{strategy['strategy']}\n\n액션: {strategy['action']}\n포지션: {strategy['position_size']}",
        priority="high" if strategy['risk_level'] == 'high' else "normal",
        color="red" if strategy['risk_level'] == 'high' else "blue"
    )
```

### 백테스팅 결과 해석

```python
# 전체 기간의 스테이지별 통계
stage_stats = []

for stage_num in range(1, 7):
    stage_days = df[df['Stage'] == stage_num]
    strategy = get_stage_strategy(stage_num)
    
    stage_stats.append({
        'stage': stage_num,
        'name': strategy['name'],
        'days': len(stage_days),
        'percentage': len(stage_days) / len(df) * 100,
        'action': strategy['action'],
        'risk': strategy['risk_level']
    })

stats_df = pd.DataFrame(stage_stats)
print("\n스테이지별 통계:")
print(stats_df.to_string(index=False))

# 고위험 기간 확인
high_risk_days = df[df['Stage'].isin([3, 6])]
print(f"\n고위험 기간(스테이지 3, 6): {len(high_risk_days)}일 ({len(high_risk_days)/len(df)*100:.1f}%)")
```

---

## 테스트 시나리오 (8개)

### 1-6. 제1~6스테이지 전략 조회

```python
def test_strategy_stage_1(self):
    """제1스테이지 전략"""
    strategy = get_stage_strategy(1)
    
    assert strategy['stage'] == 1
    assert strategy['name'] == '안정 상승기'
    assert strategy['market_phase'] == '강세장'
    assert strategy['action'] == 'buy'
    assert strategy['risk_level'] == 'low'
    assert len(strategy['key_points']) == 5
    assert 'description' in strategy

def test_strategy_stage_2(self):
    """제2스테이지 전략"""
    strategy = get_stage_strategy(2)
    
    assert strategy['stage'] == 2
    assert strategy['name'] == '하락 변화기1'
    assert strategy['action'] == 'hold_or_exit'
    assert strategy['risk_level'] == 'medium'

def test_strategy_stage_3(self):
    """제3스테이지 전략"""
    strategy = get_stage_strategy(3)
    
    assert strategy['stage'] == 3
    assert strategy['name'] == '하락 변화기2'
    assert strategy['action'] == 'sell_or_short'
    assert strategy['risk_level'] == 'high'

def test_strategy_stage_4(self):
    """제4스테이지 전략"""
    strategy = get_stage_strategy(4)
    
    assert strategy['stage'] == 4
    assert strategy['name'] == '안정 하락기'
    assert strategy['action'] == 'short_or_wait'
    assert strategy['risk_level'] == 'low'

def test_strategy_stage_5(self):
    """제5스테이지 전략"""
    strategy = get_stage_strategy(5)
    
    assert strategy['stage'] == 5
    assert strategy['name'] == '상승 변화기1'
    assert strategy['action'] == 'hold_or_exit'
    assert strategy['risk_level'] == 'medium'

def test_strategy_stage_6(self):
    """제6스테이지 전략"""
    strategy = get_stage_strategy(6)
    
    assert strategy['stage'] == 6
    assert strategy['name'] == '상승 변화기2'
    assert strategy['action'] == 'cover_or_buy'
    assert strategy['risk_level'] == 'high'
```

### 7. MACD 방향 포함

```python
def test_strategy_with_macd_directions(self):
    """MACD 방향 정보 포함"""
    macd_dirs = {'상': 'up', '중': 'up', '하': 'up'}
    
    strategy = get_stage_strategy(1, macd_directions=macd_dirs)
    
    # MACD 방향 정보 확인
    assert 'macd_directions' in strategy
    assert strategy['macd_directions'] == macd_dirs
    
    # MACD 일치도 확인
    assert 'macd_alignment' in strategy
    assert strategy['macd_alignment']['up_count'] == 3
    assert strategy['macd_alignment']['down_count'] == 0
    assert strategy['macd_alignment']['neutral_count'] == 0
    assert strategy['macd_alignment']['strength'] == 'strong'

def test_strategy_with_weak_macd(self):
    """약한 MACD 신호"""
    macd_dirs = {'상': 'up', '중': 'down', '하': 'neutral'}
    
    strategy = get_stage_strategy(1, macd_directions=macd_dirs)
    
    assert strategy['macd_alignment']['up_count'] == 1
    assert strategy['macd_alignment']['down_count'] == 1
    assert strategy['macd_alignment']['neutral_count'] == 1
    assert strategy['macd_alignment']['strength'] == 'weak'
```

### 8. 에러 케이스

```python
def test_strategy_invalid_stage(self):
    """잘못된 스테이지 번호"""
    # 0
    with pytest.raises(ValueError, match="stage는 1~6"):
        get_stage_strategy(0)
    
    # 7
    with pytest.raises(ValueError, match="stage는 1~6"):
        get_stage_strategy(7)
    
    # -1
    with pytest.raises(ValueError, match="stage는 1~6"):
        get_stage_strategy(-1)

def test_strategy_invalid_type(self):
    """잘못된 타입"""
    with pytest.raises(TypeError, match="stage는 정수여야 합니다"):
        get_stage_strategy("1")
    
    with pytest.raises(TypeError, match="stage는 정수여야 합니다"):
        get_stage_strategy(1.5)
```

---

## 예상 구현 시간
- **난이도**: ⭐⭐ (중간, 딕셔너리 작성)
- **구현**: 40분
- **테스트**: 20분
- **총**: 1시간

---

# 종합 요약

## 구현 예정 함수

| 함수 | 목적 | 난이도 | 시간 | 테스트 |
|------|------|-------|------|--------|
| **calculate_ma_spread** | 이동평균선 간격 계산 | ⭐ | 30분 | 5개 |
| **check_ma_slope** | 이동평균선 기울기 확인 | ⭐ | 30분 | 5개 |
| **get_stage_strategy** | 스테이지별 전략 제공 | ⭐⭐ | 1시간 | 8개 |
| **총계** | - | - | **2시간** | **18개** |

---

## 함수 간 관계

```
determine_stage()  ─────┐
                        ├──> 스테이지 판단
detect_stage_transition()┘
         │
         ├──> stage 번호
         ↓
get_stage_strategy() ───> 전략 정보 제공
         │
         ├──> 의사결정 보조
         │
         ↓
calculate_ma_spread() ──┐
                        ├──> 세부 판단
check_ma_slope() ───────┘
```

---

## 핵심 특징

### calculate_ma_spread
- **가장 단순**: 뺄셈 연산만
- **직관적**: 간격의 의미 명확
- **활용도**: 제2/5스테이지 판단

### check_ma_slope
- **재사용**: Level 2 함수 활용
- **방향성**: 우상향/평행/우하향
- **활용도**: 제2/5/6스테이지 판단

### get_stage_strategy
- **딕셔너리**: 스테이지별 전략 매핑
- **확장 가능**: MACD 방향 추가
- **활용도**: UI/알림/백테스팅

---

## 테스트 전략

### 공통 테스트
- 정상 케이스 (각 스테이지/패턴)
- 엣지 케이스 (NaN, 극값)
- 에러 케이스 (타입, 범위, 누락)

### 특화 테스트
- **spread**: 양수/음수, 확대/축소
- **slope**: 우상향/평행/우하향
- **strategy**: MACD 방향, 일치도

---

## 성공 기준

### 필수 조건
- ✅ 3개 함수 모두 구현
- ✅ 18개 테스트 모두 통과
- ✅ 타입 힌팅 완비
- ✅ Docstring 완비
- ✅ 에러 처리 철저

### 품질 기준
- ✅ 코드 가독성 높음
- ✅ 로깅 적절
- ✅ 재사용성 고려
- ✅ 문서화 완료

---

## Level 3 완료 후

### 완성되는 것
- ✅ 스테이지 분석 모듈 전체 (7개 함수)
- ✅ 6단계 대순환 분석 시스템
- ✅ 매매 전략 가이드

### 다음 단계 (Level 4)
- **매매 신호 생성 모듈** (`src/analysis/signal/`)
  - 진입 신호 생성
  - 청산 신호 생성
  - 신호 강도 평가
  - 신호 필터링

---

## 참고 자료

- [이동평균선 투자법 전략 정리](../../Moving_Average_Investment_Strategy_Summary.md)
- [Level 2: 기술적 지표 모듈](../2025-11-13_technical_indicators_all.md)
- [Level 3-1: 기초 함수](../2025-11-14_collector_improvement_and_stage_level3_start.md)
- [Level 3-2: 메인 함수](../2025-11-14_stage_level3_2_determine_stage_and_transition.md)

---

## 작성자
- seunghakim
- AI Assistant (Claude)

## 검토 이력
- 2025-11-14: Level 3-3 계획 수립 ✅
  - 3개 보조 함수 계획 수립 ✅
  - 18개 테스트 시나리오 작성 ✅
  - 활용 방법 상세 기술 ✅
  - 예상 시간 산정 (2시간) ✅
