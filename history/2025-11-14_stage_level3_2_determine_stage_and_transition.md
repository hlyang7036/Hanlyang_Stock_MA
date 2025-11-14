# 스테이지 분석 모듈 Level 3-2단계 구현

## 날짜
2025-11-14

## 작업 개요
Level 3 스테이지 분석 모듈의 2단계로, 핵심 함수인 `determine_stage()`와 `detect_stage_transition()`을 구현했습니다. 이 두 함수는 이동평균선 배열과 MACD 교차를 종합하여 6단계 스테이지를 판단하고, 스테이지 전환 시점을 감지하는 메인 함수들입니다.

---

## 구현 내용

### 1. determine_stage() 함수 구현

**목적**: 이동평균선 배열과 MACD 0선 교차를 종합하여 현재 스테이지 판단

**위치**: `src/analysis/stage.py`

#### 함수 시그니처
```python
def determine_stage(data: pd.DataFrame) -> pd.Series:
    """
    이동평균선 배열과 MACD 0선 교차를 종합하여 현재 스테이지 판단
    
    Args:
        data: DataFrame (필수 컬럼: EMA_5, EMA_20, EMA_40, MACD_상, MACD_중, MACD_하)
    
    Returns:
        pd.Series: 각 시점의 스테이지 (1~6)
    """
```

#### 알고리즘 (3단계)

**1단계: 이동평균선 배열로 기본 스테이지 판단**
```python
# 이미 구현된 determine_ma_arrangement() 활용
stage = determine_ma_arrangement(data)
```

**2단계: MACD 0선 교차 감지**
```python
# 이미 구현된 detect_macd_zero_cross() 활용
crosses = detect_macd_zero_cross(data)
```

**3단계: MACD 교차로 스테이지 확정 (우선순위 적용)**
```python
# 우선순위: Cross_하 > Cross_중 > Cross_상
stage[crosses['Cross_하'] == 1] = 1   # 골든크로스3 → 제1스테이지
stage[crosses['Cross_하'] == -1] = 4  # 데드크로스3 → 제4스테이지
stage[crosses['Cross_중'] == 1] = 6   # 골든크로스2 → 제6스테이지
stage[crosses['Cross_중'] == -1] = 3  # 데드크로스2 → 제3스테이지
stage[crosses['Cross_상'] == 1] = 5   # 골든크로스1 → 제5스테이지
stage[crosses['Cross_상'] == -1] = 2  # 데드크로스1 → 제2스테이지
```

#### 스테이지 판단 매핑

| 배열 패턴 | MACD 교차 | 확정 스테이지 | 의미 |
|---------|----------|-------------|------|
| 1 (단>중>장) | Cross_하 = 1 | 1 | 골든크로스3, 상승 확정 |
| 2 (중>단>장) | Cross_상 = -1 | 2 | 데드크로스1, 하락 시작 |
| 3 (중>장>단) | Cross_중 = -1 | 3 | 데드크로스2, 하락 가속 |
| 4 (장>중>단) | Cross_하 = -1 | 4 | 데드크로스3, 하락 확정 |
| 5 (장>단>중) | Cross_상 = 1 | 5 | 골든크로스1, 상승 시작 |
| 6 (단>장>중) | Cross_중 = 1 | 6 | 골든크로스2, 상승 가속 |

#### 핵심 특징

1. **MACD 우선 원칙**
   - MACD 0선 교차가 배열 패턴보다 우선
   - 명확한 전환 신호로 스테이지 확정

2. **우선순위 적용**
   - Cross_하 > Cross_중 > Cross_상
   - 동시 교차 시 더 강력한 신호 우선

3. **로깅 시스템**
   - 각 단계별 상세 로깅
   - 교차 발생 횟수 집계
   - 스테이지 분포 통계

4. **에러 처리**
   - 필수 컬럼 검증
   - 타입 체크
   - 명확한 에러 메시지

---

### 2. detect_stage_transition() 함수 구현

**목적**: 스테이지 전환 시점 감지 및 전환 유형 판단

