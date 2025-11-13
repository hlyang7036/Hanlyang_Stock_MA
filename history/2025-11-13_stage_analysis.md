# 스테이지 분석 모듈 구현 (Level 3)

## 날짜
2025-11-13

## 작업 개요
Level 3 공통 모듈인 스테이지 분석 모듈을 구현합니다. 이 모듈은 이동평균선 배열과 MACD를 활용하여 6단계 스테이지를 판단하고, 스테이지별 매매 전략을 제공합니다.

---

## 구현 목표

### 모듈 위치
**경로**: `src/analysis/stage.py`

### 핵심 기능
1. **이동평균선 배열 분석**: 3개 이동평균선(5일, 20일, 40일)의 상하 위치 관계 판단
2. **MACD 0선 교차 감지**: 3종 MACD의 0선 교차 시점 포착
3. **6단계 스테이지 판단**: 배열과 MACD를 종합하여 현재 스테이지 결정
4. **스테이지 전환 감지**: 스테이지가 바뀌는 시점 탐지
5. **보조 지표 제공**: 이동평균선 간격, 기울기 등
6. **전략 가이드**: 스테이지별 권장 매매 전략 제공

---

## 6단계 스테이지 개요

### 스테이지 정의

| 스테이지 | 배열 (위→아래) | MACD 전환 신호 | 시장 국면 | 전략 |
|---------|---------------|---------------|----------|------|
| **제1** | 단기>중기>장기 | MACD(하) -→0 | 안정 상승기 | 공격적 매수 |
| **제2** | 중기>단기>장기 | MACD(상) +→0 | 하락 변화기1 | 포지션 유지 판단 |
| **제3** | 중기>장기>단기 | MACD(중) +→0 | 하락 변화기2 | 매수 청산, 매도 진입 |
| **제4** | 장기>중기>단기 | MACD(하) +→0 | 안정 하락기 | 공격적 매도 |
| **제5** | 장기>단기>중기 | MACD(상) -→0 | 상승 변화기1 | 포지션 유지 판단 |
| **제6** | 단기>장기>중기 | MACD(중) -→0 | 상승 변화기2 | 매도 청산, 매수 진입 |

### 순환 구조
```
제1 (안정 상승) 
    ↓ 데드크로스1
제2 (하락 변화1) 
    ↓ 데드크로스2
제3 (하락 변화2) 
    ↓ 데드크로스3
제4 (안정 하락) 
    ↓ 골든크로스1
제5 (상승 변화1) 
    ↓ 골든크로스2
제6 (상승 변화2) 
    ↓ 골든크로스3
제1로 회귀 (순환)
```

---

## 구현할 함수 목록 (7개)

### 1. determine_ma_arrangement(data)
**목적**: 이동평균선 배열 순서 판단

**입력**:
- `data`: DataFrame (EMA_5, EMA_20, EMA_40 컬럼 필요)

**출력**:
- `pd.Series`: 각 시점의 배열 상태 (1~6)
  - 1: 단기 > 중기 > 장기
  - 2: 중기 > 단기 > 장기
  - 3: 중기 > 장기 > 단기
  - 4: 장기 > 중기 > 단기
  - 5: 장기 > 단기 > 중기
  - 6: 단기 > 장기 > 중기

**왜 필요한가?**
- 6단계 스테이지의 핵심은 이동평균선 배열
- 시각적 판단이 아닌 수치적 판단 필요
- 자동화를 위한 명확한 기준 제공

**알고리즘**:
```python
# 각 시점마다 3개 이동평균선 비교
if EMA_5 > EMA_20 > EMA_40:
    arrangement = 1
elif EMA_20 > EMA_5 > EMA_40:
    arrangement = 2
elif EMA_20 > EMA_40 > EMA_5:
    arrangement = 3
elif EMA_40 > EMA_20 > EMA_5:
    arrangement = 4
elif EMA_40 > EMA_5 > EMA_20:
    arrangement = 5
elif EMA_5 > EMA_40 > EMA_20:
    arrangement = 6
```

---

### 2. detect_macd_zero_cross(data)
**목적**: MACD 0선 교차 감지

**입력**:
- `data`: DataFrame (MACD_상, MACD_중, MACD_하 컬럼 필요)

