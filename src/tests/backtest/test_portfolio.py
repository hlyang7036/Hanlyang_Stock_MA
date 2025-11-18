"""
포트폴리오 모듈 테스트
"""

import pytest
from datetime import datetime, timedelta
import pandas as pd
import numpy as np

from src.backtest.portfolio import Position, Portfolio


class TestPosition:
    """Position 클래스 테스트"""

    def test_position_creation(self):
        """포지션 생성 테스트"""
        position = Position(
            ticker='005930',
            position_type='long',
            entry_date=datetime(2023, 1, 1),
            entry_price=50000,
            shares=100,
            units=2,
            stop_price=48000,
            stop_type='volatility'
        )

        assert position.ticker == '005930'
        assert position.position_type == 'long'
        assert position.shares == 100
        assert position.units == 2
        assert position.stop_price == 48000
        assert position.highest_price == 50000  # 자동 초기화

    def test_position_validation(self):
        """포지션 검증 테스트"""
        # 잘못된 position_type
        with pytest.raises(ValueError, match="position_type"):
            Position(
                ticker='005930',
                position_type='invalid',
                entry_date=datetime.now(),
                entry_price=50000,
                shares=100,
                units=2,
                stop_price=48000,
                stop_type='volatility'
            )

        # 음수 shares
        with pytest.raises(ValueError, match="shares"):
            Position(
                ticker='005930',
                position_type='long',
                entry_date=datetime.now(),
                entry_price=50000,
                shares=-100,
                units=2,
                stop_price=48000,
                stop_type='volatility'
            )

        # 음수 entry_price
        with pytest.raises(ValueError, match="entry_price"):
            Position(
                ticker='005930',
                position_type='long',
                entry_date=datetime.now(),
                entry_price=-50000,
                shares=100,
                units=2,
                stop_price=48000,
                stop_type='volatility'
            )

    def test_current_value_long(self):
        """롱 포지션 평가액 계산 테스트"""
        position = Position(
            ticker='005930',
            position_type='long',
            entry_date=datetime.now(),
            entry_price=50000,
            shares=100,
            units=2,
            stop_price=48000,
            stop_type='volatility'
        )

        # 현재가 52000원
        assert position.current_value(52000) == 5_200_000

        # 현재가 48000원
        assert position.current_value(48000) == 4_800_000

    def test_current_value_short(self):
        """숏 포지션 평가액 계산 테스트"""
        position = Position(
            ticker='005930',
            position_type='short',
            entry_date=datetime.now(),
            entry_price=50000,
            shares=100,
            units=2,
            stop_price=52000,
            stop_type='volatility'
        )

        # 현재가 48000원 (가격 하락, 숏 포지션 수익)
        # value = 100 * (2*50000 - 48000) = 5_200_000
        assert position.current_value(48000) == 5_200_000

        # 현재가 52000원 (가격 상승, 숏 포지션 손실)
        # value = 100 * (2*50000 - 52000) = 4_800_000
        assert position.current_value(52000) == 4_800_000

    def test_unrealized_pnl_long(self):
        """롱 포지션 미실현 손익 테스트"""
        position = Position(
            ticker='005930',
            position_type='long',
            entry_date=datetime.now(),
            entry_price=50000,
            shares=100,
            units=2,
            stop_price=48000,
            stop_type='volatility'
        )

        # 현재가 52000원 (수익)
        assert position.unrealized_pnl(52000) == 200_000

        # 현재가 48000원 (손실)
        assert position.unrealized_pnl(48000) == -200_000

    def test_unrealized_pnl_short(self):
        """숏 포지션 미실현 손익 테스트"""
        position = Position(
            ticker='005930',
            position_type='short',
            entry_date=datetime.now(),
            entry_price=50000,
            shares=100,
            units=2,
            stop_price=52000,
            stop_type='volatility'
        )

        # 현재가 48000원 (가격 하락, 수익)
        assert position.unrealized_pnl(48000) == 200_000

        # 현재가 52000원 (가격 상승, 손실)
        assert position.unrealized_pnl(52000) == -200_000

    def test_realized_pnl_full(self):
        """전체 청산 손익 테스트"""
        position = Position(
            ticker='005930',
            position_type='long',
            entry_date=datetime.now(),
            entry_price=50000,
            shares=100,
            units=2,
            stop_price=48000,
            stop_type='volatility'
        )

        # 전체 청산 (수익)
        assert position.realized_pnl(52000) == 200_000

        # 전체 청산 (손실)
        assert position.realized_pnl(48000) == -200_000

    def test_realized_pnl_partial(self):
        """부분 청산 손익 테스트"""
        position = Position(
            ticker='005930',
            position_type='long',
            entry_date=datetime.now(),
            entry_price=50000,
            shares=100,
            units=2,
            stop_price=48000,
            stop_type='volatility'
        )

        # 50주만 청산
        assert position.realized_pnl(52000, 50) == 100_000

    def test_update_extremes_long(self):
        """롱 포지션 최고가 업데이트 테스트"""
        position = Position(
            ticker='005930',
            position_type='long',
            entry_date=datetime.now(),
            entry_price=50000,
            shares=100,
            units=2,
            stop_price=48000,
            stop_type='volatility'
        )

        # 초기 최고가
        assert position.highest_price == 50000

        # 새로운 최고가
        position.update_extremes(52000)
        assert position.highest_price == 52000

        # 최고가 미갱신
        position.update_extremes(51000)
        assert position.highest_price == 52000

        # 다시 최고가 갱신
        position.update_extremes(53000)
        assert position.highest_price == 53000

    def test_update_extremes_short(self):
        """숏 포지션 최저가 업데이트 테스트"""
        position = Position(
            ticker='005930',
            position_type='short',
            entry_date=datetime.now(),
            entry_price=50000,
            shares=100,
            units=2,
            stop_price=52000,
            stop_type='volatility'
        )

        # 초기 최저가
        assert position.lowest_price == 50000

        # 새로운 최저가
        position.update_extremes(48000)
        assert position.lowest_price == 48000

        # 최저가 미갱신
        position.update_extremes(49000)
        assert position.lowest_price == 48000

        # 다시 최저가 갱신
        position.update_extremes(47000)
        assert position.lowest_price == 47000


