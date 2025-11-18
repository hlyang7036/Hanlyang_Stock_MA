"""
주문 실행 모듈 테스트
"""

import pytest
from datetime import datetime

from src.backtest.execution import Order, ExecutionEngine


class TestOrder:
    """Order 클래스 테스트"""

    def test_order_creation_minimal(self):
        """최소 필수 정보로 주문 생성 테스트"""
        order = Order(
            ticker='005930',
            action='buy',
            shares=100
        )

        assert order.ticker == '005930'
        assert order.action == 'buy'
        assert order.shares == 100
        assert order.order_type == 'market'
        assert order.position_type == 'long'
        assert order.timestamp is not None  # 자동 설정

    def test_order_creation_full(self):
        """전체 정보로 주문 생성 테스트"""
        timestamp = datetime(2023, 1, 1, 9, 30, 0)

        order = Order(
            ticker='005930',
            action='sell',
            shares=50,
            order_type='limit',
            limit_price=52000,
            timestamp=timestamp,
            position_type='long',
            units=2,
            stop_price=48000,
            signal_strength=85,
            reason='exit_signal'
        )

        assert order.ticker == '005930'
        assert order.action == 'sell'
        assert order.shares == 50
        assert order.order_type == 'limit'
        assert order.limit_price == 52000
        assert order.timestamp == timestamp
        assert order.position_type == 'long'
        assert order.units == 2
        assert order.stop_price == 48000
        assert order.signal_strength == 85
        assert order.reason == 'exit_signal'

    def test_order_validation_action(self):
        """잘못된 action 검증 테스트"""
        with pytest.raises(ValueError, match="action"):
            Order(
                ticker='005930',
                action='invalid',
                shares=100
            )

    def test_order_validation_shares(self):
        """잘못된 shares 검증 테스트"""
        # 0 shares
        with pytest.raises(ValueError, match="shares"):
            Order(
                ticker='005930',
                action='buy',
                shares=0
            )

        # 음수 shares
        with pytest.raises(ValueError, match="shares"):
            Order(
                ticker='005930',
                action='buy',
                shares=-100
            )

    def test_order_validation_order_type(self):
        """잘못된 order_type 검증 테스트"""
        with pytest.raises(ValueError, match="order_type"):
            Order(
                ticker='005930',
                action='buy',
                shares=100,
                order_type='invalid'
            )

    def test_order_validation_limit_price(self):
        """limit 주문 시 limit_price 필요 검증 테스트"""
        with pytest.raises(ValueError, match="limit_price"):
            Order(
                ticker='005930',
                action='buy',
                shares=100,
                order_type='limit'
                # limit_price 누락
            )

    def test_order_validation_position_type(self):
        """잘못된 position_type 검증 테스트"""
        with pytest.raises(ValueError, match="position_type"):
            Order(
                ticker='005930',
                action='buy',
                shares=100,
                position_type='invalid'
            )


