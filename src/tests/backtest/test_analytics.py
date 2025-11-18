"""
백테스팅 성과 분석 테스트
"""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock
import tempfile
import os

from src.backtest.analytics import PerformanceAnalyzer


class TestPerformanceAnalyzer:
    """PerformanceAnalyzer 클래스 테스트"""

    def test_analyzer_creation_with_data(self):
        """데이터가 있는 경우 분석기 생성 테스트"""
        # Mock 데이터
        history = [
            {'date': datetime(2023, 1, 1), 'equity': 10_000_000},
            {'date': datetime(2023, 1, 2), 'equity': 10_100_000},
            {'date': datetime(2023, 1, 3), 'equity': 10_200_000},
        ]

        trades = [
            {'ticker': '005930', 'pnl': 100_000, 'return_pct': 2.0},
            {'ticker': '000660', 'pnl': -50_000, 'return_pct': -1.0},
        ]

        analyzer = PerformanceAnalyzer(history, trades, 10_000_000)

        assert analyzer.initial_capital == 10_000_000
        assert len(analyzer.portfolio_history) == 3
        assert len(analyzer.trades) == 2
        assert not analyzer.history_df.empty
        assert not analyzer.trades_df.empty
        assert 'equity' in analyzer.history_df.columns

    def test_analyzer_creation_empty_data(self):
        """빈 데이터로 분석기 생성 테스트"""
        analyzer = PerformanceAnalyzer([], [], 10_000_000)

        assert analyzer.initial_capital == 10_000_000
        assert analyzer.history_df.empty
        assert analyzer.trades_df.empty

    def test_calculate_returns_normal(self):
        """정상적인 수익률 계산 테스트"""
        # 1년 데이터 생성 (252 거래일)
        dates = [datetime(2023, 1, 1) + timedelta(days=i) for i in range(252)]
        equity_values = [10_000_000 * (1 + i * 0.001) for i in range(252)]  # 점진적 상승

        history = [
            {'date': date, 'equity': equity}
            for date, equity in zip(dates, equity_values)
        ]

        analyzer = PerformanceAnalyzer(history, [], 10_000_000)
        returns = analyzer.calculate_returns()

        # 총 수익률: (12,510,000 - 10,000,000) / 10,000,000 * 100 = 25.1%
        # (마지막 equity는 10,000,000 * (1 + 251 * 0.001) = 10,000,000 * 1.251)
        assert abs(returns['total_return'] - 25.1) < 0.01

        # CAGR: 1년 데이터이므로 총 수익률과 유사
        assert abs(returns['cagr'] - 25.1) < 0.01

        # 일평균 수익률
        assert returns['daily_return_mean'] > 0

        # 일수익률 표준편차
        assert returns['daily_return_std'] > 0

        # 월별 수익률
        assert len(returns['monthly_returns']) > 0

    def test_calculate_returns_empty_history(self):
        """빈 히스토리 시 수익률 계산 테스트"""
        analyzer = PerformanceAnalyzer([], [], 10_000_000)
        returns = analyzer.calculate_returns()

        assert returns['total_return'] == 0.0
        assert returns['cagr'] == 0.0
        assert returns['daily_return_mean'] == 0.0
        assert returns['daily_return_std'] == 0.0
        assert returns['monthly_returns'] == {}

    def test_calculate_returns_short_period(self):
        """짧은 기간 수익률 계산 테스트"""
        # 10일 데이터
        dates = [datetime(2023, 1, 1) + timedelta(days=i) for i in range(10)]
        equity_values = [10_000_000 * (1 + i * 0.01) for i in range(10)]

        history = [
            {'date': date, 'equity': equity}
            for date, equity in zip(dates, equity_values)
        ]

        analyzer = PerformanceAnalyzer(history, [], 10_000_000)
        returns = analyzer.calculate_returns()

        # 총 수익률
        assert returns['total_return'] > 0

        # CAGR (10/252년)
        assert returns['cagr'] > 0

    def test_calculate_sharpe_ratio_normal(self):
        """정상적인 샤프 비율 계산 테스트"""
        # 안정적으로 상승하는 데이터
        dates = [datetime(2023, 1, 1) + timedelta(days=i) for i in range(100)]
        equity_values = [10_000_000 * (1 + i * 0.002) for i in range(100)]

        history = [
            {'date': date, 'equity': equity}
            for date, equity in zip(dates, equity_values)
        ]

        analyzer = PerformanceAnalyzer(history, [], 10_000_000)
        sharpe = analyzer.calculate_sharpe_ratio()

        # 안정적 상승이므로 양수의 샤프 비율
        assert sharpe > 0

    def test_calculate_sharpe_ratio_custom_risk_free(self):
        """사용자 정의 무위험 수익률로 샤프 비율 계산 테스트"""
        dates = [datetime(2023, 1, 1) + timedelta(days=i) for i in range(100)]
        equity_values = [10_000_000 * (1 + i * 0.002) for i in range(100)]

        history = [
            {'date': date, 'equity': equity}
            for date, equity in zip(dates, equity_values)
        ]

        analyzer = PerformanceAnalyzer(history, [], 10_000_000)

        sharpe_3pct = analyzer.calculate_sharpe_ratio(risk_free_rate=0.03)
        sharpe_5pct = analyzer.calculate_sharpe_ratio(risk_free_rate=0.05)

        # 무위험 수익률이 높을수록 샤프 비율은 낮아짐
        assert sharpe_5pct < sharpe_3pct

    def test_calculate_sharpe_ratio_empty_history(self):
        """빈 히스토리 시 샤프 비율 계산 테스트"""
        analyzer = PerformanceAnalyzer([], [], 10_000_000)
        sharpe = analyzer.calculate_sharpe_ratio()

        assert sharpe == 0.0

    def test_calculate_sharpe_ratio_zero_volatility(self):
        """변동성이 0인 경우 샤프 비율 계산 테스트"""
        # 모든 날 동일한 자산 (변동성 0)
        history = [
            {'date': datetime(2023, 1, 1), 'equity': 10_000_000},
            {'date': datetime(2023, 1, 2), 'equity': 10_000_000},
            {'date': datetime(2023, 1, 3), 'equity': 10_000_000},
        ]

        analyzer = PerformanceAnalyzer(history, [], 10_000_000)
        sharpe = analyzer.calculate_sharpe_ratio()

        assert sharpe == 0.0

    def test_calculate_max_drawdown_normal(self):
        """정상적인 최대 낙폭 계산 테스트"""
        history = [
            {'date': datetime(2023, 1, 1), 'equity': 10_000_000},
            {'date': datetime(2023, 1, 2), 'equity': 11_000_000},  # 고점
            {'date': datetime(2023, 1, 3), 'equity': 9_000_000},   # 저점 (MDD)
            {'date': datetime(2023, 1, 4), 'equity': 10_000_000},
            {'date': datetime(2023, 1, 5), 'equity': 11_500_000},  # 회복
        ]

        analyzer = PerformanceAnalyzer(history, [], 10_000_000)
        mdd = analyzer.calculate_max_drawdown()

        # MDD = (11,000,000 - 9,000,000) / 11,000,000 * 100 = 18.18%
        assert abs(mdd['max_drawdown'] - 18.18) < 0.01
        assert mdd['peak_date'] == '2023-01-02'
        assert mdd['trough_date'] == '2023-01-03'
        assert mdd['recovery_date'] == '2023-01-05'
        assert mdd['duration_days'] == 3

    def test_calculate_max_drawdown_no_drawdown(self):
        """낙폭이 없는 경우 (계속 상승) 테스트"""
        history = [
            {'date': datetime(2023, 1, 1), 'equity': 10_000_000},
            {'date': datetime(2023, 1, 2), 'equity': 10_500_000},
            {'date': datetime(2023, 1, 3), 'equity': 11_000_000},
            {'date': datetime(2023, 1, 4), 'equity': 11_500_000},
        ]

        analyzer = PerformanceAnalyzer(history, [], 10_000_000)
        mdd = analyzer.calculate_max_drawdown()

        # 낙폭 없음
        assert mdd['max_drawdown'] == 0.0

    def test_calculate_max_drawdown_no_recovery(self):
        """회복하지 못한 경우 테스트"""
        history = [
            {'date': datetime(2023, 1, 1), 'equity': 10_000_000},
            {'date': datetime(2023, 1, 2), 'equity': 11_000_000},  # 고점
            {'date': datetime(2023, 1, 3), 'equity': 9_000_000},   # 저점
            {'date': datetime(2023, 1, 4), 'equity': 9_500_000},   # 미회복
        ]

        analyzer = PerformanceAnalyzer(history, [], 10_000_000)
        mdd = analyzer.calculate_max_drawdown()

        assert abs(mdd['max_drawdown'] - 18.18) < 0.01
        assert mdd['peak_date'] == '2023-01-02'
        assert mdd['trough_date'] == '2023-01-03'
        assert mdd['recovery_date'] is None  # 미회복
        assert mdd['duration_days'] == 2

    def test_calculate_max_drawdown_empty_history(self):
        """빈 히스토리 시 최대 낙폭 계산 테스트"""
        analyzer = PerformanceAnalyzer([], [], 10_000_000)
        mdd = analyzer.calculate_max_drawdown()

        assert mdd['max_drawdown'] == 0.0
        assert mdd['peak_date'] is None
        assert mdd['trough_date'] is None
        assert mdd['recovery_date'] is None
        assert mdd['duration_days'] == 0

    def test_calculate_win_rate_normal(self):
        """정상적인 승률 계산 테스트"""
        trades = [
            {'ticker': '005930', 'pnl': 200_000, 'return_pct': 4.0},
            {'ticker': '000660', 'pnl': -100_000, 'return_pct': -2.0},
            {'ticker': '035420', 'pnl': 150_000, 'return_pct': 3.0},
            {'ticker': '051910', 'pnl': -50_000, 'return_pct': -1.0},
            {'ticker': '035720', 'pnl': 300_000, 'return_pct': 6.0},
        ]

        analyzer = PerformanceAnalyzer([], trades, 10_000_000)
        win_rate = analyzer.calculate_win_rate()

        assert win_rate['total_trades'] == 5
        assert win_rate['winning_trades'] == 3
        assert win_rate['losing_trades'] == 2
        assert win_rate['win_rate'] == 60.0

        # 평균 수익: (200,000 + 150,000 + 300,000) / 3 = 216,666.67
        assert abs(win_rate['avg_win'] - 216666.67) < 1

        # 평균 손실: (-100,000 - 50,000) / 2 = -75,000
        assert abs(win_rate['avg_loss'] - (-75000)) < 1

    def test_calculate_win_rate_all_wins(self):
        """모두 수익인 경우 테스트"""
        trades = [
            {'ticker': '005930', 'pnl': 200_000, 'return_pct': 4.0},
            {'ticker': '000660', 'pnl': 150_000, 'return_pct': 3.0},
        ]

        analyzer = PerformanceAnalyzer([], trades, 10_000_000)
        win_rate = analyzer.calculate_win_rate()

        assert win_rate['total_trades'] == 2
        assert win_rate['winning_trades'] == 2
        assert win_rate['losing_trades'] == 0
        assert win_rate['win_rate'] == 100.0
        assert win_rate['avg_loss'] == 0.0

    def test_calculate_win_rate_all_losses(self):
        """모두 손실인 경우 테스트"""
        trades = [
            {'ticker': '005930', 'pnl': -200_000, 'return_pct': -4.0},
            {'ticker': '000660', 'pnl': -150_000, 'return_pct': -3.0},
        ]

        analyzer = PerformanceAnalyzer([], trades, 10_000_000)
        win_rate = analyzer.calculate_win_rate()

        assert win_rate['total_trades'] == 2
        assert win_rate['winning_trades'] == 0
        assert win_rate['losing_trades'] == 2
        assert win_rate['win_rate'] == 0.0
        assert win_rate['avg_win'] == 0.0

    def test_calculate_win_rate_empty_trades(self):
        """거래 내역 없는 경우 테스트"""
        analyzer = PerformanceAnalyzer([], [], 10_000_000)
        win_rate = analyzer.calculate_win_rate()

        assert win_rate['total_trades'] == 0
        assert win_rate['winning_trades'] == 0
        assert win_rate['losing_trades'] == 0
        assert win_rate['win_rate'] == 0.0
        assert win_rate['avg_win'] == 0.0
        assert win_rate['avg_loss'] == 0.0

    def test_calculate_profit_factor_normal(self):
        """정상적인 손익비 계산 테스트"""
        trades = [
            {'ticker': '005930', 'pnl': 400_000},
            {'ticker': '000660', 'pnl': -100_000},
            {'ticker': '035420', 'pnl': 200_000},
            {'ticker': '051910', 'pnl': -50_000},
        ]

        analyzer = PerformanceAnalyzer([], trades, 10_000_000)
        pf = analyzer.calculate_profit_factor()

        # 총 수익: 600,000 / 총 손실: 150,000 = 4.0
        assert abs(pf - 4.0) < 0.01

    def test_calculate_profit_factor_only_profits(self):
        """손실이 없는 경우 (무한대) 테스트"""
        trades = [
            {'ticker': '005930', 'pnl': 200_000},
            {'ticker': '000660', 'pnl': 150_000},
        ]

        analyzer = PerformanceAnalyzer([], trades, 10_000_000)
        pf = analyzer.calculate_profit_factor()

        assert pf == float('inf')

    def test_calculate_profit_factor_only_losses(self):
        """수익이 없는 경우 테스트"""
        trades = [
            {'ticker': '005930', 'pnl': -200_000},
            {'ticker': '000660', 'pnl': -150_000},
        ]

        analyzer = PerformanceAnalyzer([], trades, 10_000_000)
        pf = analyzer.calculate_profit_factor()

        assert pf == 0.0

    def test_calculate_profit_factor_empty_trades(self):
        """거래 내역 없는 경우 테스트"""
        analyzer = PerformanceAnalyzer([], [], 10_000_000)
        pf = analyzer.calculate_profit_factor()

        assert pf == 0.0

    def test_generate_report_normal(self):
        """정상적인 리포트 생성 테스트"""
        # 데이터 생성
        dates = [datetime(2023, 1, 1) + timedelta(days=i) for i in range(100)]
        equity_values = [10_000_000 * (1 + i * 0.002) for i in range(100)]

        history = [
            {'date': date, 'equity': equity}
            for date, equity in zip(dates, equity_values)
        ]

        trades = [
            {'ticker': '005930', 'pnl': 200_000, 'return_pct': 4.0},
            {'ticker': '000660', 'pnl': -100_000, 'return_pct': -2.0},
        ]

        analyzer = PerformanceAnalyzer(history, trades, 10_000_000)
        report = analyzer.generate_report()

        # 리포트 내용 확인
        assert '백테스팅 성과 분석 리포트' in report
        assert '수익률 지표' in report
        assert '리스크 지표' in report
        assert '거래 통계' in report
        assert '초기 자본' in report
        assert '샤프 비율' in report
        assert '최대 낙폭' in report
        assert '승률' in report

    def test_generate_report_empty_data(self):
        """빈 데이터로 리포트 생성 테스트"""
        analyzer = PerformanceAnalyzer([], [], 10_000_000)
        report = analyzer.generate_report()

        # 리포트가 생성되어야 함 (빈 값들로)
        assert '백테스팅 성과 분석 리포트' in report
        assert '0.00%' in report

    @patch('matplotlib.pyplot.savefig')
    @patch('matplotlib.pyplot.figure')
    @patch('matplotlib.pyplot.close')
    def test_plot_equity_curve_with_file(self, mock_close, mock_figure, mock_savefig):
        """자산곡선 차트 생성 (파일 저장) 테스트"""
        history = [
            {'date': datetime(2023, 1, 1), 'equity': 10_000_000},
            {'date': datetime(2023, 1, 2), 'equity': 10_100_000},
            {'date': datetime(2023, 1, 3), 'equity': 10_200_000},
        ]

        analyzer = PerformanceAnalyzer(history, [], 10_000_000)
        analyzer.plot_equity_curve('test_equity.png')

        # matplotlib 함수가 호출되었는지 확인
        assert mock_figure.called
        mock_savefig.assert_called_with('test_equity.png', dpi=300, bbox_inches='tight')
        assert mock_close.called

    @patch('matplotlib.pyplot.show')
    @patch('matplotlib.pyplot.figure')
    @patch('matplotlib.pyplot.close')
    def test_plot_equity_curve_without_file(self, mock_close, mock_figure, mock_show):
        """자산곡선 차트 생성 (표시만) 테스트"""
        history = [
            {'date': datetime(2023, 1, 1), 'equity': 10_000_000},
            {'date': datetime(2023, 1, 2), 'equity': 10_100_000},
        ]

        analyzer = PerformanceAnalyzer(history, [], 10_000_000)
        analyzer.plot_equity_curve()

        assert mock_figure.called
        assert mock_show.called
        assert mock_close.called

    def test_plot_equity_curve_empty_history(self):
        """빈 히스토리로 자산곡선 차트 생성 테스트"""
        analyzer = PerformanceAnalyzer([], [], 10_000_000)

        # 에러 없이 처리되어야 함
        analyzer.plot_equity_curve()

    @patch('matplotlib.pyplot.savefig')
    @patch('matplotlib.pyplot.figure')
    @patch('matplotlib.pyplot.close')
    def test_plot_drawdown_with_file(self, mock_close, mock_figure, mock_savefig):
        """낙폭 차트 생성 (파일 저장) 테스트"""
        history = [
            {'date': datetime(2023, 1, 1), 'equity': 10_000_000},
            {'date': datetime(2023, 1, 2), 'equity': 11_000_000},
            {'date': datetime(2023, 1, 3), 'equity': 9_000_000},
        ]

        analyzer = PerformanceAnalyzer(history, [], 10_000_000)
        analyzer.plot_drawdown('test_dd.png')

        assert mock_figure.called
        mock_savefig.assert_called_with('test_dd.png', dpi=300, bbox_inches='tight')
        assert mock_close.called

    def test_plot_drawdown_empty_history(self):
        """빈 히스토리로 낙폭 차트 생성 테스트"""
        analyzer = PerformanceAnalyzer([], [], 10_000_000)

        # 에러 없이 처리되어야 함
        analyzer.plot_drawdown()

    def test_export_trades_normal(self):
        """거래 내역 CSV export 테스트"""
        trades = [
            {'ticker': '005930', 'pnl': 200_000, 'return_pct': 4.0},
            {'ticker': '000660', 'pnl': -100_000, 'return_pct': -2.0},
        ]

        analyzer = PerformanceAnalyzer([], trades, 10_000_000)

        # 임시 파일 생성
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            filepath = f.name

        try:
            analyzer.export_trades(filepath)

            # 파일이 생성되었는지 확인
            assert os.path.exists(filepath)

            # CSV 내용 확인
            df = pd.read_csv(filepath)
            assert len(df) == 2
            assert 'ticker' in df.columns
            assert 'pnl' in df.columns

        finally:
            # 임시 파일 삭제
            if os.path.exists(filepath):
                os.remove(filepath)

    def test_export_trades_empty(self):
        """빈 거래 내역 export 테스트"""
        analyzer = PerformanceAnalyzer([], [], 10_000_000)

        # 에러 없이 처리되어야 함 (경고 로그만)
        analyzer.export_trades('test_empty.csv')

        # 파일이 생성되지 않아야 함
        assert not os.path.exists('test_empty.csv')

    def test_integration_full_analysis(self):
        """전체 분석 통합 테스트"""
        # 실제 시나리오와 유사한 데이터
        dates = [datetime(2023, 1, 1) + timedelta(days=i) for i in range(252)]
        equity_values = []
        base_equity = 10_000_000

        # 변동성 있는 수익률 생성
        for i in range(252):
            if i < 100:
                # 초반 상승
                equity_values.append(base_equity * (1 + i * 0.003))
            elif i < 150:
                # 중반 하락
                equity_values.append(base_equity * (1.3 - (i - 100) * 0.002))
            else:
                # 후반 회복
                equity_values.append(base_equity * (1.2 + (i - 150) * 0.001))

        history = [
            {'date': date, 'equity': equity}
            for date, equity in zip(dates, equity_values)
        ]

        trades = [
            {'ticker': f'{i:06d}', 'pnl': (i % 3 - 1) * 100_000, 'return_pct': (i % 3 - 1) * 2.0}
            for i in range(20)
        ]

        analyzer = PerformanceAnalyzer(history, trades, 10_000_000)

        # 모든 메서드 실행
        returns = analyzer.calculate_returns()
        sharpe = analyzer.calculate_sharpe_ratio()
        mdd = analyzer.calculate_max_drawdown()
        win_rate = analyzer.calculate_win_rate()
        profit_factor = analyzer.calculate_profit_factor()
        report = analyzer.generate_report()

        # 결과 확인
        assert returns['total_return'] != 0.0
        assert sharpe != 0.0
        assert mdd['max_drawdown'] > 0.0
        assert win_rate['total_trades'] == 20
        assert profit_factor > 0.0
        assert len(report) > 0