**위치**: `src/analysis/stage.py`

#### 함수 시그니처
```python
def detect_stage_transition(data: pd.DataFrame) -> pd.Series:
    """
    스테이지 전환 시점 감지
    
    Args:
        data: DataFrame (Stage 컬럼 필요)
    
    Returns:
        pd.Series: 스테이지 전환 정보
            0: 전환 없음
            12, 23, 34...: 이전→현재 (예: 12 = 1→2 전환)
    """
```

#### 알고리즘 (간단명료)

```python
def detect_stage_transition(data: pd.DataFrame) -> pd.Series:
    # 1. 현재 및 이전 스테이지
    current_stage = data['Stage']
    prev_stage = current_stage.shift(1)
    
    # 2. 전환 여부 확인
    is_transition = (current_stage != prev_stage)
    
    # 3. 전환 값 계산: 이전*10 + 현재
    transition = prev_stage * 10 + current_stage
    
    # 4. 전환 없으면 0
    transition[~is_transition] = 0
    
    # 5. 첫 행은 비교 불가 → 0
    transition.iloc[0] = 0
    
    # 6. NaN 처리
    transition[current_stage.isna()] = np.nan
    
    return transition.astype('Int64')  # nullable integer
```

#### 전환 값 인코딩

| 전환 값 | 의미 | 해석 |
|--------|------|------|
| 0 | 전환 없음 | 스테이지 유지 |
| 12 | 1→2 | 데드크로스1 발생 |
| 23 | 2→3 | 데드크로스2 발생 |
| 34 | 3→4 | 데드크로스3 발생 |
| 45 | 4→5 | 골든크로스1 발생 |
| 56 | 5→6 | 골든크로스2 발생 |
| 61 | 6→1 | 골든크로스3 발생 (순환 완료) |

**비순차 전환** (드물지만 가능):
- 13, 24, 35 등 - 급격한 시장 변화

#### 핵심 특징

1. **간단한 로직**
   - shift(1)로 이전 값 비교
   - 인코딩으로 전환 유형 명확화

2. **엣지 케이스 처리**
   - 첫 행 처리 (비교 대상 없음)
   - NaN 전파
   - nullable integer 타입 사용

3. **통계 로깅**
   - 전환 발생 횟수
   - 전환 유형별 집계
   - 제X→제Y 형태로 로깅

---

## 테스트 코드

### TestDetermineStage 클래스 (8개)

#### 1. 제1~6스테이지 판단 테스트 (6개)

```python
def test_stage_1_determination(self):
    """제1스테이지: 완전 정배열 + MACD(하) 골든크로스"""
    df = pd.DataFrame({
        'EMA_5': [110, 115, 120],
        'EMA_20': [105, 108, 112],
        'EMA_40': [100, 102, 105],
        'MACD_상': [1.0, 1.2, 1.5],
        'MACD_중': [0.5, 0.8, 1.0],
        'MACD_하': [-0.5, 0.2, 0.8]  # 골든크로스
    })
    
    stage = determine_stage(df)
    
    # MACD(하) 골든크로스 발생 → 제1스테이지 확정
    assert stage.iloc[1] == 1
```

**패턴**:
- `test_stage_1_determination` - 완전 정배열 + MACD(하) 골든
- `test_stage_2_determination` - 패턴2 + MACD(상) 데드
- `test_stage_3_determination` - 패턴3 + MACD(중) 데드
- `test_stage_4_determination` - 완전 역배열 + MACD(하) 데드
- `test_stage_5_determination` - 패턴5 + MACD(상) 골든
- `test_stage_6_determination` - 패턴6 + MACD(중) 골든

#### 2. 전환 시나리오 테스트 (1개)

```python
def test_stage_transition_scenario(self):
    """제1→제2 전환 시나리오"""
    df = pd.DataFrame({
        'EMA_5': [110, 108, 105],
        'EMA_20': [105, 107, 108],
        'EMA_40': [100, 102, 110],
        'MACD_상': [1.0, 0.5, -0.3],  # 데드크로스
        'MACD_중': [1.5, 1.2, 0.5],
        'MACD_하': [2.0, 1.8, 1.5]
    })
    
    stage = determine_stage(df)
    
    assert stage.iloc[0] == 1  # 완전 정배열
    assert stage.iloc[2] == 2  # 데드크로스1 → 제2스테이지
```

