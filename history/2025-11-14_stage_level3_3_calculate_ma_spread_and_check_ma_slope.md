# Level 3-3단계 보조 함수 구현 완료

## 날짜
2025-11-14

## 작업 개요
Level 3 스테이지 분석 모듈의 마지막 단계인 3개의 보조 함수를 구현했습니다. 이 함수들은 스테이지 판단을 보조하고, 구체적인 매매 전략을 제공하는 역할을 합니다.

---

## 구현 완료 함수 목록

### 1. calculate_ma_spread() - 이동평균선 간격 계산
### 2. check_ma_slope() - 이동평균선 기울기 확인
### 3. get_stage_strategy() - 스테이지별 권장 전략 제공

---

## 1. calculate_ma_spread() 함수

### 구현 위치
- **파일**: `src/analysis/stage.py`
- **라인**: 함수 추가

### 함수 명세

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
    """
```

### 구현 특징

1. **단순 뺄셈 연산**
   - 복잡한 계산 없이 이동평균선 간 차이를 직접 계산
   - 양수: 위쪽 MA가 위에 위치 (정배열 방향)
   - 음수: 아래쪽 MA가 위에 위치 (역배열 방향)

2. **3개의 간격 지표 제공**
   - `Spread_5_20`: 단기-중기 관계
   - `Spread_20_40`: 중기-장기 관계
   - `Spread_5_40`: 단기-장기 관계 (전체 추세)

3. **간격 통계 로깅**
   - 각 간격의 평균값을 로깅하여 추세 강도 파악

### 활용 방법

**제2스테이지에서의 활용**:
```python
# 중기-장기 간격이 줄어들지 않으면 매수 포지션 유지
if stage == 2:
    spread_20_40_current = spreads['Spread_20_40'].iloc[-1]
    spread_20_40_prev = spreads['Spread_20_40'].iloc[-2]
    
    if spread_20_40_current >= spread_20_40_prev:
        action = "매수 포지션 유지"
```

**제5스테이지에서의 활용**:
```python
# 중기-장기 간격이 줄어들지 않으면 매도 포지션 유지 (음수이므로 절댓값 비교)
if stage == 5:
    spread_20_40_current = spreads['Spread_20_40'].iloc[-1]
    spread_20_40_prev = spreads['Spread_20_40'].iloc[-2]
    
    if abs(spread_20_40_current) >= abs(spread_20_40_prev):
        action = "매도 포지션 유지"
```

---

## 2. check_ma_slope() 함수

### 구현 위치
- **파일**: `src/analysis/stage.py`
- **라인**: 함수 추가

### 함수 명세

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
    """
```

### 구현 특징

1. **Level 2 함수 재사용**
   - `calculate_slope()` 함수를 그대로 활용
   - 중복 코드 없이 깔끔한 구현
   - 일관된 기울기 계산 방법 유지

2. **기울기 해석**
   - 기울기 > 0: 우상향 (상승 추세)
   - 기울기 ≈ 0: 평행 (추세 전환 임박)
   - 기울기 < 0: 우하향 (하락 추세)

3. **커스터마이징 가능**
   - `period` 파라미터로 기울기 계산 기간 조정
   - 단기/장기 추세 선택적 확인 가능

### 활용 방법

**제2스테이지: 매수 포지션 유지 판단**:
```python
if stage == 2:
    slope_40 = slopes['Slope_EMA_40'].iloc[-1]
    
    if slope_40 > 0:
        action = "매수 포지션 유지"
        reason = "장기선이 여전히 상승 중"
    else:
        action = "포지션 청산 검토"
        reason = "장기선이 하락 전환"
```

**제6스테이지: 조기 매수 진입 판단**:
```python
if stage == 6:
    slope_5 = slopes['Slope_EMA_5'].iloc[-1]
    slope_20 = slopes['Slope_EMA_20'].iloc[-1]
    slope_40 = slopes['Slope_EMA_40'].iloc[-1]
    
    # 조기 매수 조건: 단기·중기 우상향, 장기 평행
    if slope_5 > 0 and slope_20 > 0 and abs(slope_40) < 0.1:
        action = "조기 매수 진입"
```

**3개선 방향 일치도 확인**:
```python
# 3개선 모두 우상향
all_uptrend = (slopes['Slope_EMA_5'] > 0) & \
              (slopes['Slope_EMA_20'] > 0) & \
              (slopes['Slope_EMA_40'] > 0)

# 3개선 모두 우하향
all_downtrend = (slopes['Slope_EMA_5'] < 0) & \
                (slopes['Slope_EMA_20'] < 0) & \
                (slopes['Slope_EMA_40'] < 0)
```

---

## 3. get_stage_strategy() 함수

### 구현 위치
- **파일**: `src/analysis/stage.py`
- **라인**: 함수 추가

### 함수 명세

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
            - stage: 스테이지 번호
            - name: 스테이지 이름
            - market_phase: 시장 국면
            - strategy: 권장 전략
            - action: 구체적 액션
            - position_size: 포지션 크기
            - risk_level: 리스크 레벨
            - description: 상세 설명
            - key_points: 핵심 포인트 리스트
            - macd_directions: MACD 방향 정보 (선택)
            - macd_alignment: MACD 일치도 (선택)
    """
```

