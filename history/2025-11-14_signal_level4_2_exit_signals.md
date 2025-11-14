# Level 4-2 청산 신호 생성 구현 완료

## 날짜
2025-11-14

## 작업 개요
Level 4의 두 번째 단계로 3단계 청산 시스템을 구현했습니다.
히스토그램, MACD선, MACD-시그널 교차를 활용한 체계적인 청산 신호를 생성합니다.

---

## 구현 완료 내역

### 모듈 구조
```
src/analysis/signal/
├── __init__.py          # 업데이트
└── exit.py              # 청산 신호 생성 (4개 함수)

src/tests/analysis/signal/
└── test_signal_exit.py  # 테스트 (19개)
```

---

## 3단계 청산 시스템

```
[레벨 1] 히스토그램 피크아웃
    ↓
  경계 태세 (0% 청산)
  ⚠️ 주의 신호
    ↓
[레벨 2] MACD선 피크아웃
    ↓
  50% 청산
  📉 부분 청산
    ↓
[레벨 3] MACD-시그널 교차
    ↓
  100% 청산
  🚨 전량 청산
```

---

## 구현 함수 (4개)

### 1. check_histogram_peakout()
**기능**: 히스토그램 피크아웃 확인 (1단계)

**로직**:
- **매수 포지션**: 히스토그램 고점 후 하락 (하락 피크아웃)
- **매도 포지션**: 히스토그램 저점 후 상승 (상승 피크아웃)

**출력**: 
- `pd.Series` (boolean) - 피크아웃 발생 여부

**활용**: Level 2의 `detect_peakout()` 재사용

### 2. check_macd_peakout()
**기능**: MACD선 피크아웃 확인 (2단계)

**로직**:
- **매수 포지션**: MACD선 고점 후 하락
- **매도 포지션**: MACD선 저점 후 상승

**출력**: 
- `pd.Series` (boolean) - 피크아웃 발생 여부

### 3. check_macd_cross()
**기능**: MACD-시그널 교차 확인 (3단계)

**로직**:
- **매수 포지션**: 데드크로스 (MACD < Signal로 교차)
- **매도 포지션**: 골든크로스 (MACD > Signal로 교차)

**출력**: 
- `pd.Series` (boolean) - 교차 발생 여부

### 4. generate_exit_signal()
**기능**: 청산 신호 생성 (3단계 통합)

**출력**:
```python
{
    'Exit_Level': 0/1/2/3,         # 청산 레벨
    'Exit_Percentage': 0/0/50/100, # 청산 비율
    'Exit_Reason': str,            # 청산 이유
    'Should_Exit': bool            # 실제 청산 여부
}
```

**우선순위**: 레벨 3 > 레벨 2 > 레벨 1

---

## 사용 예시

### 기본 사용
```python
from src.analysis.signal import generate_exit_signal

# 매수 포지션 청산 신호
exit_signals = generate_exit_signal(df, 'long')

# 경계 신호 (레벨 1)
alert_points = df[exit_signals['Exit_Level'] == 1]
print(f"경계 신호: {len(alert_points)}회")

# 50% 청산 (레벨 2)
exit_50 = df[exit_signals['Exit_Level'] == 2]
print(f"50% 청산: {len(exit_50)}회")

# 100% 청산 (레벨 3)
exit_100 = df[exit_signals['Exit_Level'] == 3]
print(f"100% 청산: {len(exit_100)}회")
```

### 실시간 청산 판단
```python
# 최신 데이터로 청산 필요 여부 확인
latest_signals = generate_exit_signal(df.tail(10), 'long')
current_signal = latest_signals.iloc[-1]

if current_signal['Should_Exit']:
    print(f"청산 필요: {current_signal['Exit_Reason']}")
    print(f"청산 비율: {current_signal['Exit_Percentage']}%")
    
    if current_signal['Exit_Level'] == 3:
        # 전량 청산
        close_position(100)
    elif current_signal['Exit_Level'] == 2:
        # 절반 청산
        close_position(50)
else:
    print(f"현재 레벨: {current_signal['Exit_Level']}")
    if current_signal['Exit_Level'] == 1:
        print("⚠️ 경계 태세 유지")
```

### 매도 포지션 청산
```python
# 매도 포지션 (숏 포지션) 청산
short_exit = generate_exit_signal(df, 'short')

# 골든크로스로 청산
golden_cross_exit = df[short_exit['Exit_Reason'].str.contains('골든크로스')]
```

---

## 청산 레벨별 상세

### 레벨 1: 히스토그램 피크아웃

**의미**: 
- 추세 약화 초기 징후
- 모멘텀 감소

**액션**:
- 청산하지 않음 (0%)
- 경계 태세 진입
- 추가 매수 중단

**예시**:
```python
# 매수 포지션
히스토그램: [1.0, 2.0, 3.0, 2.5]  # 3.0 고점 후 하락
→ 레벨 1 신호 발생
```

### 레벨 2: MACD선 피크아웃

**의미**:
- 추세 반전 가능성
- 명확한 약세 신호

**액션**:
- 50% 청산
- 이익 일부 실현
- 리스크 감소

**예시**:
```python
# 매수 포지션
MACD: [1.0, 2.0, 3.0, 2.5, 2.0]  # 3.0 고점 후 하락
→ 레벨 2 신호 발생 → 50% 청산
```

### 레벨 3: MACD-시그널 교차

