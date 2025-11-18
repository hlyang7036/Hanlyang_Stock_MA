# Level 6-1: 주문 실행 모듈 구현

## 날짜
2025-11-16

## 작업 개요
백테스팅 엔진의 Phase 1 작업으로 주문 실행 시뮬레이션 모듈을 구현했습니다.
Order와 ExecutionEngine 클래스를 통해 백테스팅 시 실제 거래와 유사한 체결가 계산,
슬리피지 및 수수료를 반영하여 현실적인 주문 실행을 시뮬레이션합니다.

---

## 구현 내용

### 1. Order 클래스 (src/backtest/execution.py)

**개요**: 주문 정보를 담는 데이터 클래스

**주요 속성**:
- `ticker`: 종목코드
- `action`: 'buy' (매수) 또는 'sell' (매도)
- `shares`: 주식 수
- `order_type`: 주문 유형 ('market' 또는 'limit')
- `limit_price`: 지정가 (limit 주문 시)
- `timestamp`: 주문 시각 (자동 설정)
- `position_type`: 포지션 유형 ('long' 또는 'short')
- `units`: 유닛 수
- `stop_price`: 손절가
- `signal_strength`: 신호 강도
- `reason`: 주문 사유

**검증 로직**:
- `action`은 'buy' 또는 'sell'만 허용
- `shares`는 양수여야 함
- `order_type`은 'market' 또는 'limit'만 허용
- limit 주문 시 `limit_price` 필수
- `position_type`은 'long' 또는 'short'만 허용
- timestamp가 없으면 현재 시각으로 자동 설정

---

### 2. ExecutionEngine 클래스 (src/backtest/execution.py)

**개요**: 주문 실행을 시뮬레이션하는 엔진

**주요 속성**:
- `commission_rate`: 수수료율 (기본값: 0.00015 = 0.015%)
- `slippage_pct`: 슬리피지 비율 (기본값: 0.001 = 0.1%)

**한국 증권사 수수료율 기준**:
- 온라인 거래 수수료: 약 0.015% (0.00015)
- 본 시스템은 한국투자증권 기준을 따름

**슬리피지 개념**:
- 시장가 주문 시 실제 체결가와 기대 가격의 차이
- 매수: 시장가보다 높게 체결 (불리)
- 매도: 시장가보다 낮게 체결 (불리)
- 기본값 0.1%는 보수적인 추정치

**주요 메서드**:

#### execute(order, market_price)
주문을 실행하고 체결 결과 반환

**반환값**:
```python
{
    'filled': bool,           # 체결 여부 (항상 True)
    'fill_price': float,      # 체결가 (슬리피지 포함)
    'shares': int,            # 체결 수량
    'commission': float,      # 수수료
    'total_cost': float,      # 총 비용(매수) 또는 총 수령액(매도)
    'slippage': float,        # 슬리피지 금액 (절대값)
    'ticker': str,            # 종목코드
    'action': str,            # 매수/매도
    'timestamp': datetime     # 체결 시각
}
```

**체결 로직**:
1. 체결가 계산 (슬리피지 반영)
2. 수수료 계산
3. 총 비용/수령액 계산
   - 매수: `체결가 × 수량 + 수수료`
   - 매도: `체결가 × 수량 - 수수료`
4. 슬리피지 금액 계산

#### calculate_fill_price(order, market_price)
슬리피지를 반영한 체결가 계산

**계산 공식**:
- 매수: `market_price × (1 + slippage_pct)`
- 매도: `market_price × (1 - slippage_pct)`

**예시**:
```python
# 매수 체결가
# 시장가: 50,000원, 슬리피지: 0.1%
# 체결가: 50,000 × 1.001 = 50,050원

# 매도 체결가
# 시장가: 50,000원, 슬리피지: 0.1%
# 체결가: 50,000 × 0.999 = 49,950원
```

#### calculate_commission(fill_price, shares)
수수료 계산

**계산 공식**:
```
수수료 = 체결가 × 주식 수 × 수수료율
```

**예시**:
```python
# 체결가: 50,000원, 수량: 100주, 수수료율: 0.015%
# 수수료 = 50,000 × 100 × 0.00015 = 750원
```

#### calculate_total_cost(fill_price, shares, commission, action)
총 비용 또는 총 수령액 계산

**계산 로직**:
- 매수: `주식 가격 + 수수료`
- 매도: `주식 가격 - 수수료`