**출력**:
- `pd.DataFrame`: 3개 컬럼
  - `Cross_상`: MACD(상) 0선 교차 (1: 골든크로스, -1: 데드크로스, 0: 없음)
  - `Cross_중`: MACD(중) 0선 교차
  - `Cross_하`: MACD(하) 0선 교차

**왜 필요한가?**
- MACD 0선 교차 = 이동평균선 교차
- 스테이지 전환의 핵심 신호
- 구체적 전환 시점 포착

**MACD 교차와 스테이지 전환**:
- MACD(상) +→0: 제2스테이지 진입 (데드크로스1)
- MACD(중) +→0: 제3스테이지 진입 (데드크로스2)
- MACD(하) +→0: 제4스테이지 진입 (데드크로스3)
- MACD(상) -→0: 제5스테이지 진입 (골든크로스1)
- MACD(중) -→0: 제6스테이지 진입 (골든크로스2)
- MACD(하) -→0: 제1스테이지 진입 (골든크로스3)

**알고리즘**:
```python
# 골든크로스 감지: 전일 음수 → 당일 양수
golden_cross = (data['MACD_상'].shift(1) < 0) & (data['MACD_상'] > 0)

# 데드크로스 감지: 전일 양수 → 당일 음수
dead_cross = (data['MACD_상'].shift(1) > 0) & (data['MACD_상'] < 0)

# 결과: 1(골든), -1(데드), 0(없음)
cross = golden_cross.astype(int) - dead_cross.astype(int)
```

---

### 3. determine_stage(data)
**목적**: 현재 스테이지 판단 (메인 함수)

**입력**:
- `data`: DataFrame (모든 지표 포함)

**출력**:
- `pd.Series`: 각 시점의 스테이지 (1~6)

**왜 필요한가?**
- 전체 시스템의 핵심 판단 함수
- 스테이지에 따라 매매 전략이 결정됨
- 백테스팅과 실전 매매 모두에서 사용

**판단 로직**:
1. 이동평균선 배열 확인 (`determine_ma_arrangement`)
2. MACD 0선 교차 확인 (`detect_macd_zero_cross`)
3. 두 정보를 종합하여 스테이지 판단
   - 기본: 배열 상태로 판단
   - 확정: MACD 교차 발생 시 스테이지 전환 확정

**알고리즘 개요**:
```python
# 1. 배열 기반 초기 판단
stage = determine_ma_arrangement(data)

# 2. MACD 교차로 전환 확정
cross = detect_macd_zero_cross(data)

# 3. 교차 발생 시 스테이지 업데이트
for i in range(len(data)):
    if cross['Cross_상'].iloc[i] == 1:  # 골든크로스1
        stage.iloc[i] = 5
    elif cross['Cross_중'].iloc[i] == 1:  # 골든크로스2
        stage.iloc[i] = 6
    elif cross['Cross_하'].iloc[i] == 1:  # 골든크로스3
        stage.iloc[i] = 1
    elif cross['Cross_상'].iloc[i] == -1:  # 데드크로스1
        stage.iloc[i] = 2
    elif cross['Cross_중'].iloc[i] == -1:  # 데드크로스2
        stage.iloc[i] = 3
    elif cross['Cross_하'].iloc[i] == -1:  # 데드크로스3
        stage.iloc[i] = 4
```

---

### 4. detect_stage_transition(data)
**목적**: 스테이지 전환 시점 감지

**입력**:
- `data`: DataFrame (Stage 컬럼 필요)

**출력**:
- `pd.Series`: 스테이지 전환 정보
  - 0: 전환 없음
  - 12, 23, 34 등: 이전→현재 스테이지 (예: 12 = 1→2 전환)

**왜 필요한가?**
- 스테이지 전환 시점 = 중요한 매매 타이밍
- 백테스팅에서 전환 시점 분석 필요
- 알림 시스템 구축에 활용
- 전환 패턴 분석 가능

**알고리즘**:
```python
# 이전 스테이지와 비교
prev_stage = data['Stage'].shift(1)
curr_stage = data['Stage']

# 전환 감지
transition = (prev_stage != curr_stage)

# 전환 값 생성: 이전*10 + 현재
transition_value = prev_stage * 10 + curr_stage
transition_value[~transition] = 0
```