### 구현 특징

1. **딕셔너리 기반 전략 매핑**
   - 스테이지 1~6 각각의 전략을 딕셔너리로 정의
   - 확장 가능하고 유지보수가 쉬운 구조
   - 전략 정보를 한눈에 파악 가능

2. **상세한 전략 정보 제공**
   - 시장 국면, 권장 전략, 구체적 액션
   - 포지션 크기, 리스크 레벨
   - 핵심 포인트 5개 (체크리스트)

3. **MACD 방향 일치도 분석 (선택)**
   - 3개 MACD의 방향 일치도 계산
   - 'strong': 3개 모두 같은 방향
   - 'weak': 방향이 섞여 있음

### 스테이지별 전략 요약

| 스테이지 | 이름 | 전략 | 액션 | 포지션 | 리스크 |
|---------|------|------|------|--------|--------|
| **1** | 안정 상승기 | 공격적 매수 | buy | 80-100% | low |
| **2** | 하락 변화기1 | 유지 판단 | hold/exit | 50-80% | medium |
| **3** | 하락 변화기2 | 청산/매도 | sell/short | 전량 청산 | high |
| **4** | 안정 하락기 | 매도/관망 | short/wait | 매도 또는 현금 | low |
| **5** | 상승 변화기1 | 유지 판단 | hold/exit | 50-80% | medium |
| **6** | 상승 변화기2 | 청산/매수 | cover/buy | 전량 청산 | high |

### 활용 방법

**기본 사용**:
```python
# 현재 스테이지 전략 조회
current_stage = df['Stage'].iloc[-1]
strategy = get_stage_strategy(current_stage)

print(f"현재: 제{strategy['stage']}스테이지 - {strategy['name']}")
print(f"시장 국면: {strategy['market_phase']}")
print(f"권장 전략: {strategy['strategy']}")
print(f"액션: {strategy['action']}")
print(f"포지션 크기: {strategy['position_size']}")
print(f"리스크: {strategy['risk_level']}")
```

**MACD 방향 포함**:
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
    if alignment['strength'] == 'strong':
        print("✅ 강한 신호 - 추세 확실")
    else:
        print("⚠️ 약한 신호 - 신중한 접근 필요")
```

**알림 시스템**:
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
        priority="high" if strategy['risk_level'] == 'high' else "normal"
    )
```

---

## 테스트 코드

### 테스트 파일
- **위치**: `src/tests/analysis/test_stage.py`

### 테스트 구성

#### TestCalculateMaSpread (6개 테스트)
1. `test_spread_calculation`: 간격 계산 정확성
2. `test_spread_positive_negative`: 양수/음수 케이스
3. `test_spread_change_tracking`: 간격 확대/축소 추적
4. `test_spread_with_nan`: NaN 처리
5. `test_spread_missing_columns`: 필수 컬럼 누락 에러
6. `test_spread_invalid_type`: 잘못된 타입 에러

#### TestCheckMaSlope (6개 테스트)
1. `test_slope_uptrend`: 우상향 기울기 판단
2. `test_slope_downtrend`: 우하향 기울기 판단
3. `test_slope_flat`: 평행 기울기 판단
4. `test_slope_custom_period`: 커스텀 period
5. `test_slope_invalid_period`: 잘못된 period 에러
6. `test_slope_missing_columns`: 필수 컬럼 누락 에러

#### TestGetStageStrategy (10개 테스트)
1. `test_strategy_stage_1`: 제1스테이지 전략
2. `test_strategy_stage_2`: 제2스테이지 전략
3. `test_strategy_stage_3`: 제3스테이지 전략
4. `test_strategy_stage_4`: 제4스테이지 전략
5. `test_strategy_stage_5`: 제5스테이지 전략
6. `test_strategy_stage_6`: 제6스테이지 전략
7. `test_strategy_with_macd_directions`: MACD 방향 포함
8. `test_strategy_with_weak_macd_alignment`: 약한 MACD 일치도
9. `test_strategy_invalid_stage_type`: 잘못된 스테이지 타입 에러
10. `test_strategy_invalid_stage_range`: 잘못된 스테이지 범위 에러

---

## 구현 통계

### 코드 라인 수
- `calculate_ma_spread()`: ~35줄
- `check_ma_slope()`: ~40줄
- `get_stage_strategy()`: ~170줄
- **총 구현 코드**: ~245줄

### 테스트 코드 라인 수
- `test_stage.py`: ~340줄

### 함수 복잡도
- `calculate_ma_spread()`: ⭐ (매우 쉬움)
- `check_ma_slope()`: ⭐ (쉬움, Level 2 재사용)
- `get_stage_strategy()`: ⭐⭐ (중간, 딕셔너리 매핑)

---

## Level 3 전체 완성도

### 구현 완료 함수 (7개)