class TestExecutionEngine:
    """ExecutionEngine 클래스 테스트"""

    def test_engine_creation_default(self):
        """기본 설정으로 엔진 생성 테스트"""
        engine = ExecutionEngine()

        assert engine.commission_rate == 0.00015
        assert engine.slippage_pct == 0.001

    def test_engine_creation_custom(self):
        """사용자 정의 설정으로 엔진 생성 테스트"""
        engine = ExecutionEngine(
            commission_rate=0.0002,
            slippage_pct=0.002
        )

        assert engine.commission_rate == 0.0002
        assert engine.slippage_pct == 0.002

    def test_engine_validation_commission_rate(self):
        """음수 수수료율 검증 테스트"""
        with pytest.raises(ValueError, match="수수료율"):
            ExecutionEngine(commission_rate=-0.001)

    def test_engine_validation_slippage_pct(self):
        """음수 슬리피지 비율 검증 테스트"""
        with pytest.raises(ValueError, match="슬리피지"):
            ExecutionEngine(slippage_pct=-0.001)

    def test_calculate_fill_price_buy(self):
        """매수 시 체결가 계산 테스트"""
        engine = ExecutionEngine(slippage_pct=0.001)

        order = Order(ticker='005930', action='buy', shares=100)
        fill_price = engine.calculate_fill_price(order, 50000)

        # 매수: 시장가 + 0.1% 슬리피지
        assert abs(fill_price - 50050.0) < 0.01

    def test_calculate_fill_price_sell(self):
        """매도 시 체결가 계산 테스트"""
        engine = ExecutionEngine(slippage_pct=0.001)

        order = Order(ticker='005930', action='sell', shares=100)
        fill_price = engine.calculate_fill_price(order, 50000)

        # 매도: 시장가 - 0.1% 슬리피지
        assert fill_price == 49950.0

    def test_calculate_fill_price_no_slippage(self):
        """슬리피지 0일 때 체결가 테스트"""
        engine = ExecutionEngine(slippage_pct=0.0)

        order_buy = Order(ticker='005930', action='buy', shares=100)
        assert engine.calculate_fill_price(order_buy, 50000) == 50000.0

        order_sell = Order(ticker='005930', action='sell', shares=100)
        assert engine.calculate_fill_price(order_sell, 50000) == 50000.0

    def test_calculate_commission(self):
        """수수료 계산 테스트"""
        engine = ExecutionEngine(commission_rate=0.00015)

        # 50,000원 × 100주 × 0.00015 = 750원
        commission = engine.calculate_commission(50000, 100)
        assert abs(commission - 750.0) < 0.01

    def test_calculate_commission_large_amount(self):
        """대금액 거래 수수료 계산 테스트"""
        engine = ExecutionEngine(commission_rate=0.00015)

        # 100,000원 × 1,000주 × 0.00015 = 15,000원
        commission = engine.calculate_commission(100000, 1000)
        assert abs(commission - 15000.0) < 0.01

    def test_calculate_total_cost_buy(self):
        """매수 총 비용 계산 테스트"""
        engine = ExecutionEngine()

        # 50,000원 × 100주 + 수수료 7.5원
        total_cost = engine.calculate_total_cost(50000, 100, 7.5, 'buy')
        assert total_cost == 5_000_007.5

    def test_calculate_total_cost_sell(self):
        """매도 총 수령액 계산 테스트"""
        engine = ExecutionEngine()

        # 50,000원 × 100주 - 수수료 7.5원
        total_cost = engine.calculate_total_cost(50000, 100, 7.5, 'sell')
        assert total_cost == 4_999_992.5

    def test_execute_buy_order(self):
        """매수 주문 실행 테스트"""
        engine = ExecutionEngine(
            commission_rate=0.00015,
            slippage_pct=0.001
        )

        order = Order(
            ticker='005930',
            action='buy',
            shares=100
        )

        result = engine.execute(order, 50000)

        assert result['filled'] is True
        assert result['ticker'] == '005930'
        assert result['action'] == 'buy'
        assert result['shares'] == 100

        # 체결가 = 50,000 × 1.001 = 50,050
        assert abs(result['fill_price'] - 50050.0) < 0.01

        # 수수료 = 50,050 × 100 × 0.00015 = 750.75
        assert abs(result['commission'] - 750.75) < 1

        # 총 비용 = 5,005,000 + 750.75 = 5,005,750.75
        assert abs(result['total_cost'] - 5_005_750.75) < 1

        # 슬리피지 금액 = 50원 × 100주 = 5,000원
        assert abs(result['slippage'] - 5000.0) < 0.01

    def test_execute_sell_order(self):
        """매도 주문 실행 테스트"""
        engine = ExecutionEngine(
            commission_rate=0.00015,
            slippage_pct=0.001
        )

        order = Order(
            ticker='005930',
            action='sell',
            shares=100
        )

        result = engine.execute(order, 50000)

        assert result['filled'] is True
        assert result['ticker'] == '005930'
        assert result['action'] == 'sell'
        assert result['shares'] == 100

        # 체결가 = 50,000 × 0.999 = 49,950
        assert abs(result['fill_price'] - 49950.0) < 0.01

        # 수수료 = 49,950 × 100 × 0.00015 = 749.25
        assert abs(result['commission'] - 749.25) < 1

        # 총 수령액 = 4,995,000 - 749.25 = 4,994,250.75
        assert abs(result['total_cost'] - 4_994_250.75) < 1

        # 슬리피지 금액 = 50원 × 100주 = 5,000원
        assert result['slippage'] == 5000.0

    def test_execute_invalid_market_price(self):
        """잘못된 시장가로 주문 실행 시도 테스트"""
        engine = ExecutionEngine()
        order = Order(ticker='005930', action='buy', shares=100)

        # 0 이하의 시장가
        with pytest.raises(ValueError, match="시장가"):
            engine.execute(order, 0)

        with pytest.raises(ValueError, match="시장가"):
            engine.execute(order, -50000)

    def test_execute_large_order(self):
        """대량 주문 실행 테스트"""
        engine = ExecutionEngine(
            commission_rate=0.00015,
            slippage_pct=0.001
        )

        order = Order(
            ticker='005930',
            action='buy',
            shares=10000  # 1만주
        )

        result = engine.execute(order, 50000)

        assert result['filled'] is True
        assert result['shares'] == 10000

        # 체결가 = 50,050
        assert abs(result['fill_price'] - 50050.0) < 0.01

        # 수수료 = 50,050 × 10,000 × 0.00015 = 75,075
        assert abs(result['commission'] - 75075) < 10

        # 총 비용 = 500,500,000 + 75,075 = 500,575,075
        assert abs(result['total_cost'] - 500_575_075) < 10

    def test_execute_with_no_slippage_and_commission(self):
        """슬리피지와 수수료가 0일 때 테스트"""
        engine = ExecutionEngine(
            commission_rate=0.0,
            slippage_pct=0.0
        )

        order = Order(ticker='005930', action='buy', shares=100)
        result = engine.execute(order, 50000)

        # 체결가 = 시장가
        assert result['fill_price'] == 50000.0

        # 수수료 = 0
        assert result['commission'] == 0.0

        # 총 비용 = 5,000,000
        assert result['total_cost'] == 5_000_000.0

        # 슬리피지 = 0
        assert result['slippage'] == 0.0

    def test_get_config(self):
        """설정 조회 테스트"""
        engine = ExecutionEngine(
            commission_rate=0.0002,
            slippage_pct=0.002
        )

        config = engine.get_config()

        assert config['commission_rate'] == 0.0002
        assert config['slippage_pct'] == 0.002

    def test_update_config_commission_rate(self):
        """수수료율 업데이트 테스트"""
        engine = ExecutionEngine(commission_rate=0.00015)

        engine.update_config(commission_rate=0.0002)

        assert engine.commission_rate == 0.0002
        assert engine.slippage_pct == 0.001  # 변경되지 않음

    def test_update_config_slippage_pct(self):
        """슬리피지 비율 업데이트 테스트"""
        engine = ExecutionEngine(slippage_pct=0.001)

        engine.update_config(slippage_pct=0.002)

        assert engine.commission_rate == 0.00015  # 변경되지 않음
        assert engine.slippage_pct == 0.002

    def test_update_config_both(self):
        """수수료율과 슬리피지 모두 업데이트 테스트"""
        engine = ExecutionEngine()

        engine.update_config(
            commission_rate=0.0003,
            slippage_pct=0.003
        )

        assert engine.commission_rate == 0.0003
        assert engine.slippage_pct == 0.003

    def test_update_config_invalid_commission_rate(self):
        """잘못된 수수료율로 업데이트 시도 테스트"""
        engine = ExecutionEngine()

        with pytest.raises(ValueError, match="수수료율"):
            engine.update_config(commission_rate=-0.001)

    def test_update_config_invalid_slippage_pct(self):
        """잘못된 슬리피지 비율로 업데이트 시도 테스트"""
        engine = ExecutionEngine()

        with pytest.raises(ValueError, match="슬리피지"):
            engine.update_config(slippage_pct=-0.001)

    def test_realistic_scenario(self):
        """
        현실적인 시나리오 테스트

        시나리오:
        - 삼성전자 100주를 50,000원에 매수
        - 한국투자증권 수수료율: 0.015%
        - 예상 슬리피지: 0.1%
        """
        engine = ExecutionEngine(
            commission_rate=0.00015,  # 0.015%
            slippage_pct=0.001  # 0.1%
        )

        order = Order(
            ticker='005930',
            action='buy',
            shares=100
        )

        result = engine.execute(order, 50000)

        # 체결가: 50,000 + 0.1% = 50,050원
        assert abs(result['fill_price'] - 50050.0) < 0.01

        # 주식 가격: 50,050 × 100 = 5,005,000원
        # 수수료: 50,050 × 100 × 0.00015 = 750.75원
        # 총 비용: 5,005,000 + 750.75 = 5,005,750.75원
        expected_total = 50050 * 100 + (50050 * 100 * 0.00015)
        assert abs(result['total_cost'] - expected_total) < 1

        # 슬리피지로 인한 추가 비용: 50원 × 100주 = 5,000원
        assert abs(result['slippage'] - 5000.0) < 0.01