---

### 5. calculate_ma_spread(data)
**목적**: 이동평균선 간격 계산

**입력**:
- `data`: DataFrame (EMA_5, EMA_20, EMA_40 필요)

**출력**:
- `pd.DataFrame`: 3개 컬럼
  - `Spread_5_20`: 단기-중기 간격 (EMA_5 - EMA_20)
  - `Spread_20_40`: 중기-장기 간격 (EMA_20 - EMA_40)
  - `Spread_5_40`: 단기-장기 간격 (EMA_5 - EMA_40)

**왜 필요한가?**
- 제2/5스테이지에서 포지션 유지 판단 기준
- 간격 확대/축소로 추세 강도 판단
- 전략: "중기-장기 간격이 줄어들지 않으면 포지션 유지"

**활용 예시**:
```python
# 제2스테이지에서 매수 포지션 유지 판단
if stage == 2:
    # 중기-장기 간격이 줄어들지 않으면 보유
    if Spread_20_40 >= Spread_20_40.shift(1):
        action = "hold"
    else:
        action = "consider_exit"
```

---

### 6. check_ma_slope(data, period=5)
**목적**: 이동평균선 기울기 확인

**입력**:
- `data`: DataFrame (EMA_5, EMA_20, EMA_40 필요)
- `period`: 기울기 계산 기간 (기본값: 5)

**출력**:
- `pd.DataFrame`: 3개 컬럼
  - `Slope_EMA_5`: 단기선 기울기
  - `Slope_EMA_20`: 중기선 기울기
  - `Slope_EMA_40`: 장기선 기울기

**왜 필요한가?**
- 제2/5스테이지 판단: "장기선이 여전히 상승/하락"
- 제3/6스테이지 조기 진입 판단: "장기선이 평행에 가까움"
- 3개선 모두 우상향/우하향 확인

**기울기 계산**:
- Level 2에서 구현한 `calculate_slope` 함수 재사용
- 선형 회귀 기울기 사용

**활용 예시**:
```python
# 제5스테이지에서 매도 포지션 유지 판단
if stage == 5:
    # 장기선이 여전히 하락 중이면 보유
    if Slope_EMA_40 < 0:
        action = "hold_short"
    else:
        action = "consider_exit"

# 제6스테이지 조기 매수 진입 판단
if stage == 6:
    # 단기·중기 우상향, 장기 평행
    if Slope_EMA_5 > 0 and Slope_EMA_20 > 0 and abs(Slope_EMA_40) < 0.1:
        action = "early_buy"
```

---

### 7. get_stage_strategy(stage, macd_directions=None)
**목적**: 스테이지별 권장 전략 제공

**입력**:
- `stage`: 현재 스테이지 (1~6)
- `macd_directions`: 3개 MACD 방향 (선택, Dict 또는 None)
  - 예: `{'상': 'up', '중': 'up', '하': 'up'}`

**출력**:
- `Dict`: 전략 정보
  ```python
  {
      'stage': 1,
      'name': '안정 상승기',
      'market_phase': '강세장',
      'strategy': '공격적 매수',
      'action': 'buy',
      'position_size': '적극적',
      'risk_level': 'low',
      'description': '완전 정배열, 강한 상승 추세',
      'key_points': [
          '3개 이동평균선 모두 우상향',
          '간격 확대 중',
          '매수 포지션 확대 적기'
      ]
  }
  ```

**왜 필요한가?**
- 스테이지만 알아서는 실제 액션 불명확
- 각 스테이지별 구체적인 전략 가이드 제공
- UI/알림에서 사용자에게 명확한 메시지 전달
- 백테스팅 결과 해석에 활용

**스테이지별 전략 매핑**:

| 스테이지 | 전략 | 액션 | 포지션 크기 | 리스크 |
|---------|------|------|-----------|--------|
| 1 | 공격적 매수 | buy | 적극적 | low |
| 2 | 포지션 유지 판단 | hold/exit | 유지/축소 | medium |
| 3 | 매수 청산, 매도 진입 | sell/short | 전량 청산 | high |
| 4 | 공격적 매도 | short | 적극적 | low |
| 5 | 포지션 유지 판단 | hold/exit | 유지/축소 | medium |
| 6 | 매도 청산, 매수 진입 | cover/buy | 전량 청산 | high |

