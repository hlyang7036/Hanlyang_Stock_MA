# Level 6-1: 포트폴리오 관리 모듈 구현

## 날짜
2025-11-16

## 작업 개요
백테스팅 엔진의 Phase 1 작업으로 포트폴리오 관리 모듈을 구현했습니다.
Position과 Portfolio 클래스를 통해 백테스팅 시 포지션 추적, 손익 계산,
손절 관리 등의 핵심 기능을 제공합니다.

---

## 구현 내용

### 1. Position 클래스 (src/backtest/portfolio.py)

**개요**: 개별 포지션의 정보를 관리하는 데이터 클래스

**주요 속성**:
- `ticker`: 종목코드
- `position_type`: 'long' (매수) 또는 'short' (공매도)
- `entry_date`: 진입 날짜
- `entry_price`: 진입 평균가
- `shares`: 보유 주식 수
- `units`: 유닛 수 (터틀 트레이딩)
- `stop_price`: 손절가
- `stop_type`: 손절 유형 ('volatility' or 'trend')
- `highest_price`: 진입 후 최고가 (트레일링 스톱용)
- `lowest_price`: 진입 후 최저가 (트레일링 스톱용)
- `signal_strength`: 진입 시 신호 강도
- `stage_at_entry`: 진입 시 스테이지

**주요 메서드**:

#### current_value(current_price)
현재 포지션의 평가액 계산
- 매수 포지션: `shares × current_price`
- 공매도 포지션: `shares × (2 × entry_price - current_price)`

#### unrealized_pnl(current_price)
미실현 손익 계산
- 매수: `(current_price - entry_price) × shares`
- 공매도: `(entry_price - current_price) × shares`

#### realized_pnl(exit_price, shares=None)
실현 손익 계산 (청산 시)
- 전체 청산 또는 부분 청산 지원

#### update_extremes(current_price)
최고가/최저가 업데이트 (트레일링 스톱용)
- 매수: 최고가 갱신 시 업데이트
- 공매도: 최저가 갱신 시 업데이트

**검증 로직**:
- `position_type`은 'long' 또는 'short'만 허용
- `shares`와 `entry_price`는 양수여야 함
- 최고가/최저가 자동 초기화

---

### 2. Portfolio 클래스 (src/backtest/portfolio.py)

**개요**: 전체 포트폴리오를 관리하는 클래스

**주요 속성**:
- `initial_capital`: 초기 자본금
- `cash`: 현금 잔고
- `positions`: 보유 포지션 딕셔너리 {ticker: Position}
- `closed_positions`: 청산된 포지션 리스트
- `history`: 포트폴리오 스냅샷 히스토리
- `trades`: 모든 거래 내역
- `commission_rate`: 수수료율 (기본값: 0.015%)

**주요 메서드**:

#### add_position(position, cost)
새로운 포지션 추가
- 기존 포지션이 있으면 평균가 계산하여 통합
- 현금 부족 시 ValueError 발생
- 로깅: 포지션 추가/신규 정보

**평균가 계산 로직**:
```python
avg_price = (existing_price × existing_shares + new_price × new_shares) / total_shares
```

#### close_position(ticker, exit_price, shares=None, reason=None)
포지션 청산
- 전체 청산 또는 부분 청산 지원
- 실현 손익 및 수익률 계산
- 수수료 반영하여 현금 회수
- 거래 내역 자동 기록

**반환값**:
```python
{
    'ticker': str,
    'shares': int,
    'entry_price': float,
    'exit_price': float,
    'pnl': float,  # 실현 손익
    'return_pct': float,  # 수익률 (%)
    'holding_days': int,  # 보유 기간
    'reason': str,  # 청산 사유
    'commission': float  # 수수료
}
```

#### calculate_equity(current_prices)
총 자산 계산
- 현금 + 모든 포지션의 평가액
- 현재가가 없는 종목은 진입가 사용

#### check_stop_losses(current_prices, market_data)
모든 포지션의 손절가 체크
- Level 5-2의 `check_stop_loss_triggered()` 활용
- 손절 발동된 포지션 리스트 반환

#### update_trailing_stops(current_prices, market_data)
트레일링 스톱 업데이트
- 각 포지션의 최고가/최저가 업데이트
- Level 5-2의 `update_trailing_stop()` 활용
- ATR 기반 트레일링 스톱 계산

#### record_snapshot(date, current_prices)
일별 포트폴리오 스냅샷 저장
- 날짜, 현금, 총 자산, 포지션 수, 각 포지션 상세 정보

#### get_position_dict()
리스크 관리용 포지션 딕셔너리 반환
- Level 5의 `apply_risk_management()`에 전달하기 위한 형식
- `{ticker: units}` 형태

#### get_summary()
포트폴리오 요약 정보
- 초기 자본, 현재 현금, 보유/청산 포지션 수
- 총 거래 수, 승률, 총 유닛 수

---

## 테스트 구현

### 테스트 파일
`src/tests/backtest/test_portfolio.py`

### 테스트 통계
- **총 테스트**: 24개
- **통과**: 24개 (100%)
- **실행 시간**: 0.22초

### 테스트 커버리지

#### TestPosition 클래스 (10개 테스트)
1. ✅ `test_position_creation`: 포지션 생성 및 초기화
2. ✅ `test_position_validation`: 입력 검증 (잘못된 타입, 음수 값)
3. ✅ `test_current_value_long`: 롱 포지션 평가액 계산
4. ✅ `test_current_value_short`: 숏 포지션 평가액 계산
5. ✅ `test_unrealized_pnl_long`: 롱 포지션 미실현 손익
6. ✅ `test_unrealized_pnl_short`: 숏 포지션 미실현 손익
7. ✅ `test_realized_pnl_full`: 전체 청산 손익 계산
8. ✅ `test_realized_pnl_partial`: 부분 청산 손익 계산
9. ✅ `test_update_extremes_long`: 롱 포지션 최고가 업데이트
10. ✅ `test_update_extremes_short`: 숏 포지션 최저가 업데이트