#### get_config()
실행 엔진 설정 조회
- 수수료율과 슬리피지 비율 반환

#### update_config(commission_rate, slippage_pct)
실행 엔진 설정 업데이트
- 수수료율 또는 슬리피지 비율 변경
- 음수 값 검증
- 로깅: 변경 내역 기록

---

## 테스트 구현

### 테스트 파일
`src/tests/backtest/test_execution.py`

### 테스트 통계
- **총 테스트**: 30개
- **통과**: 30개 (100%)
- **실행 시간**: 0.03초

### 테스트 커버리지

#### TestOrder 클래스 (7개 테스트)
1. ✅ `test_order_creation_minimal`: 최소 필수 정보로 주문 생성
2. ✅ `test_order_creation_full`: 전체 정보로 주문 생성
3. ✅ `test_order_validation_action`: 잘못된 action 검증
4. ✅ `test_order_validation_shares`: 잘못된 shares 검증
5. ✅ `test_order_validation_order_type`: 잘못된 order_type 검증
6. ✅ `test_order_validation_limit_price`: limit 주문 시 limit_price 필수 검증
7. ✅ `test_order_validation_position_type`: 잘못된 position_type 검증

#### TestExecutionEngine 클래스 (23개 테스트)
1. ✅ `test_engine_creation_default`: 기본 설정으로 엔진 생성
2. ✅ `test_engine_creation_custom`: 사용자 정의 설정으로 엔진 생성
3. ✅ `test_engine_validation_commission_rate`: 음수 수수료율 검증
4. ✅ `test_engine_validation_slippage_pct`: 음수 슬리피지 비율 검증
5. ✅ `test_calculate_fill_price_buy`: 매수 시 체결가 계산
6. ✅ `test_calculate_fill_price_sell`: 매도 시 체결가 계산
7. ✅ `test_calculate_fill_price_no_slippage`: 슬리피지 0일 때 체결가
8. ✅ `test_calculate_commission`: 수수료 계산
9. ✅ `test_calculate_commission_large_amount`: 대금액 거래 수수료 계산
10. ✅ `test_calculate_total_cost_buy`: 매수 총 비용 계산
11. ✅ `test_calculate_total_cost_sell`: 매도 총 수령액 계산
12. ✅ `test_execute_buy_order`: 매수 주문 실행
13. ✅ `test_execute_sell_order`: 매도 주문 실행
14. ✅ `test_execute_invalid_market_price`: 잘못된 시장가로 주문 실행 시도
15. ✅ `test_execute_large_order`: 대량 주문 실행
16. ✅ `test_execute_with_no_slippage_and_commission`: 슬리피지와 수수료 0일 때
17. ✅ `test_get_config`: 설정 조회
18. ✅ `test_update_config_commission_rate`: 수수료율 업데이트
19. ✅ `test_update_config_slippage_pct`: 슬리피지 비율 업데이트
20. ✅ `test_update_config_both`: 수수료율과 슬리피지 모두 업데이트
21. ✅ `test_update_config_invalid_commission_rate`: 잘못된 수수료율로 업데이트 시도
22. ✅ `test_update_config_invalid_slippage_pct`: 잘못된 슬리피지 비율로 업데이트 시도
23. ✅ `test_realistic_scenario`: 현실적인 시나리오 (삼성전자 100주 매수)

### 주요 테스트 시나리오

**매수 주문 실행 테스트**:
```python
# 주문: 삼성전자 100주 매수
# 시장가: 50,000원
# 슬리피지: 0.1%
# 수수료율: 0.015%

# 체결가 = 50,000 × 1.001 = 50,050원
# 주식 가격 = 50,050 × 100 = 5,005,000원
# 수수료 = 5,005,000 × 0.00015 = 750.75원
# 총 비용 = 5,005,000 + 750.75 = 5,005,750.75원
# 슬리피지 금액 = 50 × 100 = 5,000원
```

**매도 주문 실행 테스트**:
```python
# 주문: 삼성전자 100주 매도
# 시장가: 50,000원
# 슬리피지: 0.1%
# 수수료율: 0.015%

# 체결가 = 50,000 × 0.999 = 49,950원
# 주식 가격 = 49,950 × 100 = 4,995,000원
# 수수료 = 4,995,000 × 0.00015 = 749.25원
# 총 수령액 = 4,995,000 - 749.25 = 4,994,250.75원
# 슬리피지 금액 = 50 × 100 = 5,000원
```