---

## 기술적 세부사항

### 1. 이동평균선 배열 판단 알고리즘

**비교 방법**:
```python
def determine_ma_arrangement(data):
    ema_5 = data['EMA_5']
    ema_20 = data['EMA_20']
    ema_40 = data['EMA_40']
    
    arrangement = pd.Series(index=data.index, dtype=int)
    
    # 6가지 배열 패턴 판단
    arrangement[(ema_5 > ema_20) & (ema_20 > ema_40)] = 1
    arrangement[(ema_20 > ema_5) & (ema_5 > ema_40)] = 2
    arrangement[(ema_20 > ema_40) & (ema_40 > ema_5)] = 3
    arrangement[(ema_40 > ema_20) & (ema_20 > ema_5)] = 4
    arrangement[(ema_40 > ema_5) & (ema_5 > ema_20)] = 5
    arrangement[(ema_5 > ema_40) & (ema_40 > ema_20)] = 6
    
    return arrangement
```

**엣지 케이스 처리**:
1. **동일값 처리**: 
   - 두 이동평균선이 거의 같을 때 (차이 < 0.01%)
   - 이전 배열 상태 유지
   
2. **NaN 처리**:
   - 초기 기간 NaN → 배열 판단 불가
   - NaN은 0 또는 특수값으로 표시

---

### 2. MACD 0선 교차 감지

**정확한 교차 감지**:
```python
def detect_macd_zero_cross(data):
    crosses = pd.DataFrame(index=data.index)
    
    for macd_col in ['MACD_상', 'MACD_중', 'MACD_하']:
        macd = data[macd_col]
        
        # 골든크로스: 음수 → 양수
        golden = (macd.shift(1) < 0) & (macd > 0)
        
        # 데드크로스: 양수 → 음수
        dead = (macd.shift(1) > 0) & (macd < 0)
        
        # 1: 골든, -1: 데드, 0: 없음
        cross_name = macd_col.replace('MACD_', 'Cross_')
        crosses[cross_name] = golden.astype(int) - dead.astype(int)
    
    return crosses
```

**필터링 (선택적)**:
- 0선 근처 진동 필터링
- 예: MACD 절댓값이 임계값 이상일 때만 교차로 인정
- 또는 N일 연속 양수/음수 유지 후 확정

---

### 3. 스테이지 판단 통합 로직

**우선순위**:
1. MACD 0선 교차 (최우선) → 즉시 스테이지 전환
2. 이동평균선 배열 (기본) → 배열 상태로 스테이지 판단

**구현 방식**:
```python
def determine_stage(data):
    # 1. 배열 기반 초기 스테이지
    stage = determine_ma_arrangement(data)
    
    # 2. MACD 교차로 스테이지 확정
    cross = detect_macd_zero_cross(data)
    
    # 3. 교차 우선 적용
    stage[cross['Cross_상'] == 1] = 5   # 골든크로스1
    stage[cross['Cross_중'] == 1] = 6   # 골든크로스2
    stage[cross['Cross_하'] == 1] = 1   # 골든크로스3
    stage[cross['Cross_상'] == -1] = 2  # 데드크로스1
    stage[cross['Cross_중'] == -1] = 3  # 데드크로스2
    stage[cross['Cross_하'] == -1] = 4  # 데드크로스3
    
    return stage
```

---

### 4. 스테이지 전환 감지

**전환 인코딩**:
```python
def detect_stage_transition(data):
    stage = data['Stage']
    prev_stage = stage.shift(1)
    
    # 전환 발생 여부
    is_transition = (stage != prev_stage)
    
    # 전환 값: 이전 스테이지 * 10 + 현재 스테이지
    # 예: 1→2 = 12, 2→3 = 23
    transition = prev_stage * 10 + stage
    transition[~is_transition] = 0
    
    return transition
```