#### 3. 에러 케이스 (1개)

```python
def test_stage_missing_columns(self):
    """에러: 필수 컬럼 누락"""
    df = pd.DataFrame({
        'EMA_5': [110, 115],
        'EMA_20': [105, 108],
        'EMA_40': [100, 102]
        # MACD 컬럼 누락
    })
    
    with pytest.raises(ValueError, match="필수 컬럼이 없습니다"):
        determine_stage(df)
```

---

### TestDetectStageTransition 클래스 (6개)

#### 1. 정상 전환 감지 (1개)

```python
def test_transition_detection(self):
    """정상적인 스테이지 전환 감지"""
    df = pd.DataFrame({
        'Stage': [1, 1, 2, 2, 3, 3]
    })
    
    transition = detect_stage_transition(df)
    
    assert transition.iloc[0] == 0   # 첫 행
    assert transition.iloc[1] == 0   # 1→1 (유지)
    assert transition.iloc[2] == 12  # 1→2 전환
    assert transition.iloc[3] == 0   # 2→2 (유지)
    assert transition.iloc[4] == 23  # 2→3 전환
```

#### 2. 전환 없음 (1개)

```python
def test_no_transition(self):
    """스테이지 전환이 없는 경우"""
    df = pd.DataFrame({'Stage': [1, 1, 1, 1, 1]})
    
    transition = detect_stage_transition(df)
    
    assert all(transition == 0)
```

#### 3. 연속 전환 (1개)

```python
def test_multiple_transitions(self):
    """연속적인 스테이지 전환"""
    df = pd.DataFrame({'Stage': [1, 2, 3, 4, 5, 6, 1]})
    
    transition = detect_stage_transition(df)
    
    assert transition.iloc[1] == 12  # 1→2
    assert transition.iloc[2] == 23  # 2→3
    assert transition.iloc[3] == 34  # 3→4
    assert transition.iloc[4] == 45  # 4→5
    assert transition.iloc[5] == 56  # 5→6
    assert transition.iloc[6] == 61  # 6→1 (순환)
```

#### 4. 비순차 전환 인코딩 (1개)

```python
def test_transition_encoding(self):
    """비순차 전환도 올바르게 인코딩"""
    df = pd.DataFrame({'Stage': [1, 3, 2, 5]})
    
    transition = detect_stage_transition(df)
    
    assert transition.iloc[1] == 13  # 1→3
    assert transition.iloc[2] == 32  # 3→2
    assert transition.iloc[3] == 25  # 2→5
```

#### 5-6. 에러 케이스 (2개)

```python
def test_transition_missing_column(self):
    """에러: Stage 컬럼 누락"""
    df = pd.DataFrame({'NotStage': [1, 2, 3]})
    
    with pytest.raises(ValueError, match="Stage 컬럼이 필요합니다"):
        detect_stage_transition(df)

def test_transition_invalid_type(self):
    """에러: 잘못된 타입"""
    with pytest.raises(TypeError, match="DataFrame이 필요합니다"):
        detect_stage_transition([1, 2, 3])
```

---

## 테스트 결과

### ✅ 전체 테스트 통과

```bash
pytest src/tests/analysis/test_stage.py -v
```

**결과**: 35개 테스트 모두 통과 ✅

| 테스트 클래스 | 테스트 수 | 결과 |
|-------------|----------|------|
| TestDetermineMAArrangement | 9개 | ✅ PASSED |
| TestDetectMACDZeroCross | 12개 | ✅ PASSED |
| **TestDetermineStage** | **8개** | ✅ **PASSED** |
| **TestDetectStageTransition** | **6개** | ✅ **PASSED** |
| **총계** | **35개** | ✅ **ALL PASSED** |