**대량 주문 테스트**:
```python
# 주문: 삼성전자 10,000주 매수
# 시장가: 50,000원

# 체결가 = 50,050원
# 수수료 = 50,050 × 10,000 × 0.00015 = 75,075원
# 총 비용 = 500,500,000 + 75,075 = 500,575,075원
```

**슬리피지와 수수료 없는 이상적 상황**:
```python
# 슬리피지: 0%
# 수수료율: 0%

# 체결가 = 시장가 (50,000원)
# 수수료 = 0원
# 총 비용 = 5,000,000원
# 슬리피지 금액 = 0원
```

---

## 기술적 특징

### 1. 현실적인 거래 비용 시뮬레이션

**슬리피지 반영**:
- 매수/매도 방향에 따라 불리하게 적용
- 시장 충격(market impact) 효과 반영
- 기본값 0.1%는 보수적 추정

**수수료 반영**:
- 한국 증권사 기준 수수료율
- 매수/매도 모두 동일하게 적용
- 거래 금액에 비례한 정확한 계산

### 2. 유연한 설정 관리

**초기 설정**:
- 수수료율과 슬리피지를 생성 시 지정 가능
- 기본값은 한국 시장 기준

**동적 업데이트**:
- `update_config()` 메서드로 런타임 변경 가능
- 부분 업데이트 지원 (한 가지만 변경 가능)
- 변경 내역 자동 로깅

### 3. 상세한 체결 정보 제공

**반환 정보**:
- 체결가, 수량, 수수료, 총 비용
- 슬리피지 금액 (추후 분석용)
- 종목코드, 액션, 타임스탬프

**로깅**:
- DEBUG 레벨: 체결 상세 정보
- INFO 레벨: 엔진 초기화 정보
- 슬리피지와 수수료 명시

### 4. 강력한 입력 검증

**Order 클래스 검증**:
- action, shares, order_type, position_type 검증
- limit 주문 시 limit_price 필수 확인
- timestamp 자동 설정

**ExecutionEngine 검증**:
- 수수료율과 슬리피지는 0 이상이어야 함
- 시장가는 양수여야 함
- 명확한 에러 메시지 제공

### 5. 부동 소수점 처리

**테스트에서의 처리**:
- 부동 소수점 오차를 고려한 tolerance 기반 비교
- `abs(value - expected) < tolerance` 패턴 사용
- 금액 계산: ±1원 tolerance
- 비율 계산: ±0.01 tolerance

---

## 의존성

### 표준 라이브러리
- `dataclasses`: Order 클래스 구현
- `datetime`: 타임스탬프 처리
- `typing`: 타입 힌팅 (Optional, Dict, Any)
- `logging`: 로깅

### 외부 라이브러리
- 없음 (순수 Python 구현)

---

## 파일 구조

```
src/backtest/
├── __init__.py
├── portfolio.py              # Level 6-1 portfolio 작업에서 생성
└── execution.py              # 이번 작업에서 생성

src/tests/backtest/
├── __init__.py
├── test_portfolio.py         # Level 6-1 portfolio 작업에서 생성
└── test_execution.py         # 이번 작업에서 생성
```

---

## 코드 품질

### Type Hints
- ✅ 모든 함수에 타입 힌팅 적용
- ✅ Optional, Dict, Any 등 타입 명시

### Docstrings
- ✅ 모든 클래스와 메서드에 docstring
- ✅ Args, Returns, Notes, Examples 섹션 포함
- ✅ 계산 공식과 예시 코드 제공

### 테스트 커버리지
- ✅ 100% 통과율 (30/30)
- ✅ 정상 케이스 + 예외 케이스 모두 커버
- ✅ 경계값 테스트 (0, 음수, 대량 주문)
- ✅ 현실적 시나리오 테스트

### 로깅
- ✅ INFO 레벨: 엔진 초기화, 설정 업데이트
- ✅ DEBUG 레벨: 주문 체결 상세 정보
- ✅ 수수료와 슬리피지 명시

---

## Portfolio 모듈과의 통합

### 연동 방식

**주문 생성 → 실행 → 포트폴리오 업데이트** 흐름:

