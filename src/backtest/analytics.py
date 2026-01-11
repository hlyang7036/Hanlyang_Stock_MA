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

    def calculate_sortino_ratio(
        self,
        risk_free_rate: float = 0.03,
        target_return: float = 0.0
    ) -> float:
        """
        소르티노 비율 계산

        샤프 비율과 달리 하방 변동성(downside deviation)만 고려합니다.
        손실 위험에 대한 보상을 더 정확하게 측정합니다.

        Args:
            risk_free_rate: 무위험 수익률 (연율, 기본값: 3%)
            target_return: 목표 수익률 (연율, 기본값: 0%)

        Returns:
            float: 소르티노 비율

        Notes:
            공식: (수익률 - 목표수익률) / 하방편차

            해석:
            - > 2.0: 매우 우수
            - 1.0 ~ 2.0: 우수
            - 0.5 ~ 1.0: 양호
            - < 0.5: 개선 필요

        Examples:
            >>> analyzer = PerformanceAnalyzer(history, trades, 10_000_000)
            >>> sortino = analyzer.calculate_sortino_ratio()
            >>> print(f"소르티노 비율: {sortino:.2f}")
        """
        if self.history_df.empty or 'daily_return' not in self.history_df.columns:
            self.calculate_returns()  # 일별 수익률 계산

        if self.history_df.empty:
            return 0.0

        # 일별 수익률
        daily_returns = self.history_df['daily_return'].dropna()

        if len(daily_returns) == 0:
            return 0.0

        # 일별 목표 수익률
        daily_target = (target_return / 252) * 100

        # 하방 편차 계산 (목표 수익률 미달 수익률만 고려)
        downside_returns = daily_returns[daily_returns < daily_target]

        if len(downside_returns) == 0:
            # 모든 수익률이 목표 이상
            return float('inf') if daily_returns.mean() > daily_target else 0.0

        downside_deviation = downside_returns.std()

        if downside_deviation == 0:
            return 0.0

        # 일별 무위험 수익률
        daily_risk_free = (risk_free_rate / 252) * 100

        # 소르티노 비율 (연환산)
        excess_return = daily_returns.mean() - daily_risk_free
        sortino_ratio = (excess_return / downside_deviation) * np.sqrt(252)

        return sortino_ratio

    def calculate_calmar_ratio(self) -> float:
        """
        칼마 비율 계산

        연환산 수익률 대비 최대 낙폭 비율입니다.

        Returns:
            float: 칼마 비율

        Notes:
            공식: CAGR / MDD

            해석:
            - > 3.0: 매우 우수
            - 1.0 ~ 3.0: 우수
            - 0.5 ~ 1.0: 양호
            - < 0.5: 개선 필요

        Examples:
            >>> analyzer = PerformanceAnalyzer(history, trades, 10_000_000)
            >>> calmar = analyzer.calculate_calmar_ratio()
            >>> print(f"칼마 비율: {calmar:.2f}")
        """
        returns = self.calculate_returns()
        cagr = returns['cagr']

        mdd_info = self.calculate_max_drawdown()
        mdd = mdd_info['max_drawdown']

        if mdd == 0:
            return float('inf') if cagr > 0 else 0.0

        return cagr / mdd

    def calculate_recovery_factor(self) -> float:
        """
        회복 팩터 계산

        순이익 대비 최대 낙폭 비율입니다.
        전략이 MDD에서 얼마나 빠르게 회복하는지 측정합니다.

        Returns:
            float: 회복 팩터

        Notes:
            공식: 순이익(원) / 최대낙폭금액(원)

            해석:
            - 높을수록 손실 대비 수익 회복력이 우수

        Examples:
            >>> analyzer = PerformanceAnalyzer(history, trades, 10_000_000)
            >>> recovery = analyzer.calculate_recovery_factor()
            >>> print(f"회복 팩터: {recovery:.2f}")
        """
        if self.history_df.empty:
            return 0.0

        # 순이익 (원)
        final_equity = self.history_df['equity'].iloc[-1]
        net_profit = final_equity - self.initial_capital

        # MDD 금액 계산
        mdd_info = self.calculate_max_drawdown()
        mdd_pct = mdd_info['max_drawdown']

        if mdd_pct == 0:
            return float('inf') if net_profit > 0 else 0.0

        # MDD를 금액으로 환산
        equity = self.history_df['equity']
        cummax = equity.cummax()
        drawdown_amount = (cummax - equity).max()

        if drawdown_amount == 0:
            return float('inf') if net_profit > 0 else 0.0

        return net_profit / drawdown_amount

    def calculate_risk_reward_ratio(self) -> float:
        """
        위험보상비율 계산

        평균 수익 대비 평균 손실 비율입니다.

        Returns:
            float: 위험보상비율

        Notes:
            공식: |평균 수익| / |평균 손실|

            해석:
            - > 2.0: 우수 (손실 대비 수익이 2배 이상)
            - 1.5 ~ 2.0: 양호
            - 1.0 ~ 1.5: 보통
            - < 1.0: 개선 필요 (손실이 수익보다 큼)

        Examples:
            >>> analyzer = PerformanceAnalyzer(history, trades, 10_000_000)
            >>> rr = analyzer.calculate_risk_reward_ratio()
            >>> print(f"위험보상비율: {rr:.2f}")
        """
        win_rate_info = self.calculate_win_rate()
        avg_win = win_rate_info['avg_win']
        avg_loss = win_rate_info['avg_loss']

        if avg_loss == 0:
            return float('inf') if avg_win > 0 else 0.0

        return abs(avg_win / avg_loss)

    def calculate_expected_value(self) -> float:
        """
        기대값 계산

        거래당 기대 수익을 계산합니다.

        Returns:
            float: 거래당 기대값 (원)

        Notes:
            공식: (승률 × 평균수익) - (패률 × |평균손실|)

            양수면 장기적으로 수익, 음수면 장기적으로 손실

        Examples:
            >>> analyzer = PerformanceAnalyzer(history, trades, 10_000_000)
            >>> ev = analyzer.calculate_expected_value()
            >>> print(f"거래당 기대값: {ev:,.0f}원")
        """
        win_rate_info = self.calculate_win_rate()

        win_rate = win_rate_info['win_rate'] / 100  # 백분율 -> 비율
        loss_rate = 1 - win_rate
        avg_win = win_rate_info['avg_win']
        avg_loss = abs(win_rate_info['avg_loss'])

        expected_value = (win_rate * avg_win) - (loss_rate * avg_loss)

        return expected_value

    def calculate_consecutive_stats(self) -> Dict[str, Any]:
        """
        연속 거래 통계

        연속 승패 패턴을 분석합니다.

        Returns:
            Dict: 연속 거래 통계
                - max_consecutive_wins: 최대 연속 수익 거래
                - max_consecutive_losses: 최대 연속 손실 거래
                - avg_consecutive_wins: 평균 연속 수익 거래
                - avg_consecutive_losses: 평균 연속 손실 거래

        Notes:
            최대 연속 손실은 자금 관리에 매우 중요합니다.

        Examples:
            >>> analyzer = PerformanceAnalyzer(history, trades, 10_000_000)
            >>> stats = analyzer.calculate_consecutive_stats()
            >>> print(f"최대 연속 손실: {stats['max_consecutive_losses']}회")
        """
        if self.trades_df.empty or 'pnl' not in self.trades_df.columns:
            return {
                'max_consecutive_wins': 0,
                'max_consecutive_losses': 0,
                'avg_consecutive_wins': 0.0,
                'avg_consecutive_losses': 0.0
            }

        # 승패 판정 (True: 수익, False: 손실)
        is_win = self.trades_df['pnl'] > 0

        # 연속 승패 카운트
        win_streaks = []
        loss_streaks = []

        current_streak = 0
        current_type = None

        for win in is_win:
            if win:
                if current_type == 'win':
                    current_streak += 1
                else:
                    if current_type == 'loss' and current_streak > 0:
                        loss_streaks.append(current_streak)
                    current_streak = 1
                    current_type = 'win'
            else:
                if current_type == 'loss':
                    current_streak += 1
                else:
                    if current_type == 'win' and current_streak > 0:
                        win_streaks.append(current_streak)
                    current_streak = 1
                    current_type = 'loss'

        # 마지막 연속 기록 추가
        if current_type == 'win' and current_streak > 0:
            win_streaks.append(current_streak)
        elif current_type == 'loss' and current_streak > 0:
            loss_streaks.append(current_streak)

        return {
            'max_consecutive_wins': max(win_streaks) if win_streaks else 0,
            'max_consecutive_losses': max(loss_streaks) if loss_streaks else 0,
            'avg_consecutive_wins': np.mean(win_streaks) if win_streaks else 0.0,
            'avg_consecutive_losses': np.mean(loss_streaks) if loss_streaks else 0.0
        }

    def calculate_holding_period(self) -> Dict[str, Any]:
        """
        보유 기간 분석

        수익/손실 거래별 평균 보유 기간을 분석합니다.

        Returns:
            Dict: 보유 기간 통계
                - avg_holding_days: 평균 보유 일수
                - min_holding_days: 최소 보유 일수
                - max_holding_days: 최대 보유 일수
                - avg_winning_holding_days: 수익 거래 평균 보유 일수
                - avg_losing_holding_days: 손실 거래 평균 보유 일수

        Notes:
            수익/손실 거래별 보유 기간 차이 분석
            "손절은 빠르게, 수익은 길게" 원칙 검증

        Examples:
            >>> analyzer = PerformanceAnalyzer(history, trades, 10_000_000)
            >>> holding = analyzer.calculate_holding_period()
            >>> print(f"평균 보유: {holding['avg_holding_days']:.1f}일")
        """
        if self.trades_df.empty or 'holding_days' not in self.trades_df.columns:
            return {
                'avg_holding_days': 0.0,
                'min_holding_days': 0,
                'max_holding_days': 0,
                'avg_winning_holding_days': 0.0,
                'avg_losing_holding_days': 0.0
            }

        # 전체 통계
        avg_holding = self.trades_df['holding_days'].mean()
        min_holding = self.trades_df['holding_days'].min()
        max_holding = self.trades_df['holding_days'].max()

        # 수익/손실별 통계
        winning_trades = self.trades_df[self.trades_df['pnl'] > 0]
        losing_trades = self.trades_df[self.trades_df['pnl'] < 0]

        avg_winning_holding = winning_trades['holding_days'].mean() if len(winning_trades) > 0 else 0.0
        avg_losing_holding = losing_trades['holding_days'].mean() if len(losing_trades) > 0 else 0.0

        return {
            'avg_holding_days': avg_holding,
            'min_holding_days': min_holding,
            'max_holding_days': max_holding,
            'avg_winning_holding_days': avg_winning_holding,
            'avg_losing_holding_days': avg_losing_holding
        }

    def analyze_by_exit_reason(self) -> Dict[str, Dict[str, Any]]:
        """
        청산 사유별 성과 분석

        손절, 신호청산 등 청산 사유별로 성과를 분석합니다.

        Returns:
            Dict: 청산 사유별 통계
                {
                    'reason_name': {
                        'count': int,
                        'total_pnl': float,
                        'avg_pnl': float,
                        'win_rate': float
                    },
                    ...
                }

        Notes:
            손절 vs 신호청산 효과 비교
            각 청산 방법의 효율성 검증

        Examples:
            >>> analyzer = PerformanceAnalyzer(history, trades, 10_000_000)
            >>> reasons = analyzer.analyze_by_exit_reason()
            >>> for reason, stats in reasons.items():
            ...     print(f"{reason}: {stats['count']}건, 평균 {stats['avg_pnl']:,.0f}원")
        """
        if self.trades_df.empty or 'reason' not in self.trades_df.columns:
            return {}

        # 청산 사유별 그룹화
        result = {}

        for reason in self.trades_df['reason'].unique():
            reason_trades = self.trades_df[self.trades_df['reason'] == reason]

            count = len(reason_trades)
            total_pnl = reason_trades['pnl'].sum()
            avg_pnl = reason_trades['pnl'].mean()

            winning_count = len(reason_trades[reason_trades['pnl'] > 0])
            win_rate = (winning_count / count * 100) if count > 0 else 0.0

            result[reason] = {
                'count': count,
                'total_pnl': total_pnl,
                'avg_pnl': avg_pnl,
                'win_rate': win_rate
            }

        return result

    def analyze_by_entry_stage(self) -> Dict[str, Dict[str, Any]]:
        """
        진입 스테이지별 성과 분석

        조기 진입(Stage 5) vs 통상 진입(Stage 6) 효과를 비교합니다.

        Returns:
            Dict: 스테이지별 통계
                {
                    'stage_N': {
                        'count': int,
                        'total_pnl': float,
                        'avg_pnl': float,
                        'win_rate': float
                    },
                    ...
                }

        Notes:
            조기진입(Stage 5) vs 통상진입(Stage 6) 효과 비교
            스테이지별 수익성 검증

        Examples:
            >>> analyzer = PerformanceAnalyzer(history, trades, 10_000_000)
            >>> stages = analyzer.analyze_by_entry_stage()
            >>> for stage, stats in stages.items():
            ...     print(f"{stage}: 승률 {stats['win_rate']:.1f}%")
        """
        if self.trades_df.empty or 'entry_stage' not in self.trades_df.columns:
            return {}

        # 스테이지별 그룹화
        result = {}

        for stage in self.trades_df['entry_stage'].unique():
            if pd.isna(stage):
                continue

            stage_trades = self.trades_df[self.trades_df['entry_stage'] == stage]

            count = len(stage_trades)
            total_pnl = stage_trades['pnl'].sum()
            avg_pnl = stage_trades['pnl'].mean()

            winning_count = len(stage_trades[stage_trades['pnl'] > 0])
            win_rate = (winning_count / count * 100) if count > 0 else 0.0

            result[f'stage_{int(stage)}'] = {
                'count': count,
                'total_pnl': total_pnl,
                'avg_pnl': avg_pnl,
                'win_rate': win_rate
            }

        return result

    def analyze_by_entry_strategy(self) -> Dict[str, Dict[str, Any]]:
        """
        진입 전략별 성과 분석

        역발상 매수 vs 일반 매수 등 전략별 효과를 비교합니다.

        Returns:
            Dict: 전략별 통계
                {
                    'contrarian_buy': {
                        'count': int,
                        'total_pnl': float,
                        'avg_pnl': float,
                        'win_rate': float,
                        'avg_holding_days': float
                    },
                    'normal_buy': {...},
                    'early_buy': {...},
                    'early_contrarian_buy': {...}
                }

        Notes:
            - contrarian_buy: 역발상 매수 (Stage 3)
            - early_contrarian_buy: 조기 역발상 매수 (Stage 2)
            - normal_buy: 일반 매수 (Stage 6)
            - early_buy: 조기 매수 (Stage 5)

        Examples:
            >>> analyzer = PerformanceAnalyzer(history, trades, 10_000_000)
            >>> strategies = analyzer.analyze_by_entry_strategy()
            >>> for strategy, stats in strategies.items():
            ...     print(f"{strategy}: 승률 {stats['win_rate']:.1f}%")
        """
        if self.trades_df.empty or 'entry_strategy' not in self.trades_df.columns:
            return {}

        # 전략별 그룹화
        result = {}

        for strategy in self.trades_df['entry_strategy'].unique():
            if pd.isna(strategy):
                continue

            strategy_trades = self.trades_df[self.trades_df['entry_strategy'] == strategy]

            count = len(strategy_trades)
            total_pnl = strategy_trades['pnl'].sum()
            avg_pnl = strategy_trades['pnl'].mean()

            winning_count = len(strategy_trades[strategy_trades['pnl'] > 0])
            win_rate = (winning_count / count * 100) if count > 0 else 0.0

            avg_holding = strategy_trades['holding_days'].mean() if 'holding_days' in strategy_trades.columns else 0.0

            result[strategy] = {
                'count': count,
                'total_pnl': total_pnl,
                'avg_pnl': avg_pnl,
                'win_rate': win_rate,
                'avg_holding_days': avg_holding
            }

        return result

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
        # 기존 지표 계산
        returns = self.calculate_returns()
        sharpe = self.calculate_sharpe_ratio()
        mdd = self.calculate_max_drawdown()
        win_rate = self.calculate_win_rate()
        profit_factor = self.calculate_profit_factor()

        # Phase 1 신규 지표 계산
        sortino = self.calculate_sortino_ratio()
        calmar = self.calculate_calmar_ratio()
        recovery = self.calculate_recovery_factor()
        risk_reward = self.calculate_risk_reward_ratio()
        expected_value = self.calculate_expected_value()
        consecutive = self.calculate_consecutive_stats()

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
            f"소르티노 비율: {sortino:.2f}",
            f"칼마 비율: {calmar:.2f}",
            f"회복 팩터: {recovery:.2f}",
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
            f"위험보상비율(R/R): {risk_reward:.2f}",
            f"거래당 기대값: {expected_value:,.0f}원",
            "",
            "=== 연속 거래 분석 ===",
            f"최대 연속 수익: {consecutive['max_consecutive_wins']}회",
            f"최대 연속 손실: {consecutive['max_consecutive_losses']}회",
            f"평균 연속 수익: {consecutive['avg_consecutive_wins']:.1f}회",
            f"평균 연속 손실: {consecutive['avg_consecutive_losses']:.1f}회",
            "",
        ]

        # Phase 2 분석 추가
        holding = self.calculate_holding_period()
        if holding['avg_holding_days'] > 0:
            report_lines.extend([
                "=== 보유 기간 분석 ===",
                f"평균 보유 기간: {holding['avg_holding_days']:.1f}일",
                f"최소/최대 보유: {holding['min_holding_days']}일 / {holding['max_holding_days']}일",
                f"수익 거래 평균 보유: {holding['avg_winning_holding_days']:.1f}일",
                f"손실 거래 평균 보유: {holding['avg_losing_holding_days']:.1f}일",
                "",
            ])

        exit_reasons = self.analyze_by_exit_reason()
        if exit_reasons:
            report_lines.append("=== 청산 사유별 분석 ===")
            for reason, stats in exit_reasons.items():
                report_lines.append(
                    f"{reason}: {stats['count']}건 "
                    f"(승률 {stats['win_rate']:.1f}%, "
                    f"평균 {stats['avg_pnl']:,.0f}원)"
                )
            report_lines.append("")

        entry_stages = self.analyze_by_entry_stage()
        if entry_stages:
            report_lines.append("=== 진입 스테이지별 분석 ===")
            for stage, stats in sorted(entry_stages.items()):
                report_lines.append(
                    f"{stage}: {stats['count']}건 "
                    f"(승률 {stats['win_rate']:.1f}%, "
                    f"평균 {stats['avg_pnl']:,.0f}원)"
                )
            report_lines.append("")

        entry_strategies = self.analyze_by_entry_strategy()
        if entry_strategies:
            report_lines.append("=== 진입 전략별 분석 ===")
            for strategy, stats in sorted(entry_strategies.items()):
                report_lines.append(
                    f"{strategy}: {stats['count']}건 "
                    f"(승률 {stats['win_rate']:.1f}%, "
                    f"평균 {stats['avg_pnl']:,.0f}원, "
                    f"평균 보유 {stats['avg_holding_days']:.1f}일)"
                )
            report_lines.append("")

        report_lines.append("=== 월별 수익률 (최근 12개월) ===")

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

    def analyze_stage6_failures(self) -> Dict[str, Any]:
        """
        Stage 6 진입 실패 패턴 분석

        Stage 6은 "상승 변화기2 (강세 가속)"로 상승장 입구이지만,
        실제로는 가짜 신호가 많아 승률이 낮을 수 있습니다.
        이 함수는 Stage 6 진입의 실패 패턴을 분석합니다.

        분석 항목:
        1. Stage 6 진입 종목의 청산 사유별 분포
        2. Stage 6에서 수익/손실 종목의 신호 강도 차이
        3. Stage 6에서 보유 기간 패턴
        4. 승자와 패자의 특징 비교

        Returns:
            Dict[str, Any]: 분석 결과
                - total_count: 총 거래 건수
                - win_rate: 승률 (%)
                - avg_pnl: 평균 손익
                - exit_reason_dist: 청산 사유별 통계 (건수, 평균 손익, 승률)
                - signal_strength_comparison: 신호 강도 비교 (승자 vs 패자)
                - holding_period_stats: 보유 기간 통계
                - stage6_trades: Stage 6 진입 거래 DataFrame

        Examples:
            >>> analyzer = PerformanceAnalyzer(history, trades, 10_000_000)
            >>> stage6_result = analyzer.analyze_stage6_failures()
            >>> print(f"Stage 6 승률: {stage6_result['win_rate']:.1f}%")
        """
        if self.trades_df.empty:
            return {
                'total_count': 0,
                'win_rate': 0.0,
                'message': '거래 내역이 없습니다.'
            }

        # Stage 6 진입 거래 필터링
        stage6_trades = self.trades_df[self.trades_df['entry_stage'] == 6].copy()

        if stage6_trades.empty:
            return {
                'total_count': 0,
                'win_rate': 0.0,
                'message': 'Stage 6 진입 거래가 없습니다.'
            }

        # 기본 통계
        total_count = len(stage6_trades)
        winners = stage6_trades[stage6_trades['pnl'] > 0]
        losers = stage6_trades[stage6_trades['pnl'] <= 0]
        win_rate = len(winners) / total_count * 100
        avg_pnl = stage6_trades['pnl'].mean()

        # 청산 사유별 분포
        exit_reason_dist = {}
        for reason in stage6_trades['reason'].unique():
            reason_trades = stage6_trades[stage6_trades['reason'] == reason]
            exit_reason_dist[reason] = {
                'count': len(reason_trades),
                'avg_pnl': reason_trades['pnl'].mean(),
                'win_rate': (reason_trades['pnl'] > 0).sum() / len(reason_trades) * 100
            }

        # 신호 강도 비교 (signal_strength 필드가 있는 경우)
        signal_strength_comparison = None
        if 'signal_strength' in stage6_trades.columns:
            if not winners.empty and not losers.empty:
                signal_strength_comparison = {
                    'winners_avg_strength': winners['signal_strength'].mean(),
                    'losers_avg_strength': losers['signal_strength'].mean(),
                    'strength_diff': winners['signal_strength'].mean() - losers['signal_strength'].mean(),
                    'winners_min': winners['signal_strength'].min(),
                    'winners_max': winners['signal_strength'].max(),
                    'losers_min': losers['signal_strength'].min(),
                    'losers_max': losers['signal_strength'].max()
                }

        # 보유 기간 패턴
        holding_period_stats = {
            'avg_holding_all': stage6_trades['holding_days'].mean(),
            'avg_holding_winners': winners['holding_days'].mean() if not winners.empty else 0,
            'avg_holding_losers': losers['holding_days'].mean() if not losers.empty else 0,
            'median_holding_all': stage6_trades['holding_days'].median(),
            'max_holding': stage6_trades['holding_days'].max(),
            'min_holding': stage6_trades['holding_days'].min()
        }

        return {
            'total_count': total_count,
            'win_count': len(winners),
            'loss_count': len(losers),
            'win_rate': win_rate,
            'avg_pnl': avg_pnl,
            'avg_win': winners['pnl'].mean() if not winners.empty else 0,
            'avg_loss': losers['pnl'].mean() if not losers.empty else 0,
            'exit_reason_dist': exit_reason_dist,
            'signal_strength_comparison': signal_strength_comparison,
            'holding_period_stats': holding_period_stats,
            'stage6_trades': stage6_trades
        }

    def analyze_stage3_success(self) -> Dict[str, Any]:
        """
        Stage 3 진입 성공 패턴 분석

        Stage 3은 "하락 변화기2 (약세 가속)"로 일반적으로 매수 청산 시점이지만,
        역발상 매수 시 바닥 반등을 잡을 수 있습니다.
        이 함수는 Stage 3 진입의 성공 패턴을 분석합니다.

        분석 항목:
        1. Stage 3 진입 종목의 청산 사유별 분포
        2. Stage 3에서 큰 수익이 발생하는 이유
        3. 보유 기간 패턴
        4. 신호 강도 분석

        Returns:
            Dict[str, Any]: 분석 결과
                - total_count: 총 거래 건수
                - win_rate: 승률 (%)
                - avg_pnl: 평균 손익
                - exit_reason_dist: 청산 사유별 통계
                - signal_strength_stats: 신호 강도 통계
                - holding_period_stats: 보유 기간 통계
                - stage3_trades: Stage 3 진입 거래 DataFrame

        Examples:
            >>> analyzer = PerformanceAnalyzer(history, trades, 10_000_000)
            >>> stage3_result = analyzer.analyze_stage3_success()
            >>> print(f"Stage 3 평균 수익: {stage3_result['avg_pnl']:,.0f}원")
        """
        if self.trades_df.empty:
            return {
                'total_count': 0,
                'win_rate': 0.0,
                'message': '거래 내역이 없습니다.'
            }

        # Stage 3 진입 거래 필터링
        stage3_trades = self.trades_df[self.trades_df['entry_stage'] == 3].copy()

        if stage3_trades.empty:
            return {
                'total_count': 0,
                'win_rate': 0.0,
                'message': 'Stage 3 진입 거래가 없습니다.'
            }

        # 기본 통계
        total_count = len(stage3_trades)
        winners = stage3_trades[stage3_trades['pnl'] > 0]
        losers = stage3_trades[stage3_trades['pnl'] <= 0]
        win_rate = len(winners) / total_count * 100
        avg_pnl = stage3_trades['pnl'].mean()

        # 청산 사유별 분포
        exit_reason_dist = {}
        for reason in stage3_trades['reason'].unique():
            reason_trades = stage3_trades[stage3_trades['reason'] == reason]
            exit_reason_dist[reason] = {
                'count': len(reason_trades),
                'avg_pnl': reason_trades['pnl'].mean(),
                'win_rate': (reason_trades['pnl'] > 0).sum() / len(reason_trades) * 100
            }

        # 신호 강도 분석 (signal_strength 필드가 있는 경우)
        signal_strength_stats = None
        if 'signal_strength' in stage3_trades.columns:
            signal_strength_stats = {
                'avg_strength': stage3_trades['signal_strength'].mean(),
                'median_strength': stage3_trades['signal_strength'].median(),
                'min_strength': stage3_trades['signal_strength'].min(),
                'max_strength': stage3_trades['signal_strength'].max(),
                'std_strength': stage3_trades['signal_strength'].std()
            }

        # 보유 기간 패턴
        holding_period_stats = {
            'avg_holding_all': stage3_trades['holding_days'].mean(),
            'avg_holding_winners': winners['holding_days'].mean() if not winners.empty else 0,
            'avg_holding_losers': losers['holding_days'].mean() if not losers.empty else 0,
            'median_holding_all': stage3_trades['holding_days'].median(),
            'max_holding': stage3_trades['holding_days'].max(),
            'min_holding': stage3_trades['holding_days'].min()
        }

        # 수익 분포 분석
        pnl_distribution = {
            'max_profit': stage3_trades['pnl'].max(),
            'min_profit': stage3_trades['pnl'].min(),
            'median_profit': stage3_trades['pnl'].median(),
            'std_profit': stage3_trades['pnl'].std()
        }

        return {
            'total_count': total_count,
            'win_count': len(winners),
            'loss_count': len(losers),
            'win_rate': win_rate,
            'avg_pnl': avg_pnl,
            'avg_win': winners['pnl'].mean() if not winners.empty else 0,
            'avg_loss': losers['pnl'].mean() if not losers.empty else 0,
            'exit_reason_dist': exit_reason_dist,
            'signal_strength_stats': signal_strength_stats,
            'holding_period_stats': holding_period_stats,
            'pnl_distribution': pnl_distribution,
            'stage3_trades': stage3_trades
        }

    def analyze_stage_exit_cross(self) -> pd.DataFrame:
        """
        진입 스테이지 × 청산 사유 교차 분석

        각 스테이지에서 진입한 거래들이 어떤 청산 사유로 끝나는지를
        교차 분석하여 패턴을 파악합니다.

        Returns:
            pd.DataFrame: 교차 분석 결과 (MultiIndex DataFrame)
                - Index: entry_stage
                - Columns: reason (청산 사유)
                - Values: count (건수), mean (평균 손익)

        Notes:
            - Stage 3 진입은 대부분 trailing_stop으로 수익 실현
            - Stage 6 진입은 stop_loss로 손실이 많이 발생
            이런 패턴을 확인할 수 있습니다.

        Examples:
            >>> analyzer = PerformanceAnalyzer(history, trades, 10_000_000)
            >>> cross_table = analyzer.analyze_stage_exit_cross()
            >>> print(cross_table)
        """
        if self.trades_df.empty:
            logger.warning("거래 내역이 없습니다.")
            return pd.DataFrame()

        # 교차 분석: entry_stage × reason
        cross_table = pd.crosstab(
            self.trades_df['entry_stage'],
            self.trades_df['reason'],
            values=self.trades_df['pnl'],
            aggfunc=['count', 'mean'],
            margins=True,  # 합계 행/열 추가
            margins_name='Total'
        )

        return cross_table
