# Level 5-3: 포트폴리오 제한 모듈 구현

## 날짜
2025-11-16

## 작업 개요
Level 5-3 포트폴리오 제한 모듈을 구현했습니다. 4단계 계층적 제한 구조를 통해 포트폴리오의 집중 리스크를 방지하는 시스템을 완성했습니다.

---

## 구현 내용

### 1. 모듈 구현 (`src/analysis/risk/portfolio.py`)

#### 구현된 함수 (5개)

**1. check_single_position_limit()**
- 단일 종목 포지션 제한 체크
- 기본 한도: 4유닛
- 한 종목의 급락 시 피해 최소화

**2. check_correlated_group_limit()**
- 상관관계 그룹 제한 체크
- 기본 한도: 6유닛 (그룹 합계)
- 같은 섹터 종목들의 동반 하락 방지
- 종목이 여러 그룹에 속할 경우 가장 제한적인 것 적용

**3. check_diversified_limit()**
- 분산 투자 제한 체크
- 기본 한도: 10유닛 (서로 다른 섹터)
- 과도한 분산으로 인한 관리 어려움 방지
- 그룹별 합계 + 미분류 종목 합계

**4. check_total_exposure_limit()**
- 전체 포트폴리오 노출 제한 체크
- 기본 한도: 12유닛
- 계좌의 12% 이상 리스크 노출 금지
- 모든 제한 중 최종 안전장치

**5. get_available_position_size()**
- 실제 추가 가능한 포지션 크기 계산
- 위 4가지 제한을 모두 종합
- 가장 제한적인 조건의 허용 유닛 반환
- 제한 요인 식별 ('single', 'correlated', 'diversified', 'total', 'none')

---

### 2. 테스트 구현 (`src/tests/analysis/risk/test_portfolio.py`)

#### 테스트 클래스 (6개)

**1. TestCheckSinglePositionLimit (14개 테스트)**
- 한도 내/초과 케이스
- 경계값 테스트
- 에러 케이스
- 사용자 정의 한도

**2. TestCheckCorrelatedGroupLimit (10개 테스트)**
- 그룹 한도 체크
- 그룹에 속하지 않은 종목
- 여러 그룹 처리
- 종목이 여러 그룹에 속하는 경우

**3. TestCheckDiversifiedLimit (5개 테스트)**
- 분산 투자 한도 체크
- 그룹별 합계 + 미분류 종목
- 빈 상관관계 그룹 처리

**4. TestCheckTotalExposureLimit (6개 테스트)**
- 전체 한도 체크
- 빈 포지션 케이스
- 최대 용량 도달

**5. TestGetAvailablePositionSize (13개 테스트)**
- 모든 제한 통합 테스트
- 각 제한별 제한 요인 확인
- 사용자 정의 제한
- 신규 종목 진입
- 여러 제한 동시 적용

**6. TestIntegration (5개 테스트)**
- 현실적인 포트폴리오 시나리오
- 점진적 포지션 구축
- 그룹 제한 - 여러 종목
- 최대 포트폴리오 용량
- 빈 포트폴리오 → 가득 찬 포트폴리오

**총 테스트 수: 53개**

---

## 주요 설계 결정

### 1. 4단계 계층적 제한 구조

```
단일 종목 (4유닛)
    ↓
상관관계 그룹 (6유닛)
    ↓
분산 투자 (10유닛)
    ↓
전체 포트폴리오 (12유닛)
```

**결정 이유**:
- 점진적인 리스크 제어
- 집중 리스크와 과도한 분산 모두 방지
- 유연한 설정 가능 (사용자 정의 한도)

### 2. 가장 제한적인 조건 적용

`get_available_position_size()` 함수는 모든 제한을 체크한 후 가장 작은 허용 유닛을 반환합니다.

**예시**:
```python
# 단일 종목: 2유닛 가능
# 상관관계 그룹: 1유닛 가능
# 분산 투자: 3유닛 가능
# 전체 노출: 4유닛 가능
→ 최종 허용: 1유닛 (가장 제한적)
```

**결정 이유**:
- 보수적인 리스크 관리
- 모든 제한 준수 보장
- 명확한 제한 요인 식별

### 3. 유연한 상관관계 그룹 정의

종목이 여러 그룹에 속할 수 있도록 설계했습니다.

**예시**:
```python
correlation_groups = {
    '반도체': ['005930', '000660'],
    '대형주': ['005930', '005380'],  # 삼성전자가 두 그룹에 속함
}
```