```python
# 1. 주문 생성
order = Order(
    ticker='005930',
    action='buy',
    shares=100
)

# 2. 주문 실행
execution_engine = ExecutionEngine()
result = execution_engine.execute(order, market_price=50000)

# 3. 포트폴리오 업데이트 (매수)
if result['filled']:
    position = Position(
        ticker=result['ticker'],
        position_type='long',
        entry_date=result['timestamp'],
        entry_price=result['fill_price'],
        shares=result['shares']
    )
    portfolio.add_position(position, result['total_cost'])

# 4. 포트폴리오 업데이트 (매도)
if result['filled'] and result['action'] == 'sell':
    close_result = portfolio.close_position(
        ticker=result['ticker'],
        exit_price=result['fill_price'],
        shares=result['shares']
    )
```

### 핵심 연동 포인트

1. **ExecutionEngine.execute() → Portfolio.add_position()**
   - 체결가(`fill_price`)가 포지션의 진입가(`entry_price`)로 사용
   - 총 비용(`total_cost`)이 포트폴리오 현금에서 차감

2. **ExecutionEngine.execute() → Portfolio.close_position()**
   - 체결가(`fill_price`)가 청산가(`exit_price`)로 사용
   - 총 수령액(`total_cost`)이 포트폴리오 현금으로 회수
   - 수수료는 이미 `total_cost`에 반영되어 있음

3. **수수료 처리의 일관성**
   - ExecutionEngine: 수수료를 `total_cost`에 포함
   - Portfolio: 청산 시 추가로 수수료 차감
   - **주의**: 백테스팅 엔진에서는 이중 차감 방지 필요
     - 해결: Portfolio.close_position()에서 수수료 0으로 호출
     - 또는 ExecutionEngine의 `total_cost`를 그대로 사용

---

## 테스트 중 발견된 이슈 및 해결

### 이슈 1: 부동 소수점 정밀도 오류

**문제**:
```python
# 예상: 4.0
# 실제: 4.0000000000000036
assert result['return_pct'] == 4.0  # 실패
```

**원인**: 부동 소수점 연산의 정밀도 한계

**해결**:
```python
# tolerance 기반 비교로 변경
assert abs(result['return_pct'] - 4.0) < 0.01
```

### 이슈 2: 수수료 계산 공식 오해

**문제**:
```python
# 잘못된 기대값: 7.5원
# 올바른 값: 750원
# 50,000 × 100 × 0.00015 = 750원
```

**원인**: 테스트 작성 시 수수료 계산 공식 오해

**해결**: 기대값을 올바른 값(750원)으로 수정

### 이슈 3: 슬리피지 금액 계산 정밀도

**문제**:
```python
# 예상: 5,000원
# 실제: 4,999.999999999272원
assert result['slippage'] == 5000.0  # 실패
```

**해결**:
```python
assert abs(result['slippage'] - 5000.0) < 0.01
```

---

## 다음 단계

### Phase 1 완료
- ✅ `portfolio.py`: 포트폴리오 관리
- ✅ `execution.py`: 주문 실행 시뮬레이션

### Phase 2 예정
- `data_manager.py`: 전체 시장 데이터 관리
  - 전체 종목 코드 조회 (KOSPI + KOSDAQ)
  - 병렬 데이터 로딩 (ThreadPoolExecutor)
  - 데이터 캐싱
  - 진행 상황 표시 (tqdm)

### Phase 3 예정
- `backtest_engine.py`: 백테스팅 메인 엔진
  - 일별 시뮬레이션 루프
  - 신호 생성 및 필터링
  - 리스크 관리 적용
  - 주문 생성 및 실행
  - 손절 체크 및 포지션 청산
  - 성과 기록

---

## 참고 사항

### 설계 원칙
- 계획 문서(`history/plan/2025-11-16_level6_backtest_engine_plan.md`)의 명세를 충실히 따름
- 한국 증권 시장 특성 반영 (수수료율, 거래 방식)
- 테스트 주도 개발 (모든 기능 테스트 커버)

### 백테스팅 특징
- 보수적인 슬리피지 적용 (0.1%)
- 실제 수수료율 반영 (0.015%)
- 시장가 주문만 지원 (limit 주문은 향후 확장 가능)
- 체결 실패 없음 (유동성 무제한 가정)

### 향후 확장 가능성
- 지정가 주문 체결 로직 구현
- 시장 충격 모델 정교화 (대량 주문 시 슬리피지 증가)
- 시간대별 슬리피지 차등 적용 (개장/마감 시 증가)
- 부분 체결 시뮬레이션

---

## 작성자
- seunghakim
- AI Assistant (Claude)

## 작성 일자
2025-11-16