**활용 방법**:
```python
# 특정 전환 필터링
stage_2_to_3 = (transition == 23)  # 제2→제3 전환
stage_6_to_1 = (transition == 61)  # 제6→제1 전환

# 알림 발송
if transition.iloc[-1] in [12, 23, 34, 45, 56, 61]:
    send_notification(f"스테이지 전환: {transition.iloc[-1]}")
```

---

## 테스트 계획 (약 30개)

### TestDetermineMAArrangement (7개)
1. `test_arrangement_1` - 단기>중기>장기
2. `test_arrangement_2` - 중기>단기>장기
3. `test_arrangement_3` - 중기>장기>단기
4. `test_arrangement_4` - 장기>중기>단기
5. `test_arrangement_5` - 장기>단기>중기
6. `test_arrangement_6` - 단기>장기>중기
7. `test_arrangement_edge_cases` - 동일값 처리

---

### TestDetectMACDZeroCross (6개)
1. `test_golden_cross_upper` - MACD(상) 골든크로스
2. `test_golden_cross_middle` - MACD(중) 골든크로스
3. `test_golden_cross_lower` - MACD(하) 골든크로스
4. `test_dead_cross_upper` - MACD(상) 데드크로스
5. `test_dead_cross_middle` - MACD(중) 데드크로스
6. `test_dead_cross_lower` - MACD(하) 데드크로스

---

### TestDetermineStage (8개)
1. `test_stage_1` - 제1스테이지 판단
2. `test_stage_2` - 제2스테이지 판단
3. `test_stage_3` - 제3스테이지 판단
4. `test_stage_4` - 제4스테이지 판단
5. `test_stage_5` - 제5스테이지 판단
6. `test_stage_6` - 제6스테이지 판단
7. `test_stage_transition` - 스테이지 전환 시나리오
8. `test_stage_with_real_data` - 실전 데이터 테스트

---

### TestDetectStageTransition (4개)
1. `test_transition_detection` - 전환 감지 정확성
2. `test_no_transition` - 전환 없음 케이스
3. `test_multiple_transitions` - 연속 전환
4. `test_transition_encoding` - 전환 값 인코딩

---

### TestCalculateMASpread (3개)
1. `test_spread_calculation` - 간격 계산 정확성
2. `test_spread_positive_negative` - 양수/음수 케이스
3. `test_spread_change_tracking` - 간격 변화 추적

---

### TestCheckMASlope (3개)
1. `test_slope_uptrend` - 우상향 판단
2. `test_slope_downtrend` - 우하향 판단
3. `test_slope_flat` - 평행 판단

---

### TestGetStageStrategy (6개)
1. `test_strategy_stage_1` - 제1스테이지 전략
2. `test_strategy_stage_2` - 제2스테이지 전략
3. `test_strategy_stage_3` - 제3스테이지 전략
4. `test_strategy_stage_4` - 제4스테이지 전략
5. `test_strategy_stage_5` - 제5스테이지 전략
6. `test_strategy_stage_6` - 제6스테이지 전략

---

### TestStageAnalysisIntegration (3개)
1. `test_full_cycle` - 제1→제6 전체 순환
2. `test_with_all_indicators` - 모든 지표와 통합
3. `test_strategy_recommendation` - 전략 추천 통합

---

## 예상되는 기술적 이슈

### 이슈 1: 스테이지 판단 모호성
**문제**: 
- 이동평균선이 거의 같을 때 배열 판단 어려움
- 예: EMA_5 = 100.00, EMA_20 = 99.99

**해결 방안**:
```python
# 임계값 설정 (0.1% 이내는 동일로 간주)
threshold = 0.001

# 이전 배열 유지 로직
if abs(ema_5 - ema_20) / ema_20 < threshold:
    arrangement = prev_arrangement
```

---

### 이슈 2: MACD 0선 근처 진동
**문제**: 
- 0선 근처에서 여러 번 교차 (가짜 신호)
- 예: +0.01 → -0.01 → +0.02 → -0.01

**해결 방안 (옵션)**:
1. **필터링**: 절댓값이 임계값 이상일 때만 교차로 인정
   ```python
   threshold = 0.5
   if abs(macd) < threshold:
       ignore_cross = True
   ```

2. **확정**: N일 연속 유지 후 스테이지 전환
   ```python
   if macd > 0 for 3 consecutive days:
       confirm_golden_cross = True
   ```

