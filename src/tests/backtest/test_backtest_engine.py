"""
백테스팅 엔진 테스트
"""

import pytest
import pandas as pd
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock

from src.backtest.engine import BacktestEngine, BacktestResult
from src.backtest.portfolio import Portfolio, Position


class TestBacktestResult:
    """BacktestResult 클래스 테스트"""

    def test_result_creation(self):
        """백테스팅 결과 생성 테스트"""
        result = BacktestResult(
            start_date='2023-01-01',
            end_date='2023-12-31',
            initial_capital=10_000_000,
            final_capital=12_000_000,
            total_return=20.0,
            max_drawdown=5.0,
            total_trades=10,
            winning_trades=6,
            losing_trades=4,
            win_rate=60.0,
            portfolio_history=[],
            trades=[],
            market_count=100
        )

        assert result.start_date == '2023-01-01'
        assert result.end_date == '2023-12-31'
        assert result.initial_capital == 10_000_000
        assert result.final_capital == 12_000_000
        assert result.total_return == 20.0
        assert result.max_drawdown == 5.0
        assert result.total_trades == 10
        assert result.winning_trades == 6
        assert result.losing_trades == 4
        assert result.win_rate == 60.0
        assert result.market_count == 100

    def test_result_summary(self):
        """백테스팅 결과 요약 테스트"""
        result = BacktestResult(
            start_date='2023-01-01',
            end_date='2023-12-31',
            initial_capital=10_000_000,
            final_capital=12_000_000,
            total_return=20.0,
            max_drawdown=5.0,
            total_trades=10,
            winning_trades=6,
            losing_trades=4,
            win_rate=60.0,
            portfolio_history=[],
            trades=[],
            market_count=100
        )

        summary = result.summary()

        assert '2023-01-01' in summary
        assert '2023-12-31' in summary
        assert '20.00%' in summary
        assert '5.00%' in summary
        assert '10건' in summary
        assert '60.00%' in summary


