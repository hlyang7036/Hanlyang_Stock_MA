"""
백테스팅 성과 분석 모듈

백테스팅 결과를 분석하여 전략의 수익성과 리스크를 평가합니다.
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Any, Optional
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class PerformanceAnalyzer:
    """
    성과 분석 클래스

    백테스팅 결과를 분석하여 다양한 성과 지표를 계산합니다.

    Attributes:
        portfolio_history: 포트폴리오 스냅샷 히스토리
        trades: 거래 내역
        initial_capital: 초기 자본

    Methods:
        calculate_returns(): 수익률 계산
        calculate_sharpe_ratio(): 샤프 비율
        calculate_max_drawdown(): 최대 낙폭
        calculate_win_rate(): 승률
        calculate_profit_factor(): 손익비
        generate_report(): 종합 리포트
        plot_equity_curve(): 자산곡선 차트
        plot_drawdown(): 낙폭 차트
        export_trades(): 거래 내역 export
    """

    def __init__(
        self,
        portfolio_history: List[Dict[str, Any]],
        trades: List[Dict[str, Any]],
        initial_capital: float
    ):
        """
        성과 분석기 초기화

        Args:
            portfolio_history: 포트폴리오 스냅샷 히스토리
            trades: 거래 내역
            initial_capital: 초기 자본
        """
        self.portfolio_history = portfolio_history
        self.trades = trades
        self.initial_capital = initial_capital

        # DataFrame 변환
        if portfolio_history:
            self.history_df = pd.DataFrame(portfolio_history)
            self.history_df['date'] = pd.to_datetime(self.history_df['date'])
            self.history_df.set_index('date', inplace=True)
        else:
            self.history_df = pd.DataFrame()

        if trades:
            self.trades_df = pd.DataFrame(trades)
        else:
            self.trades_df = pd.DataFrame()

        logger.info("PerformanceAnalyzer 초기화 완료")

    def calculate_returns(self) -> Dict[str, Any]:
        """
        수익률 계산

        Returns:
            Dict: 수익률 지표
                - total_return: 총 수익률 (%)
                - cagr: 연환산 수익률 (%)
                - daily_return_mean: 일평균 수익률 (%)
                - daily_return_std: 일수익률 표준편차 (%)
                - monthly_returns: 월별 수익률 (Dict)

        Examples:
            >>> analyzer = PerformanceAnalyzer(history, trades, 10_000_000)
            >>> returns = analyzer.calculate_returns()
            >>> print(f"총 수익률: {returns['total_return']:.2f}%")
            >>> print(f"CAGR: {returns['cagr']:.2f}%")
        """
        if self.history_df.empty:
            return {
                'total_return': 0.0,
                'cagr': 0.0,
                'daily_return_mean': 0.0,
                'daily_return_std': 0.0,
                'monthly_returns': {}
            }

        # 총 수익률
        final_equity = self.history_df['equity'].iloc[-1]
        total_return = ((final_equity - self.initial_capital) /
                       self.initial_capital) * 100

        # CAGR (연환산 수익률)
        days = len(self.history_df)
        years = days / 252  # 연간 거래일 수
        if years > 0:
            cagr = ((final_equity / self.initial_capital) ** (1 / years) - 1) * 100
        else:
            cagr = 0.0

        # 일별 수익률
        self.history_df['daily_return'] = self.history_df['equity'].pct_change() * 100
        daily_return_mean = self.history_df['daily_return'].mean()
        daily_return_std = self.history_df['daily_return'].std()

        # 월별 수익률
        monthly_equity = self.history_df['equity'].resample('ME').last()
        monthly_returns = monthly_equity.pct_change() * 100
        monthly_returns_dict = {
            date.strftime('%Y-%m'): ret
            for date, ret in monthly_returns.items()
            if not np.isnan(ret)
        }

        return {
            'total_return': total_return,
            'cagr': cagr,
            'daily_return_mean': daily_return_mean,
            'daily_return_std': daily_return_std,
            'monthly_returns': monthly_returns_dict
        }

    def calculate_sharpe_ratio(
        self,
        risk_free_rate: float = 0.03
    ) -> float:
        """
        샤프 비율 계산

        Args:
            risk_free_rate: 무위험 수익률 (연율, 기본값: 3%)

        Returns:
            float: 샤프 비율

        Notes:
            Sharpe Ratio = (수익률 - 무위험수익률) / 변동성

            해석:
            - > 2.0: 매우 우수
            - 1.0 ~ 2.0: 우수
            - 0.5 ~ 1.0: 양호
            - < 0.5: 개선 필요

        Examples:
            >>> analyzer = PerformanceAnalyzer(history, trades, 10_000_000)
            >>> sharpe = analyzer.calculate_sharpe_ratio()
            >>> print(f"샤프 비율: {sharpe:.2f}")
        """
        if self.history_df.empty or 'daily_return' not in self.history_df.columns:
            self.calculate_returns()  # 일별 수익률 계산

        if self.history_df.empty:
            return 0.0

        # 일별 수익률
        daily_returns = self.history_df['daily_return'].dropna()

        if len(daily_returns) == 0 or daily_returns.std() == 0:
            return 0.0

        # 일별 무위험 수익률
        daily_risk_free = (risk_free_rate / 252) * 100

        # 샤프 비율 (연환산)
        excess_return = daily_returns.mean() - daily_risk_free
        sharpe_ratio = (excess_return / daily_returns.std()) * np.sqrt(252)

        return sharpe_ratio

    def calculate_max_drawdown(self) -> Dict[str, Any]:
        """
        최대 낙폭 계산

        Returns:
            Dict: MDD 정보
                - max_drawdown: 최대 낙폭 (%)
                - peak_date: 고점 날짜
                - trough_date: 저점 날짜
                - recovery_date: 회복 날짜 (None이면 미회복)
                - duration_days: 낙폭 기간 (일)

        Notes:
            MDD = (고점 - 저점) / 고점 × 100

            권장 기준:
            - < 10%: 매우 우수
            - 10% ~ 20%: 우수
            - 20% ~ 30%: 양호
            - > 30%: 개선 필요

        Examples:
            >>> analyzer = PerformanceAnalyzer(history, trades, 10_000_000)
            >>> mdd = analyzer.calculate_max_drawdown()
            >>> print(f"최대 낙폭: {mdd['max_drawdown']:.2f}%")
            >>> print(f"낙폭 기간: {mdd['duration_days']}일")
        """
        if self.history_df.empty:
            return {
                'max_drawdown': 0.0,
                'peak_date': None,
                'trough_date': None,
                'recovery_date': None,
                'duration_days': 0
            }

        equity = self.history_df['equity']

        # 누적 최고점
        cummax = equity.cummax()

        # 낙폭 계산
        drawdown = (equity - cummax) / cummax * 100

        # 최대 낙폭
        max_dd = drawdown.min()
        trough_idx = drawdown.idxmin()

        # 고점 날짜 (저점 이전의 최고점)
        peak_equity = cummax.loc[trough_idx]
        peak_idx = equity[:trough_idx][equity[:trough_idx] == peak_equity].index[-1]

        # 회복 날짜 (저점 이후 고점을 회복한 날짜)
        recovery_idx = None
        if trough_idx < equity.index[-1]:
            recovery_series = equity[trough_idx:][equity[trough_idx:] >= peak_equity]
            if len(recovery_series) > 0:
                recovery_idx = recovery_series.index[0]

        # 낙폭 기간
        if recovery_idx:
            duration = (recovery_idx - peak_idx).days
        else:
            duration = (equity.index[-1] - peak_idx).days

        return {
            'max_drawdown': abs(max_dd),
            'peak_date': peak_idx.strftime('%Y-%m-%d'),
            'trough_date': trough_idx.strftime('%Y-%m-%d'),
            'recovery_date': recovery_idx.strftime('%Y-%m-%d') if recovery_idx else None,
            'duration_days': duration
        }

    def calculate_win_rate(self) -> Dict[str, Any]:
        """
        승률 계산

        Returns:
            Dict: 승률 정보
                - total_trades: 총 거래 수
                - winning_trades: 수익 거래 수
                - losing_trades: 손실 거래 수
                - win_rate: 승률 (%)
                - avg_win: 평균 수익 (원)
                - avg_loss: 평균 손실 (원)

        Examples:
            >>> analyzer = PerformanceAnalyzer(history, trades, 10_000_000)
            >>> win_rate = analyzer.calculate_win_rate()
            >>> print(f"승률: {win_rate['win_rate']:.2f}%")
        """
        if self.trades_df.empty or 'pnl' not in self.trades_df.columns:
            return {
                'total_trades': 0,
                'winning_trades': 0,
                'losing_trades': 0,
                'win_rate': 0.0,
                'avg_win': 0.0,
                'avg_loss': 0.0
            }

        total_trades = len(self.trades_df)
        winning_trades = len(self.trades_df[self.trades_df['pnl'] > 0])
        losing_trades = len(self.trades_df[self.trades_df['pnl'] < 0])

        win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0.0

        # 평균 수익/손실
        wins = self.trades_df[self.trades_df['pnl'] > 0]['pnl']
        losses = self.trades_df[self.trades_df['pnl'] < 0]['pnl']

        avg_win = wins.mean() if len(wins) > 0 else 0.0
        avg_loss = losses.mean() if len(losses) > 0 else 0.0

        return {
            'total_trades': total_trades,
            'winning_trades': winning_trades,
            'losing_trades': losing_trades,
            'win_rate': win_rate,
            'avg_win': avg_win,
            'avg_loss': avg_loss
        }

    def calculate_profit_factor(self) -> float:
        """
        손익비 계산

        Returns:
            float: 손익비 (총 수익 / 총 손실)

        Notes:
            - > 2.0: 매우 우수
            - 1.5 ~ 2.0: 우수
            - 1.0 ~ 1.5: 양호
            - < 1.0: 개선 필요

        Examples:
            >>> analyzer = PerformanceAnalyzer(history, trades, 10_000_000)
            >>> pf = analyzer.calculate_profit_factor()
            >>> print(f"손익비: {pf:.2f}")
        """
        if self.trades_df.empty or 'pnl' not in self.trades_df.columns:
            return 0.0

        total_profit = self.trades_df[self.trades_df['pnl'] > 0]['pnl'].sum()
        total_loss = abs(self.trades_df[self.trades_df['pnl'] < 0]['pnl'].sum())

        if total_loss == 0:
            return float('inf') if total_profit > 0 else 0.0

        return total_profit / total_loss

    def generate_report(self) -> str:
        """
        종합 리포트 생성

        Returns:
            str: 종합 성과 리포트

        Examples:
            >>> analyzer = PerformanceAnalyzer(history, trades, 10_000_000)
            >>> report = analyzer.generate_report()
            >>> print(report)
        """
        returns = self.calculate_returns()
        sharpe = self.calculate_sharpe_ratio()
        mdd = self.calculate_max_drawdown()
        win_rate = self.calculate_win_rate()
        profit_factor = self.calculate_profit_factor()

        report_lines = [
            "=" * 70,
            "백테스팅 성과 분석 리포트",
            "=" * 70,
            "",
            "=== 수익률 지표 ===",
            f"초기 자본: {self.initial_capital:,.0f}원",
            f"최종 자본: {self.history_df['equity'].iloc[-1]:,.0f}원" if not self.history_df.empty else "최종 자본: N/A",
            f"총 수익률: {returns['total_return']:.2f}%",
            f"연환산 수익률(CAGR): {returns['cagr']:.2f}%",
            f"일평균 수익률: {returns['daily_return_mean']:.4f}%",
            f"일수익률 표준편차: {returns['daily_return_std']:.4f}%",
            "",
            "=== 리스크 지표 ===",
            f"샤프 비율: {sharpe:.2f}",
            f"최대 낙폭(MDD): {mdd['max_drawdown']:.2f}%",
            f"  - 고점: {mdd['peak_date']}",
            f"  - 저점: {mdd['trough_date']}",
            f"  - 회복: {mdd['recovery_date'] or '미회복'}",
            f"  - 기간: {mdd['duration_days']}일",
            "",
            "=== 거래 통계 ===",
            f"총 거래 수: {win_rate['total_trades']}건",
            f"수익 거래: {win_rate['winning_trades']}건",
            f"손실 거래: {win_rate['losing_trades']}건",
            f"승률: {win_rate['win_rate']:.2f}%",
            f"평균 수익: {win_rate['avg_win']:,.0f}원",
            f"평균 손실: {win_rate['avg_loss']:,.0f}원",
            f"손익비(Profit Factor): {profit_factor:.2f}",
            "",
            "=== 월별 수익률 (최근 12개월) ===",
        ]

        # 월별 수익률 (최근 12개월)
        monthly_returns = returns['monthly_returns']
        for month in sorted(monthly_returns.keys())[-12:]:
            ret = monthly_returns[month]
            report_lines.append(f"{month}: {ret:+.2f}%")

        report_lines.append("=" * 70)

        return "\n".join(report_lines)

    def plot_equity_curve(self, filepath: Optional[str] = None) -> None:
        """
        자산곡선 차트 생성

        Args:
            filepath: 저장할 파일 경로 (None이면 표시만)

        Examples:
            >>> analyzer = PerformanceAnalyzer(history, trades, 10_000_000)
            >>> analyzer.plot_equity_curve('equity_curve.png')
        """
        try:
            import matplotlib.pyplot as plt
        except ImportError:
            logger.warning("matplotlib이 설치되어 있지 않습니다.")
            return

        if self.history_df.empty:
            logger.warning("포트폴리오 히스토리가 없습니다.")
            return

        plt.figure(figsize=(12, 6))
        plt.plot(self.history_df.index, self.history_df['equity'], linewidth=2)
        plt.title('자산 곡선 (Equity Curve)', fontsize=16)
        plt.xlabel('날짜', fontsize=12)
        plt.ylabel('자산 (원)', fontsize=12)
        plt.grid(True, alpha=0.3)
        plt.tight_layout()

        if filepath:
            plt.savefig(filepath, dpi=300, bbox_inches='tight')
            logger.info(f"자산곡선 차트 저장: {filepath}")
        else:
            plt.show()

        plt.close()

    def plot_drawdown(self, filepath: Optional[str] = None) -> None:
        """
        낙폭 차트 생성

        Args:
            filepath: 저장할 파일 경로 (None이면 표시만)

        Examples:
            >>> analyzer = PerformanceAnalyzer(history, trades, 10_000_000)
            >>> analyzer.plot_drawdown('drawdown.png')
        """
        try:
            import matplotlib.pyplot as plt
        except ImportError:
            logger.warning("matplotlib이 설치되어 있지 않습니다.")
            return

        if self.history_df.empty:
            logger.warning("포트폴리오 히스토리가 없습니다.")
            return

        equity = self.history_df['equity']
        cummax = equity.cummax()
        drawdown = (equity - cummax) / cummax * 100

        plt.figure(figsize=(12, 6))
        plt.fill_between(drawdown.index, drawdown, 0, alpha=0.3, color='red')
        plt.plot(drawdown.index, drawdown, color='red', linewidth=2)
        plt.title('낙폭 (Drawdown)', fontsize=16)
        plt.xlabel('날짜', fontsize=12)
        plt.ylabel('낙폭 (%)', fontsize=12)
        plt.grid(True, alpha=0.3)
        plt.tight_layout()

        if filepath:
            plt.savefig(filepath, dpi=300, bbox_inches='tight')
            logger.info(f"낙폭 차트 저장: {filepath}")
        else:
            plt.show()

        plt.close()

    def export_trades(self, filepath: str) -> None:
        """
        거래 내역 CSV export

        Args:
            filepath: 저장할 CSV 파일 경로

        Examples:
            >>> analyzer = PerformanceAnalyzer(history, trades, 10_000_000)
            >>> analyzer.export_trades('trades.csv')
        """
        if self.trades_df.empty:
            logger.warning("거래 내역이 없습니다.")
            return

        self.trades_df.to_csv(filepath, index=False, encoding='utf-8-sig')
        logger.info(f"거래 내역 저장: {filepath} ({len(self.trades_df)}건)")