3. **시그널선 활용**: MACD와 시그널선 거리 확인
   ```python
   if abs(macd - signal) > threshold:
       more_reliable = True
   ```

**권장**: 초기에는 필터링 없이 구현, 백테스트 후 필요 시 추가

---

### 이슈 3: 스테이지 순차 진행 보장
**문제**: 
- 이론상 1→2→3→...→6→1 순차 진행
- 현실에서는 1→3 같은 비순차 전환 가능

**원인**:
- 급격한 가격 변동
- 이동평균선이 동시에 교차
- 데이터 오류

**해결 방안**:
1. **감지**: 비순차 전환 로깅
   ```python
   expected_next = {1: 2, 2: 3, 3: 4, 4: 5, 5: 6, 6: 1}
   if next_stage != expected_next[current_stage]:
       logger.warning(f"비순차 전환 감지: {current_stage}→{next_stage}")
   ```

2. **허용**: 비순차 전환도 유효한 신호로 처리
   - 시장이 급변하는 경우 발생 가능
   - 전환 자체는 의미 있음

3. **사용자 알림**: 비정상 패턴 알림

---

### 이슈 4: 초기 데이터 부족
**문제**: 
- EMA_40 계산에 최소 40일 필요
- MACD(하) 계산에 49일 필요
- 초기 기간 스테이지 판단 불가

**해결 방안**:
```python
def determine_stage(data):
    # 최소 데이터 길이 검증
    if len(data) < 49:
        raise ValueError(f"최소 49일 데이터 필요. 현재: {len(data)}일")
    
    # 초기 NaN 기간은 스테이지 0 또는 NaN
    stage = pd.Series(0, index=data.index)
    
    # 유효한 데이터부터 스테이지 판단
    valid_idx = data['MACD_하'].notna()
    stage[valid_idx] = ...
```

---

## 실전 활용 예시

### 예시 1: 스테이지 판단 및 전략

```python
from src.data import get_stock_data
from src.analysis.technical import calculate_all_indicators
from src.analysis.stage import determine_stage, get_stage_strategy

# 데이터 수집 및 지표 계산
df = get_stock_data('005930', days=50)
df = calculate_all_indicators(df)

# 스테이지 판단
df['Stage'] = determine_stage(df)

# 현재 스테이지 및 전략
current_stage = df['Stage'].iloc[-1]
strategy = get_stage_strategy(current_stage)

print(f"현재 스테이지: {current_stage} ({strategy['name']})")
print(f"시장 국면: {strategy['market_phase']}")
print(f"권장 전략: {strategy['strategy']}")
print(f"액션: {strategy['action']}")
print(f"\n핵심 포인트:")
for point in strategy['key_points']:
    print(f"  - {point}")
```

---

### 예시 2: 스테이지 전환 감지

```python
from src.analysis.stage import detect_stage_transition

# 스테이지 전환 감지
df['Transition'] = detect_stage_transition(df)

# 전환 발생 지점
transitions = df[df['Transition'] != 0]

print("스테이지 전환 히스토리:")
for idx, row in transitions.iterrows():
    prev = int(row['Transition'] / 10)
    curr = int(row['Transition'] % 10)
    print(f"{idx.date()}: 제{prev}스테이지 → 제{curr}스테이지")

# 최근 전환
if df['Transition'].iloc[-1] != 0:
    print(f"\n⚠️ 방금 스테이지 전환 발생!")
```

---

### 예시 3: 제2스테이지 포지션 유지 판단

```python
from src.analysis.stage import calculate_ma_spread, check_ma_slope

# 스테이지 2에서 매수 포지션 유지 판단
if current_stage == 2:
    # 간격 확인
    df_spread = calculate_ma_spread(df)
    spread_20_40 = df_spread['Spread_20_40'].iloc[-1]
    prev_spread_20_40 = df_spread['Spread_20_40'].iloc[-2]
    
    # 기울기 확인
    df_slope = check_ma_slope(df, period=5)
    slope_40 = df_slope['Slope_EMA_40'].iloc[-1]
    
    # 판단
    if spread_20_40 >= prev_spread_20_40 and slope_40 > 0:
        action = "매수 포지션 유지"
        reason = "중기-장기 간격 유지 & 장기선 상승"
    else:
        action = "포지션 축소 또는 청산 검토"
        reason = "중기-장기 간격 축소 또는 장기선 하락"
    
    print(f"제2스테이지 판단:")
    print(f"  액션: {action}")
    print(f"  이유: {reason}")
```