**처리 방식**:
- 모든 해당 그룹 체크
- 가장 제한적인 그룹 적용

**결정 이유**:
- 다차원적 리스크 관리
- 실제 시장의 복잡한 상관관계 반영

### 4. 그룹에 속하지 않은 종목 처리

상관관계 그룹에 속하지 않은 종목은:
- `check_correlated_group_limit()`: 통과
- `check_diversified_limit()`: 미분류로 계산

**결정 이유**:
- 새로운 섹터 진입 가능
- 점진적인 그룹 정의 허용
- 유연성 제공

### 5. NumPy 타입 지원

`numbers.Number`를 사용하여 NumPy 타입을 포함한 모든 숫자 타입을 허용합니다.

**결정 이유**:
- Level 5-2 (stop_loss.py)와 일관성
- Pandas/NumPy 기반 시스템과의 호환성
- 타입 변환 오버헤드 제거

---

## 구현 세부사항

### 1. 반환 딕셔너리 구조

모든 체크 함수는 일관된 구조의 딕셔너리를 반환합니다:

```python
{
    'allowed': bool,           # 허용 여부
    'available_units': int,    # 추가 가능 유닛
    'limit': int,              # 최대 한도
    'reason': str              # 거부 사유 (불허 시)
}
```

추가 필드 (함수별로 다름):
- `check_single_position_limit`: `current_units`
- `check_correlated_group_limit`: `group_name`, `group_total`
- `check_diversified_limit`: `diversified_total`
- `check_total_exposure_limit`: `total_units`

### 2. 입력 검증

모든 함수는 3단계 검증을 수행합니다:

1. **타입 검증**: `isinstance()` + `numbers.Number`
2. **값 검증**: 음수, 0, 범위 체크
3. **정수 변환**: `int()` 변환

### 3. 로깅 전략

```python
# 디버그: 체크 시작
logger.debug("단일 종목 제한 체크: 현재=3유닛, 추가=2유닛")

# 성공: 통과
logger.debug("✅ 단일 종목 제한 통과: 5유닛 <= 4유닛")

# 경고: 거부
logger.warning("❌ 단일 종목 제한 초과: 5유닛 > 4유닛")

# 정보: 최종 결과
logger.info("✅ 포지션 전체 허용: 종목=005930, 허용=2유닛")
```

---

## 테스트 결과

### 테스트 커버리지

```
함수별 테스트 수:
- check_single_position_limit:     14개
- check_correlated_group_limit:    10개
- check_diversified_limit:          5개
- check_total_exposure_limit:       6개
- get_available_position_size:     13개
- 통합 테스트:                      5개

총 53개 테스트
```

### 테스트 명령어

```bash
# 전체 테스트
python -m pytest src/tests/analysis/risk/test_portfolio.py -v

# 특정 클래스만
python -m pytest src/tests/analysis/risk/test_portfolio.py::TestGetAvailablePositionSize -v

# 통합 테스트만
python -m pytest src/tests/analysis/risk/test_portfolio.py::TestIntegration -v

# 커버리지 포함
python -m pytest src/tests/analysis/risk/test_portfolio.py --cov=src/analysis/risk/portfolio -v
```

### 주요 테스트 시나리오

#### 1. 점진적 포지션 구축

```python
# 빈 포트폴리오 시작
positions = {}

# 1차: 삼성전자 2유닛 → 허용
positions['005930'] = 2

# 2차: 삼성전자 2유닛 추가 → 허용 (총 4유닛)
positions['005930'] = 4

# 3차: 삼성전자 1유닛 추가 시도 → 거부 (단일 종목 제한)
```

#### 2. 그룹 제한 테스트

```python
positions = {
    '005930': 3,  # 삼성전자
    '000660': 2,  # SK하이닉스
}
groups = {
    '반도체': ['005930', '000660']
}

# 삼성전자 2유닛 추가 시도
# 단일: 4 - 3 = 1 가능
# 그룹: 6 - 5 = 1 가능
# 결과: 1유닛만 허용 (그룹 제한)
```

#### 3. 최대 포트폴리오 용량

```python
positions = {
    '005930': 4,
    '000660': 3,
    '005380': 4,
    '051910': 1
}
# 총 12유닛 → 추가 불가 (전체 제한)
```

---

## 주요 학습 내용

### 1. 다층 제한 구조의 효과

4단계 제한 구조는:
- **단일 종목**: 특정 종목 급락 방지
- **상관관계 그룹**: 섹터별 위기 대응
- **분산 투자**: 과도한 분산 방지
- **전체 노출**: 절대 한도 설정