class TestBacktestEngine:
    """BacktestEngine 클래스 테스트"""

    def test_engine_creation_default(self):
        """기본 설정으로 엔진 생성 테스트"""
        engine = BacktestEngine()

        assert engine.config == {}
        assert engine.data_manager is not None
        assert engine.execution_engine is not None
        assert engine.portfolio is None
        assert engine.market_data is None

    def test_engine_creation_custom(self):
        """사용자 정의 설정으로 엔진 생성 테스트"""
        config = {
            'use_cache': False,
            'commission_rate': 0.0002,
            'slippage_pct': 0.002,
            'enable_early_signals': True
        }

        engine = BacktestEngine(config=config)

        assert engine.config == config
        assert engine.execution_engine.commission_rate == 0.0002
        assert engine.execution_engine.slippage_pct == 0.002

    def test_get_common_dates_empty(self):
        """빈 시장 데이터 시 공통 날짜 조회 테스트"""
        engine = BacktestEngine()
        engine.market_data = {}

        dates = engine._get_common_dates()

        assert dates == []

    def test_get_common_dates(self):
        """공통 날짜 조회 테스트"""
        engine = BacktestEngine()

        # Mock 시장 데이터
        date1 = datetime(2023, 1, 1)
        date2 = datetime(2023, 1, 2)
        date3 = datetime(2023, 1, 3)

        engine.market_data = {
            '005930': pd.DataFrame(
                {'Close': [50000, 51000, 52000]},
                index=[date1, date2, date3]
            ),
            '000660': pd.DataFrame(
                {'Close': [80000, 81000]},
                index=[date1, date2]
            )
        }

        dates = engine._get_common_dates()

        # 모든 날짜가 포함되어야 함 (교집합이 아닌 합집합)
        assert len(dates) == 3
        assert date1 in dates
        assert date2 in dates
        assert date3 in dates

    def test_get_current_prices(self):
        """현재가 조회 테스트"""
        engine = BacktestEngine()

        date = datetime(2023, 1, 2)

        engine.market_data = {
            '005930': pd.DataFrame(
                {'Close': [50000, 51000, 52000]},
                index=[datetime(2023, 1, 1), date, datetime(2023, 1, 3)]
            ),
            '000660': pd.DataFrame(
                {'Close': [80000, 81000]},
                index=[datetime(2023, 1, 1), date]
            )
        }

        prices = engine._get_current_prices(date)

        assert len(prices) == 2
        assert prices['005930'] == 51000
        assert prices['000660'] == 81000

    def test_get_current_prices_missing_date(self):
        """특정 날짜에 데이터 없는 경우 테스트"""
        engine = BacktestEngine()

        date = datetime(2023, 1, 2)

        engine.market_data = {
            '005930': pd.DataFrame(
                {'Close': [50000, 52000]},
                index=[datetime(2023, 1, 1), datetime(2023, 1, 3)]
            )
        }

        prices = engine._get_current_prices(date)

        # date가 없으므로 빈 딕셔너리
        assert prices == {}

    def test_calculate_max_drawdown_empty(self):
        """빈 히스토리 시 최대 낙폭 계산 테스트"""
        engine = BacktestEngine()
        engine.portfolio = Portfolio(initial_capital=10_000_000)

        mdd = engine._calculate_max_drawdown()

        assert mdd == 0.0

    def test_calculate_max_drawdown(self):
        """최대 낙폭 계산 테스트"""
        engine = BacktestEngine()
        engine.portfolio = Portfolio(initial_capital=10_000_000)

        # Mock 히스토리
        engine.portfolio.history = [
            {'date': datetime(2023, 1, 1), 'equity': 10_000_000},
            {'date': datetime(2023, 1, 2), 'equity': 11_000_000},  # 고점
            {'date': datetime(2023, 1, 3), 'equity': 9_000_000},   # 저점
            {'date': datetime(2023, 1, 4), 'equity': 10_500_000},  # 회복
        ]

        mdd = engine._calculate_max_drawdown()

        # (11,000,000 - 9,000,000) / 11,000,000 * 100 = 18.18%
        assert abs(mdd - 18.18) < 0.01

    def test_calculate_max_drawdown_no_drawdown(self):
        """낙폭이 없는 경우 테스트"""
        engine = BacktestEngine()
        engine.portfolio = Portfolio(initial_capital=10_000_000)

        # 계속 상승하는 경우
        engine.portfolio.history = [
            {'date': datetime(2023, 1, 1), 'equity': 10_000_000},
            {'date': datetime(2023, 1, 2), 'equity': 11_000_000},
            {'date': datetime(2023, 1, 3), 'equity': 12_000_000},
        ]

        mdd = engine._calculate_max_drawdown()

        assert mdd == 0.0

    @patch('src.backtest.engine.DataManager')
    def test_run_backtest_initialization(self, mock_data_manager):
        """백테스팅 초기화 테스트"""
        # Mock 설정
        mock_dm_instance = Mock()
        mock_dm_instance.load_market_data.return_value = {
            '005930': pd.DataFrame({
                'Open': [50000],
                'High': [51000],
                'Low': [49000],
                'Close': [50500],
                'Volume': [1000000],
                'EMA_5': [50000],
                'EMA_20': [49500],
                'EMA_40': [49000],
                'Stage': [1]
            }, index=[datetime(2023, 1, 1)])
        }
        mock_data_manager.return_value = mock_dm_instance

        engine = BacktestEngine()

        # 백테스팅 실행 (1일만)
        with patch.object(engine, 'process_day'):
            result = engine.run_backtest(
                start_date='2023-01-01',
                end_date='2023-01-01',
                initial_capital=10_000_000,
                market='ALL'
            )

        # 포트폴리오가 초기화되어야 함
        assert engine.portfolio is not None
        assert engine.portfolio.initial_capital == 10_000_000

        # 시장 데이터가 로드되어야 함
        assert engine.market_data is not None

    def test_get_results(self):
        """결과 조회 테스트"""
        engine = BacktestEngine()
        engine.portfolio = Portfolio(initial_capital=10_000_000)

        # Mock 데이터
        engine.portfolio.closed_positions = [
            {'ticker': '005930', 'pnl': 200_000, 'return_pct': 4.0},
            {'ticker': '000660', 'pnl': -100_000, 'return_pct': -2.0},
            {'ticker': '035420', 'pnl': 150_000, 'return_pct': 3.0},
        ]

        engine.portfolio.history = [
            {'date': datetime(2023, 1, 1), 'equity': 10_000_000},
            {'date': datetime(2023, 1, 2), 'equity': 10_250_000},
        ]

        # Cash 업데이트 (최종 자본)
        engine.portfolio.cash = 10_250_000

        result = engine.get_results('2023-01-01', '2023-01-02', 100)

        assert result.start_date == '2023-01-01'
        assert result.end_date == '2023-01-02'
        assert result.initial_capital == 10_000_000
        assert result.final_capital == 10_250_000
        assert result.total_return == 2.5
        assert result.total_trades == 3
        assert result.winning_trades == 2
        assert result.losing_trades == 1
        assert abs(result.win_rate - 66.67) < 0.01
        assert result.market_count == 100

    @patch('src.analysis.risk.apply_risk_management')
    @patch('src.analysis.signal.strength.evaluate_signal_strength')
    @patch('src.analysis.signal.entry.generate_entry_signals')
    def test_generate_and_execute_entries_no_signals(
        self,
        mock_entry_signals,
        mock_strength,
        mock_risk_mgmt
    ):
        """진입 신호 없는 경우 테스트"""
        engine = BacktestEngine()
        engine.portfolio = Portfolio(initial_capital=10_000_000)

        # Mock: 신호 없음
        mock_entry_signals.return_value = pd.DataFrame({
            'Entry_Signal': [0],
            'Signal_Type': ['none']
        }, index=[datetime(2023, 1, 1)])

        engine.market_data = {
            '005930': pd.DataFrame({
                'Close': [50000],
                'Stage': [1],
                'EMA_5': [50000],
                'EMA_20': [49500],
                'EMA_40': [49000]
            }, index=[datetime(2023, 1, 1)])
        }

        current_prices = {'005930': 50000}

        # 실행
        engine.generate_and_execute_entries(datetime(2023, 1, 1), current_prices)

        # 아무 신호도 없으므로 포지션 없음
        assert len(engine.portfolio.positions) == 0

    @patch('src.analysis.signal.exit.generate_exit_signal')
    def test_generate_and_execute_exits_no_signals(self, mock_exit_signal):
        """청산 신호 없는 경우 테스트"""
        engine = BacktestEngine()
        engine.portfolio = Portfolio(initial_capital=10_000_000)

        # 포지션 추가
        position = Position(
            ticker='005930',
            position_type='long',
            entry_date=datetime(2023, 1, 1),
            entry_price=50000,
            shares=100,
            units=1,
            stop_price=48000,
            stop_type='volatility'
        )
        engine.portfolio.positions['005930'] = position

        # Mock: 청산 신호 없음
        mock_exit_signal.return_value = pd.DataFrame({
            'Exit_Signal': [0],
            'Exit_Type': ['none'],
            'Exit_Ratio': [0.0]
        }, index=[datetime(2023, 1, 2)])

        engine.market_data = {
            '005930': pd.DataFrame({
                'Close': [50000, 51000],
                'Stage': [1, 1]
            }, index=[datetime(2023, 1, 1), datetime(2023, 1, 2)])
        }

        current_prices = {'005930': 51000}

        # 실행
        engine.generate_and_execute_exits(datetime(2023, 1, 2), current_prices)

        # 청산되지 않아야 함
        assert '005930' in engine.portfolio.positions

    def test_check_and_execute_stops_no_trigger(self):
        """손절 발동 없는 경우 테스트"""
        engine = BacktestEngine()
        engine.portfolio = Portfolio(initial_capital=10_000_000)

        # 포지션 추가 (손절가 48000)
        position = Position(
            ticker='005930',
            position_type='long',
            entry_date=datetime(2023, 1, 1),
            entry_price=50000,
            shares=100,
            units=1,
            stop_price=48000,
            stop_type='volatility'
        )
        engine.portfolio.positions['005930'] = position

        engine.market_data = {
            '005930': pd.DataFrame({
                'Close': [50000, 51000],  # 손절가보다 높음
                'ATR': [1000, 1000]
            }, index=[datetime(2023, 1, 1), datetime(2023, 1, 2)])
        }

        current_prices = {'005930': 51000}

        # 실행
        engine.check_and_execute_stops(datetime(2023, 1, 2), current_prices)

        # 손절 발동 안 됨
        assert '005930' in engine.portfolio.positions

    @patch('src.backtest.engine.DataManager')
    def test_process_day_integration(self, mock_data_manager):
        """일별 처리 통합 테스트"""
        # Mock 설정
        mock_dm_instance = Mock()
        mock_data_manager.return_value = mock_dm_instance

        engine = BacktestEngine()
        engine.portfolio = Portfolio(initial_capital=10_000_000)

        # Mock 시장 데이터
        engine.market_data = {
            '005930': pd.DataFrame({
                'Close': [50000, 51000],
                'Open': [49500, 50500],
                'High': [51000, 52000],
                'Low': [49000, 50000],
                'Volume': [1000000, 1100000],
                'ATR': [1000, 1000],
                'EMA_5': [50000, 51000],
                'EMA_20': [49500, 50000],
                'EMA_40': [49000, 49500],
                'Stage': [1, 1]
            }, index=[datetime(2023, 1, 1), datetime(2023, 1, 2)])
        }

        # Mock 메서드들
        with patch.object(engine, 'check_and_execute_stops'), \
             patch.object(engine, 'generate_and_execute_exits'), \
             patch.object(engine, 'generate_and_execute_entries'):

            engine.process_day(datetime(2023, 1, 2))

        # 스냅샷이 기록되어야 함
        assert len(engine.portfolio.history) == 1