---

## 코드 품질

### 1. 타입 힌팅
```python
def determine_stage(data: pd.DataFrame) -> pd.Series:
def detect_stage_transition(data: pd.DataFrame) -> pd.Series:
```

### 2. Docstring (Google 스타일)
- 함수 설명
- Args, Returns, Raises
- Notes (스테이지 전환 매핑)
- Examples (사용 예시)

### 3. 에러 처리
- 입력 타입 검증
- 필수 컬럼 확인
- 명확한 에러 메시지

### 4. 로깅
```python
logger.debug(f"스테이지 판단 시작: {len(data)}개 데이터")
logger.info(f"골든크로스3 발생: {gc3_count}회 → 제1스테이지 확정")
logger.debug(f"스테이지 분포: {stage_counts.to_dict()}")
```

---

## 활용 예시

### 예시 1: 기본 사용법

```python
from src.data import get_stock_data
from src.analysis.technical import calculate_all_indicators
from src.analysis.stage import determine_stage

# 데이터 수집 및 지표 계산
df = get_stock_data('005930', days=100)
df = calculate_all_indicators(df)

# 스테이지 판단
df['Stage'] = determine_stage(df)

# 현재 스테이지 확인
current_stage = df['Stage'].iloc[-1]
print(f"현재 스테이지: 제{current_stage}스테이지")
```

### 예시 2: 스테이지 전환 감지

```python
from src.analysis.stage import detect_stage_transition

# 스테이지 전환 감지
df['Transition'] = detect_stage_transition(df)

# 전환 발생 지점 추출
transitions = df[df['Transition'] != 0]

print("스테이지 전환 히스토리:")
for idx, row in transitions.iterrows():
    prev = int(row['Transition'] / 10)
    curr = int(row['Transition'] % 10)
    print(f"{idx.date()}: 제{prev}→제{curr} 전환")

# 최근 전환 확인
if df['Transition'].iloc[-1] != 0:
    print("⚠️ 방금 스테이지 전환 발생!")
```

### 예시 3: 전환 필터링

```python
# 특정 전환만 추출
gc3_transitions = df[df['Transition'] == 61]  # 골든크로스3
dc1_transitions = df[df['Transition'] == 12]  # 데드크로스1

print(f"골든크로스3 (매수 신호): {len(gc3_transitions)}회")
print(f"데드크로스1 (매도 주의): {len(dc1_transitions)}회")

# 상승/하락 전환 집계
uptrend_transitions = df[df['Transition'].isin([45, 56, 61])]
downtrend_transitions = df[df['Transition'].isin([12, 23, 34])]

print(f"상승 전환: {len(uptrend_transitions)}회")
print(f"하락 전환: {len(downtrend_transitions)}회")
```

---

## 진행 상황

### ✅ 완료된 작업

| 모듈 | 함수 | 테스트 | 상태 |
|------|------|--------|------|
| **collector.py** | get_stock_data() | 8개 | ✅ 개선 완료 |
| **stage.py** | determine_ma_arrangement() | 9개 | ✅ 구현 완료 |
| **stage.py** | detect_macd_zero_cross() | 12개 | ✅ 구현 완료 |
| **stage.py** | **determine_stage()** | **8개** | ✅ **구현 완료** |
| **stage.py** | **detect_stage_transition()** | **6개** | ✅ **구현 완료** |
| **총계** | **5개 함수** | **43개** | ✅ |

### 📊 Level 3 진행률

| 단계 | 함수 수 | 테스트 수 | 상태 |
|------|---------|----------|------|
| **Level 3-1** | 2개 | 21개 | ✅ 완료 |
| **Level 3-2** | 2개 | 14개 | ✅ **완료** |
| **Level 3-3** | 3개 | - | ⏳ 예정 |
| **총 예정** | 7개 | ~37개 | - |

---

## 다음 단계: Level 3-3

### 구현 예정 함수 (3개)

#### 1. calculate_ma_spread()
**목적**: 이동평균선 간격 계산