**Level 3-1: 기초 함수**
1. ✅ `determine_ma_arrangement()` - 이동평균선 배열 판단
2. ✅ `detect_macd_zero_cross()` - MACD 제로라인 교차 감지

**Level 3-2: 핵심 함수**
3. ✅ `determine_stage()` - 현재 스테이지 판단
4. ✅ `detect_stage_transition()` - 스테이지 전환 감지

**Level 3-3: 보조 함수**
5. ✅ `calculate_ma_spread()` - 이동평균선 간격 계산
6. ✅ `check_ma_slope()` - 이동평균선 기울기 확인
7. ✅ `get_stage_strategy()` - 스테이지별 권장 전략

### 모듈 구조

```
src/analysis/
└── stage.py                    # 스테이지 분석 (7개 함수)

src/tests/
└── test_stage.py     # Level 3-3 테스트 (18개)

history/
└── 2025-11-14_stage_level3_3_implementation.md
```

---

## 핵심 설계 결정

### 1. 단순성 우선
- `calculate_ma_spread()`: 복잡한 계산 없이 단순 뺄셈
- 유지보수 용이, 디버깅 쉬움

### 2. 코드 재사용
- `check_ma_slope()`: Level 2의 `calculate_slope()` 재사용
- DRY 원칙 준수, 일관성 유지

### 3. 확장 가능한 구조
- `get_stage_strategy()`: 딕셔너리 기반 전략 매핑
- 새로운 전략 추가/수정 용이

### 4. 선택적 기능
- MACD 방향 정보는 optional parameter
- 기본 기능만으로도 충분히 작동
- 필요시 고급 분석 가능

---

## 향후 활용 계획

### 1. 백테스팅 시스템 통합
```python
# 스테이지별 수익률 분석
for stage in range(1, 7):
    stage_data = df[df['Stage'] == stage]
    strategy = get_stage_strategy(stage)
    
    returns = calculate_returns(stage_data)
    print(f"{strategy['name']}: 평균 수익률 {returns.mean():.2%}")
```

### 2. 실시간 모니터링
```python
# 간격 및 기울기 실시간 추적
spreads = calculate_ma_spread(latest_data)
slopes = check_ma_slope(latest_data)

# 위험 신호 감지
if spreads['Spread_20_40'].iloc[-1] < spreads['Spread_20_40'].iloc[-2]:
    alert("간격 축소 - 추세 약화 가능성")

if slopes['Slope_EMA_40'].iloc[-1] < 0:
    alert("장기선 하락 전환")
```

### 3. 자동 매매 시스템
```python
# 스테이지 기반 자동 매매
current_stage = df['Stage'].iloc[-1]
strategy = get_stage_strategy(current_stage)

if strategy['action'] == 'buy':
    execute_buy_order(size=strategy['position_size'])
elif strategy['action'] == 'sell_or_short':
    execute_sell_order(close_all=True)
```

---

## 학습 내용

### 1. 간격 지표의 중요성
- 이동평균선 간격은 추세 강도의 직접적 지표
- 간격 확대: 추세 가속
- 간격 축소: 추세 약화 또는 전환 임박

### 2. 기울기의 선행성
- 가격보다 이동평균선 기울기가 선행하는 경우 많음
- 장기선 기울기 변화는 중요한 추세 전환 신호

### 3. 전략의 체계화
- 각 스테이지마다 명확한 전략 정의 필요
- 리스크 레벨과 포지션 크기의 체계적 관리
- MACD 방향 일치도로 신호 강도 보완

---

## 다음 단계

Level 3 스테이지 분석 모듈이 완성되었습니다!

### 다음 단계 (Level 4)

Level 3 완료 후:
- **Level 4**: 매매 신호 생성 모듈 (`src/analysis/signal/`)
  - 진입 신호 생성 (통상/조기 매수/매도)
  - 청산 신호 생성 (3단계)
  - 신호 강도 평가
  - 신호 필터링

---

### 검증 작업
1. 실제 주식 데이터로 테스트
2. 각 스테이지별 수익률 분석
3. 간격/기울기 지표의 유효성 검증
4. 전략의 실전 적용 가능성 평가

---

## 참고사항

### 문서화
- [이동평균선 투자법 전략 정리](../Moving_Average_Investment_Strategy_Summary.md)
- [Level 2: 기술적 지표 모듈](./2025-11-13_technical_indicators_all.md)
- [Level 3: 스테이지 분석 계획](plan/2025-11-13_stage_analysis.md)
- [Level 3-3: 이동평균선 스테이지 보조함수](./plan/2025-11-14_stage_level3_3_plan.md)
---

## 작성자
- seunghakim
- AI Assistant (Claude)

## 검토 이력
- 2025-11-14: Level 3-3단계 구현 완료 ✅
  - calculate_ma_spread() 구현 ✅
  - check_ma_slope() 구현 ✅
  - get_stage_strategy() 구현 ✅
  - 테스트 22개 작성 ✅
  - 전체 테스트 22개 통과 ✅
  - 다음 단계 계획 수립 ✅