각 레벨이 서로 다른 리스크를 관리합니다.

### 2. 그룹 기반 리스크 관리

상관관계 그룹을 사용하면:
- 섹터별 노출 제어 가능
- 동일 산업군 집중 방지
- 포트폴리오 다각화 강제

### 3. 실제 사용 시나리오

```python
# 매매 신호 발생
signal = {
    'ticker': '005930',
    'action': 'buy',
    'desired_units': 2
}

# 포지션 크기 계산
result = get_available_position_size(
    ticker=signal['ticker'],
    desired_units=signal['desired_units'],
    positions=current_positions,
    correlation_groups=groups
)

# 실제 주문 크기 결정
if result['allowed_units'] > 0:
    order_units = result['allowed_units']
    logger.info(f"주문 실행: {order_units}유닛")
else:
    logger.warning(f"주문 거부: {result['limiting_factor']}")
```

---

## 개선 가능 사항

### 1. 동적 상관관계 계산

현재는 정적 그룹 정의를 사용하지만, 향후:
- 실시간 상관계수 계산
- 자동 그룹 재조정
- 시장 상황에 따른 동적 한도 조정

### 2. 한도 최적화

현재 한도 (4, 6, 10, 12)는 터틀 트레이딩 기반이지만:
- 백테스팅을 통한 최적 한도 탐색
- 계좌 크기별 차등 한도
- 변동성별 동적 조정

### 3. 리스크 지표 추가

포지션 크기뿐만 아니라:
- VaR (Value at Risk) 계산
- 예상 최대 손실 (MDD)
- 섹터별 리스크 비중

---

## 다음 단계

### Level 5-4: 리스크 노출 관리 (exposure.py)

**예상 구현 내용**:
```python
# 1. calculate_position_risk()
# 개별 포지션의 리스크 계산
# 리스크 = 포지션 크기 × (진입가 - 손절가)

# 2. calculate_total_portfolio_risk()
# 전체 포트폴리오 리스크 합산
# 종목별 리스크 + 상관관계 고려

# 3. check_risk_limits()
# 리스크 한도 체크
# 총 리스크 <= 계좌의 2%

# 4. generate_risk_report()
# 포괄적 리스크 리포트
# 대시보드/알림 시스템에서 활용
```

**예상 시간**: 3-4시간  
**예상 테스트**: ~12개

### Level 5 통합

Level 5-4 완료 후:
1. `__init__.py` 통합 함수 구현
2. 전체 리스크 관리 파이프라인 테스트
3. Level 4 신호 생성과 통합
4. 문서화 완료

---

## 파일 구조

```
src/analysis/risk/
├── __init__.py              # (미구현)
├── position_sizing.py       # Level 5-1 (미구현)
├── stop_loss.py             # Level 5-2 (완료)
├── portfolio.py             # Level 5-3 (완료) ✅
└── exposure.py              # Level 5-4 (미구현)

src/tests/analysis/risk/
├── test_position_sizing.py  # (미구현)
├── test_stop_loss.py        # (완료)
├── test_portfolio.py        # (완료) ✅
└── test_exposure.py         # (미구현)

history/
├── 2025-11-14_risk_level5_plan.md
├── 2025-11-16_level5-2_stop_loss_implementation.md
└── 2025-11-16_level5-3_portfolio_implementation.md  # (신규) ✅
```

---

## 참고 자료

- [Level 5 계획](../plan/2025-11-14_risk_level5_plan.md)
- [Level 5-2: 손절 관리 구현](./2025-11-16_level5-2_stop_loss_implementation.md)
- [터틀 트레이딩 포지션 관리](https://www.turtletrader.com/)

---

## 체크리스트

- [x] portfolio.py 구현 (5개 함수)
- [x] test_portfolio.py 구현 (53개 테스트)
- [x] Type hints 100%
- [x] Docstrings 100%
- [x] 입력 검증 완료
- [x] 로깅 추가
- [x] NumPy 타입 지원
- [x] 개발 문서 작성
- [ ] 테스트 실행 및 확인 (사용자)
- [ ] Level 5-4 구현 준비

---

## 작성자
- seunghakim
- AI Assistant (Claude)

## 작성 일자
2025-11-16

---

## 변경 이력

| 날짜 | 버전 | 변경 내용 | 작성자 |
|------|------|-----------|--------|
| 2025-11-16 | 1.0 | 최초 작성 | seunghakim, Claude |