---

### 예시 4: 제6스테이지 조기 매수 판단

```python
# 스테이지 6에서 조기 매수 진입 판단
if current_stage == 6:
    # 기울기 확인
    df_slope = check_ma_slope(df, period=5)
    slope_5 = df_slope['Slope_EMA_5'].iloc[-1]
    slope_20 = df_slope['Slope_EMA_20'].iloc[-1]
    slope_40 = df_slope['Slope_EMA_40'].iloc[-1]
    
    # MACD 방향 확인
    macd_directions = {
        '상': df['Dir_MACD_상'].iloc[-1],
        '중': df['Dir_MACD_중'].iloc[-1],
        '하': df['Dir_MACD_하'].iloc[-1]
    }
    
    # 조기 매수 조건
    if (slope_5 > 0 and slope_20 > 0 and abs(slope_40) < 0.1 and
        all(d == 'up' for d in macd_directions.values())):
        action = "조기 매수 진입"
        signal_strength = "강함"
    else:
        action = "통상 매수 대기"
        signal_strength = "약함"
    
    print(f"제6스테이지 조기 진입 판단:")
    print(f"  액션: {action}")
    print(f"  신호 강도: {signal_strength}")
    print(f"  단기선 기울기: {slope_5:.4f}")
    print(f"  중기선 기울기: {slope_20:.4f}")
    print(f"  장기선 기울기: {slope_40:.4f}")
```

---

## 구현 순서

### 1단계: 기본 함수 (1-2일) ⏳
1. `determine_ma_arrangement()` 구현
2. `detect_macd_zero_cross()` 구현
3. 테스트 13개 작성 및 통과

---

### 2단계: 메인 함수 (1-2일) ⏳
4. `determine_stage()` 구현
5. `detect_stage_transition()` 구현
6. 테스트 12개 작성 및 통과

---

### 3단계: 보조 함수 (1일) ⏳
7. `calculate_ma_spread()` 구현
8. `check_ma_slope()` 구현 (Level 2 함수 재사용)
9. `get_stage_strategy()` 구현
10. 테스트 12개 작성 및 통과

---

### 4단계: 통합 테스트 및 문서화 (1일) ⏳
- 실전 시뮬레이션 데이터로 통합 테스트 3개
- 이슈 해결 및 리팩토링
- 문서 업데이트 (구현 결과 추가)
- README 업데이트

---

## 성공 기준

### 필수 조건
- ✅ 7개 함수 모두 구현
- ✅ 30개 이상 테스트 모두 통과
- ✅ 실전 데이터로 스테이지 판단 가능
- ✅ 문서화 완료

### 품질 기준
- ✅ 타입 힌트 명확
- ✅ Docstring 완비 (Google 스타일)
- ✅ 에러 처리 철저
- ✅ 로깅 적절
- ✅ 코드 가독성 높음

---

## 다음 단계 (Level 4)

Level 3 완료 후:
- **Level 4**: 매매 신호 생성 모듈 (`src/analysis/signal/`)
  - 진입 신호 생성 (통상/조기 매수/매도)
  - 청산 신호 생성 (3단계)
  - 신호 강도 평가
  - 신호 필터링

---

## 참고 자료

- [이동평균선 투자법 전략 정리](../Moving_Average_Investment_Strategy_Summary.md)
- [개발 계획](./2025-10-30_common_modules_planning.md)
- [Level 2: 기술적 지표 모듈](./2025-11-13_technical_indicators_all.md)

---

## 작성자
- seunghakim
- AI Assistant (Claude)

## 검토 이력
- 2025-11-13: Level 3 스테이지 분석 모듈 계획 수립 ✅
  - 구현할 함수 7개 정의 ✅
  - 테스트 계획 30개 수립 ✅
  - 기술적 이슈 4가지 식별 ✅
  - 구현 순서 및 일정 계획 ✅