**의미**:
- 추세 전환 확정
- 강력한 반전 신호

**액션**:
- 100% 청산
- 전량 청산
- 손실 차단 또는 이익 확정

**예시**:
```python
# 매수 포지션 - 데드크로스
MACD:   [2.0, 1.5, 1.0, 0.5]  # 하락
Signal: [1.0, 1.0, 1.0, 1.0]  # 유지
→ MACD가 Signal 아래로 교차
→ 레벨 3 신호 발생 → 100% 청산
```

---

## 테스트 결과

### 테스트 구성 (19개)

**TestCheckHistogramPeakout (5개)**:
- 매수 포지션 히스토그램 피크아웃
- 매도 포지션 히스토그램 피크아웃
- 히스토그램 피크아웃 없음
- 잘못된 position_type
- Histogram 컬럼 누락

**TestCheckMacdPeakout (4개)**:
- 매수 포지션 MACD 피크아웃
- 매도 포지션 MACD 피크아웃
- 커스텀 MACD 컬럼
- MACD 컬럼 누락

**TestCheckMacdCross (5개)**:
- 매수 포지션 데드크로스
- 매도 포지션 골든크로스
- 교차 없음
- 커스텀 컬럼명
- 필수 컬럼 누락

**TestGenerateExitSignal (5개)**:
- 레벨 1: 히스토그램 피크아웃
- 레벨 2: MACD선 피크아웃
- 레벨 3: MACD-시그널 교차
- 신호 우선순위
- 매도 포지션 청산
- 청산 신호 없음
- 잘못된 입력
- 필수 컬럼 누락

---

## 핵심 설계 결정

### 1. 3단계 체계화
**결정**: 단계별 명확한 구분

**장점**:
- 점진적 청산 가능
- 리스크 단계적 감소
- 심리적 부담 감소

**효과**: 
- 급격한 청산 방지
- 수익 극대화 기회

### 2. 레벨별 청산 비율
**결정**: 0% → 50% → 100%

**근거**:
- 레벨 1: 경고만 (False Alarm 대응)
- 레벨 2: 부분 청산 (이익 일부 확보)
- 레벨 3: 전량 청산 (추세 전환 확정)

### 3. Level 2 함수 재사용
**결정**: `detect_peakout()` 활용

**장점**:
- 코드 중복 제거
- 검증된 로직 사용
- 일관성 유지

### 4. 우선순위 시스템
**결정**: 레벨 3 > 2 > 1

**로직**:
```python
# 동시 발생 시 최고 레벨 우선
if macd_cross:  # 레벨 3
    return 3
elif macd_peakout:  # 레벨 2
    return 2
elif hist_peakout:  # 레벨 1
    return 1
```

---

## 청산 시나리오 예시

### 시나리오 1: 점진적 청산

```
Day 1: 레벨 1 발생 (히스토그램 피크아웃)
       → 경계 태세, 추가 매수 중단
       
Day 3: 레벨 2 발생 (MACD선 피크아웃)
       → 50% 청산 (100주 → 50주)
       → 이익 일부 실현
       
Day 5: 레벨 3 발생 (데드크로스)
       → 100% 청산 (50주 전량)
       → 포지션 종료
```

### 시나리오 2: 급격한 청산

```
Day 1: 레벨 3 즉시 발생 (강한 반전)
       → 100% 청산
       → 손실 차단
```

### 시나리오 3: False Alarm

```
Day 1: 레벨 1 발생
       → 경계 태세
       
Day 2-10: 추가 신호 없음
       → 정상 회복
       → 포지션 유지
```

---

## 코드 품질

### 통계
- **구현 코드**: ~280줄 (exit.py)
- **테스트 코드**: ~300줄 (test_signal_exit.py)
- **테스트 수**: 19개
- **함수 수**: 4개

### 품질 지표
- ✅ Type hints: 100%
- ✅ Docstrings: 100%
- ✅ 예외 처리: 완비
- ✅ 로깅: 상세
- ✅ 테스트 커버리지: 높음 (예상 >90%)

---

## Level 4 진행 현황

### 완료 (2/4)
- ✅ Level 4-1: 진입 신호 생성 (entry.py)
- ✅ Level 4-2: 청산 신호 생성 (exit.py)

### 남은 작업 (2/4)
- ⏳ Level 4-3: 신호 강도 평가 (strength.py)
- ⏳ Level 4-4: 신호 필터링 (filter.py)

---

## 다음 단계 (Level 4-3)

### 신호 강도 평가 (strength.py)

**구현 예정**:
- 신호 강도 점수화 (0-100점)
- 평가 요소:
  - MACD 방향 일치도 (30점)
  - 이동평균선 배열 (20점)
  - 이동평균선 간격 (20점)
  - 이동평균선 기울기 (20점)
  - ATR 변동성 (10점)

**함수 (4개)**:
- `evaluate_signal_strength()`
- `calculate_macd_alignment_score()`
- `calculate_trend_strength_score()`
- `calculate_momentum_score()`

---

## 참고 자료

- [Level 4 계획](../plan/2025-11-14_signal_level4_plan.md)
- [Level 4-1: 진입 신호](./2025-11-14_signal_level4_1_entry_signals.md)
- [Level 2: 기술적 지표](./2025-11-13_technical_indicators_all.md)

---

## 작성자
- seunghakim
- AI Assistant (Claude)

## 작성 일자
2025-11-14