**출력**:
- `Spread_5_20`: 단기-중기 간격
- `Spread_20_40`: 중기-장기 간격
- `Spread_5_40`: 단기-장기 간격

**활용**: 제2/5스테이지 포지션 유지 판단

---

#### 2. check_ma_slope()
**목적**: 이동평균선 기울기 확인

**출력**:
- `Slope_EMA_5`: 단기선 기울기
- `Slope_EMA_20`: 중기선 기울기
- `Slope_EMA_40`: 장기선 기울기

**활용**: 제2/5스테이지 장기선 방향 확인

---

#### 3. get_stage_strategy()
**목적**: 스테이지별 권장 전략 제공

**출력**:
```python
{
    'stage': 1,
    'name': '안정 상승기',
    'market_phase': '강세장',
    'strategy': '공격적 매수',
    'action': 'buy',
    'position_size': '적극적',
    'risk_level': 'low',
    'key_points': [...]
}
```

**활용**: UI/알림, 백테스팅 결과 해석

---

## 기술적 이슈 및 해결

### 이슈 1: MACD 교차 우선순위 적용

**문제**: 
- 배열 패턴과 MACD 교차가 불일치할 수 있음
- 예: 배열은 패턴1인데 MACD(중)이 골든크로스

**해결**:
```python
# MACD 교차가 우선, 순서대로 적용
# 우선순위: Cross_하 > Cross_중 > Cross_상

# 1. Cross_하 먼저 적용 (가장 강력)
stage[crosses['Cross_하'] == 1] = 1
stage[crosses['Cross_하'] == -1] = 4

# 2. Cross_중 적용
stage[crosses['Cross_중'] == 1] = 6
stage[crosses['Cross_중'] == -1] = 3

# 3. Cross_상 마지막 적용
stage[crosses['Cross_상'] == 1] = 5
stage[crosses['Cross_상'] == -1] = 2
```

**결과**: ✅ 명확한 우선순위로 일관된 판단

---

### 이슈 2: nullable integer 타입

**문제**:
- `detect_stage_transition()`에서 NaN 처리 필요
- 일반 int는 NaN 지원 안함

**해결**:
```python
# pandas의 nullable integer 타입 사용
return transition.astype('Int64')  # 'Int64' (대문자)
```

**효과**:
- NaN과 정수를 동시에 표현 가능
- 타입 일관성 유지

---

### 이슈 3: 첫 행 처리

**문제**:
- `detect_stage_transition()`에서 shift(1) 사용
- 첫 행은 이전 데이터가 없음

**해결**:
```python
# 첫 행은 명시적으로 0 설정
transition.iloc[0] = 0
```

---

## 학습 내용

### 1. 벡터 연산의 효율성
- 루프 대신 pandas 벡터 연산 사용
- `stage[crosses['Cross_하'] == 1] = 1` 형태
- 성능 향상 및 가독성 개선

### 2. 로깅 전략
- 단계별 로깅으로 디버깅 용이
- 통계 정보 제공으로 데이터 파악
- 교차 발생 횟수, 스테이지 분포 등

### 3. 우선순위 설계
- MACD 교차 우선순위 명확화
- 순차적 적용으로 충돌 방지
- 강력한 신호부터 적용

---

## 참고 자료

- [이동평균선 투자법 전략 정리](../Moving_Average_Investment_Strategy_Summary.md)
- [Level 2: 기술적 지표 모듈](./2025-11-13_technical_indicators_all.md)
- [Level 3: 스테이지 분석 계획](plan/2025-11-13_stage_analysis.md)
- [Level 3-1단계: 기초 함수](./2025-11-14_collector_improvement_and_stage_level3_start.md)

---

## 작성자
- seunghakim
- AI Assistant (Claude)

## 검토 이력
- 2025-11-14: Level 3-2단계 구현 완료 ✅
  - determine_stage() 구현 ✅
  - detect_stage_transition() 구현 ✅
  - 테스트 14개 작성 ✅
  - 전체 테스트 35개 통과 ✅
  - 다음 단계 계획 수립 ✅