#### TestPortfolio 클래스 (14개 테스트)
1. ✅ `test_portfolio_creation`: 포트폴리오 생성 및 초기화
2. ✅ `test_portfolio_validation`: 입력 검증 (음수 자본금)
3. ✅ `test_add_position_new`: 신규 포지션 추가
4. ✅ `test_add_position_existing`: 기존 포지션 추가 (평균가 계산)
5. ✅ `test_add_position_insufficient_cash`: 현금 부족 시 에러
6. ✅ `test_close_position_full`: 전체 포지션 청산
7. ✅ `test_close_position_partial`: 부분 포지션 청산
8. ✅ `test_close_position_not_exists`: 존재하지 않는 포지션 청산 시도
9. ✅ `test_close_position_exceed_shares`: 보유량 초과 청산 시도
10. ✅ `test_calculate_equity`: 총 자산 계산
11. ✅ `test_get_total_units`: 총 유닛 수 계산
12. ✅ `test_get_position_dict`: 포지션 딕셔너리 조회
13. ✅ `test_record_snapshot`: 스냅샷 기록
14. ✅ `test_get_summary`: 포트폴리오 요약 정보

### 주요 테스트 시나리오

**평균가 계산 테스트**:
```python
# 1차 매수: 100주 @ 50,000원
# 2차 매수: 50주 @ 52,000원
# 평균가 = (50,000×100 + 52,000×50) / 150 = 50,666.67원
```

**손익 계산 테스트**:
```python
# 진입: 100주 @ 50,000원
# 청산: 100주 @ 52,000원
# 손익 = (52,000 - 50,000) × 100 = 200,000원
# 수익률 = 4.0%
```

**현금 흐름 테스트**:
```python
# 초기 자본: 10,000,000원
# 매수: -5,000,000원
# 매도: +5,200,000원 (손익 +200,000원)
# 수수료: -780원 (5,200,000 × 0.00015)
# 최종 현금: 10,199,220원
```

---

## 기술적 특징

### 1. 공매도(Short) 지원
- 롱/숏 포지션 모두 지원
- 평가액 및 손익 계산 로직 분리
- 트레일링 스톱도 포지션 타입별로 처리

### 2. 부분 청산 지원
- 전체 청산과 부분 청산 모두 가능
- 부분 청산 시 유닛 수도 비율에 맞게 조정
- 평균가는 유지

### 3. 트레일링 스톱 지원
- 최고가/최저가 자동 추적
- Level 5-2와 통합하여 ATR 기반 트레일링 스톱
- 수익 보호 메커니즘

### 4. 상세한 로깅
- 포지션 추가/청산 시 상세 로그
- 트레일링 스톱 업데이트 로그
- 손절 발동 경고 로그

### 5. 검증 및 에러 처리
- 입력 값 검증 (타입, 범위 등)
- 명확한 에러 메시지
- 현금 부족, 보유량 초과 등 예외 처리

---

## 의존성

### Level 5 모듈 통합
- `src.analysis.risk.stop_loss.check_stop_loss_triggered`: 손절 발동 체크
- `src.analysis.risk.stop_loss.update_trailing_stop`: 트레일링 스톱 계산

### 표준 라이브러리
- `dataclasses`: Position 클래스 구현
- `datetime`: 날짜/시간 처리
- `typing`: 타입 힌팅
- `logging`: 로깅

### 외부 라이브러리
- `pandas`: 시장 데이터 처리 (DataFrame)

---

## 파일 구조

```
src/backtest/
├── __init__.py
└── portfolio.py              # 이번 작업에서 생성

src/tests/backtest/
├── __init__.py               # 이번 작업에서 생성
└── test_portfolio.py         # 이번 작업에서 생성
```

---

## 코드 품질

### Type Hints
- ✅ 모든 함수에 타입 힌팅 적용
- ✅ 명확한 입/출력 타입 정의

### Docstrings
- ✅ 모든 클래스와 메서드에 docstring
- ✅ Args, Returns, Raises, Notes 섹션 포함
- ✅ 예시 코드 포함

### 테스트 커버리지
- ✅ 100% 통과율 (24/24)
- ✅ 정상 케이스 + 예외 케이스 모두 커버
- ✅ 경계값 테스트 포함

### 로깅
- ✅ INFO 레벨: 주요 작업 (포지션 추가/청산)
- ✅ DEBUG 레벨: 상세 정보 (트레일링 스톱 업데이트)
- ✅ WARNING 레벨: 주의 사항 (손절 발동, 현재가 없음)

---

## 다음 단계

### Phase 1 남은 작업
- `execution.py`: 주문 실행 시뮬레이션 (Order, ExecutionEngine 클래스)
  - 슬리피지 및 수수료 반영
  - 체결가 계산

### Phase 2 예정
- `data_manager.py`: 전체 시장 데이터 관리
  - 전체 종목 코드 조회
  - 병렬 데이터 로딩
  - 캐싱

---

## 참고 사항

### 설계 원칙
- 계획 문서(`history/plan/2025-11-16_level6_backtest_engine_plan.md`)의 명세를 충실히 따름
- 기존 Level 5 리스크 관리 모듈과 통합
- 테스트 주도 개발 (모든 기능 테스트 커버)

### 백테스팅 특징
- 포트폴리오 제한 체크는 제외 (Level 5-3)
- 자본 제약만 적용
- 동시 보유 종목 수 무제한

---

## 작성자
- seunghakim
- AI Assistant (Claude)

## 작성 일자
2025-11-16