class TestPortfolio:
    """Portfolio 클래스 테스트"""

    def test_portfolio_creation(self):
        """포트폴리오 생성 테스트"""
        portfolio = Portfolio(initial_capital=10_000_000)

        assert portfolio.initial_capital == 10_000_000
        assert portfolio.cash == 10_000_000
        assert len(portfolio.positions) == 0
        assert len(portfolio.closed_positions) == 0

    def test_portfolio_validation(self):
        """포트폴리오 검증 테스트"""
        # 음수 자본금
        with pytest.raises(ValueError, match="초기 자본금"):
            Portfolio(initial_capital=-1000000)

    def test_add_position_new(self):
        """신규 포지션 추가 테스트"""
        portfolio = Portfolio(initial_capital=10_000_000)

        position = Position(
            ticker='005930',
            position_type='long',
            entry_date=datetime.now(),
            entry_price=50000,
            shares=100,
            units=2,
            stop_price=48000,
            stop_type='volatility'
        )

        cost = 5_000_000 + 7.5  # 주식 가격 + 수수료
        portfolio.add_position(position, cost)

        assert len(portfolio.positions) == 1
        assert '005930' in portfolio.positions
        assert portfolio.cash == 10_000_000 - cost

    def test_add_position_existing(self):
        """기존 포지션 추가 (평균가 계산) 테스트"""
        portfolio = Portfolio(initial_capital=10_000_000)

        # 첫 번째 매수
        position1 = Position(
            ticker='005930',
            position_type='long',
            entry_date=datetime.now(),
            entry_price=50000,
            shares=100,
            units=2,
            stop_price=48000,
            stop_type='volatility'
        )
        portfolio.add_position(position1, 5_000_000)

        # 두 번째 매수 (더 높은 가격)
        position2 = Position(
            ticker='005930',
            position_type='long',
            entry_date=datetime.now(),
            entry_price=52000,
            shares=50,
            units=1,
            stop_price=50000,
            stop_type='volatility'
        )
        portfolio.add_position(position2, 2_600_000)

        # 평균가 계산: (50000*100 + 52000*50) / 150 = 50666.67
        assert len(portfolio.positions) == 1
        position = portfolio.positions['005930']
        assert position.shares == 150
        assert position.units == 3
        assert abs(position.entry_price - 50666.67) < 1

    def test_add_position_insufficient_cash(self):
        """현금 부족 시 포지션 추가 실패 테스트"""
        portfolio = Portfolio(initial_capital=1_000_000)

        position = Position(
            ticker='005930',
            position_type='long',
            entry_date=datetime.now(),
            entry_price=50000,
            shares=100,
            units=2,
            stop_price=48000,
            stop_type='volatility'
        )

        with pytest.raises(ValueError, match="현금 부족"):
            portfolio.add_position(position, 5_000_000)

    def test_close_position_full(self):
        """전체 포지션 청산 테스트"""
        portfolio = Portfolio(initial_capital=10_000_000)

        position = Position(
            ticker='005930',
            position_type='long',
            entry_date=datetime.now(),
            entry_price=50000,
            shares=100,
            units=2,
            stop_price=48000,
            stop_type='volatility'
        )
        portfolio.add_position(position, 5_000_000)

        # 52000원에 전체 청산 (수익)
        result = portfolio.close_position(
            ticker='005930',
            exit_price=52000,
            reason='exit_signal'
        )

        assert result['pnl'] == 200_000
        assert abs(result['return_pct'] - 4.0) < 0.01
        assert len(portfolio.positions) == 0
        assert len(portfolio.closed_positions) == 1

        # 현금 = 초기 - 매수비용 + 매도대금 - 매도수수료
        # 10_000_000 - 5_000_000 + 5_200_000 - (5_200_000 * 0.00015)
        expected_cash = 10_000_000 - 5_000_000 + 5_200_000 - 780
        assert abs(portfolio.cash - expected_cash) < 1

    def test_close_position_partial(self):
        """부분 포지션 청산 테스트"""
        portfolio = Portfolio(initial_capital=10_000_000)

        position = Position(
            ticker='005930',
            position_type='long',
            entry_date=datetime.now(),
            entry_price=50000,
            shares=100,
            units=2,
            stop_price=48000,
            stop_type='volatility'
        )
        portfolio.add_position(position, 5_000_000)

        # 50주만 청산
        result = portfolio.close_position(
            ticker='005930',
            exit_price=52000,
            shares=50,
            reason='partial_exit'
        )

        assert result['pnl'] == 100_000
        assert len(portfolio.positions) == 1
        assert portfolio.positions['005930'].shares == 50
        assert portfolio.positions['005930'].units == 1  # 비율에 맞게 조정

    def test_close_position_not_exists(self):
        """존재하지 않는 포지션 청산 시도 테스트"""
        portfolio = Portfolio(initial_capital=10_000_000)

        with pytest.raises(ValueError, match="포지션이 없습니다"):
            portfolio.close_position(ticker='005930', exit_price=50000)

    def test_close_position_exceed_shares(self):
        """보유량 초과 청산 시도 테스트"""
        portfolio = Portfolio(initial_capital=10_000_000)

        position = Position(
            ticker='005930',
            position_type='long',
            entry_date=datetime.now(),
            entry_price=50000,
            shares=100,
            units=2,
            stop_price=48000,
            stop_type='volatility'
        )
        portfolio.add_position(position, 5_000_000)

        with pytest.raises(ValueError, match="청산 수량 초과"):
            portfolio.close_position(ticker='005930', exit_price=52000, shares=200)

    def test_calculate_equity(self):
        """총 자산 계산 테스트"""
        portfolio = Portfolio(initial_capital=10_000_000)

        # 포지션 1
        position1 = Position(
            ticker='005930',
            position_type='long',
            entry_date=datetime.now(),
            entry_price=50000,
            shares=100,
            units=2,
            stop_price=48000,
            stop_type='volatility'
        )
        portfolio.add_position(position1, 5_000_000)

        # 포지션 2
        position2 = Position(
            ticker='000660',
            position_type='long',
            entry_date=datetime.now(),
            entry_price=100000,
            shares=20,
            units=1,
            stop_price=96000,
            stop_type='volatility'
        )
        portfolio.add_position(position2, 2_000_000)

        # 현재가
        current_prices = {
            '005930': 52000,  # +2000원
            '000660': 105000  # +5000원
        }

        # 총 자산 = 현금 + (100*52000) + (20*105000)
        #          = 3_000_000 + 5_200_000 + 2_100_000
        #          = 10_300_000
        equity = portfolio.calculate_equity(current_prices)
        assert abs(equity - 10_300_000) < 100  # 수수료 차이 고려

    def test_get_total_units(self):
        """총 유닛 수 계산 테스트"""
        portfolio = Portfolio(initial_capital=10_000_000)

        position1 = Position(
            ticker='005930',
            position_type='long',
            entry_date=datetime.now(),
            entry_price=50000,
            shares=100,
            units=2,
            stop_price=48000,
            stop_type='volatility'
        )
        portfolio.add_position(position1, 5_000_000)

        position2 = Position(
            ticker='000660',
            position_type='long',
            entry_date=datetime.now(),
            entry_price=100000,
            shares=20,
            units=3,
            stop_price=96000,
            stop_type='volatility'
        )
        portfolio.add_position(position2, 2_000_000)

        assert portfolio.get_total_units() == 5

    def test_get_position_dict(self):
        """포지션 딕셔너리 조회 테스트"""
        portfolio = Portfolio(initial_capital=10_000_000)

        position1 = Position(
            ticker='005930',
            position_type='long',
            entry_date=datetime.now(),
            entry_price=50000,
            shares=100,
            units=2,
            stop_price=48000,
            stop_type='volatility'
        )
        portfolio.add_position(position1, 5_000_000)

        position2 = Position(
            ticker='000660',
            position_type='long',
            entry_date=datetime.now(),
            entry_price=100000,
            shares=20,
            units=3,
            stop_price=96000,
            stop_type='volatility'
        )
        portfolio.add_position(position2, 2_000_000)

        position_dict = portfolio.get_position_dict()
        assert position_dict == {'005930': 2, '000660': 3}

    def test_record_snapshot(self):
        """스냅샷 기록 테스트"""
        portfolio = Portfolio(initial_capital=10_000_000)

        position = Position(
            ticker='005930',
            position_type='long',
            entry_date=datetime.now(),
            entry_price=50000,
            shares=100,
            units=2,
            stop_price=48000,
            stop_type='volatility'
        )
        portfolio.add_position(position, 5_000_000)

        current_prices = {'005930': 52000}
        portfolio.record_snapshot(datetime.now(), current_prices)

        assert len(portfolio.history) == 1
        snapshot = portfolio.history[0]
        assert snapshot['positions_count'] == 1
        assert '005930' in snapshot['positions']

    def test_get_summary(self):
        """포트폴리오 요약 정보 테스트"""
        portfolio = Portfolio(initial_capital=10_000_000)

        # 포지션 추가
        position = Position(
            ticker='005930',
            position_type='long',
            entry_date=datetime.now(),
            entry_price=50000,
            shares=100,
            units=2,
            stop_price=48000,
            stop_type='volatility'
        )
        portfolio.add_position(position, 5_000_000)

        # 청산
        portfolio.close_position(ticker='005930', exit_price=52000, reason='test')

        summary = portfolio.get_summary()
        assert summary['initial_capital'] == 10_000_000
        assert summary['total_positions'] == 0
        assert summary['closed_positions'] == 1
        assert summary['total_trades'] == 1
        assert summary['winning_trades'] == 1
        assert summary['win_rate'] == 1.0
