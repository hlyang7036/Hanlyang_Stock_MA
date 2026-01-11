"""
백테스팅 메인 엔진 모듈

전체 백테스팅 프로세스를 관리하고 실행합니다.
일별 시뮬레이션, 신호 처리, 리스크 관리를 통합합니다.
"""

import pandas as pd
from typing import Dict, List, Any, Optional
from datetime import datetime
from dataclasses import dataclass
import logging

from src.backtest.portfolio import Portfolio, Position
from src.backtest.execution import ExecutionEngine, Order
from src.backtest.data_manager import DataManager

logger = logging.getLogger(__name__)


@dataclass
class BacktestResult:
    """
    백테스팅 결과

    Attributes:
        start_date: 백테스팅 시작일
        end_date: 백테스팅 종료일
        initial_capital: 초기 자본금
        final_capital: 최종 자본금
        total_return: 총 수익률 (%)
        max_drawdown: 최대 낙폭 (%)
        total_trades: 총 거래 수
        winning_trades: 수익 거래 수
        losing_trades: 손실 거래 수
        win_rate: 승률 (%)
        portfolio_history: 포트폴리오 히스토리
        trades: 거래 내역
        market_count: 스캔한 종목 수
    """
    start_date: str
    end_date: str
    initial_capital: float
    final_capital: float
    total_return: float
    max_drawdown: float
    total_trades: int
    winning_trades: int
    losing_trades: int
    win_rate: float
    portfolio_history: List[Dict[str, Any]]
    trades: List[Dict[str, Any]]
    market_count: int

    def summary(self) -> str:
        """
        백테스팅 결과 요약

        Returns:
            str: 요약 문자열
        """
        summary_lines = [
            "=" * 60,
            "백테스팅 결과 요약",
            "=" * 60,
            f"기간: {self.start_date} ~ {self.end_date}",
            f"시장: {self.market_count}개 종목 스캔",
            "",
            "=== 수익 지표 ===",
            f"초기 자본: {self.initial_capital:,.0f}원",
            f"최종 자본: {self.final_capital:,.0f}원",
            f"총 수익률: {self.total_return:.2f}%",
            f"최대 낙폭: {self.max_drawdown:.2f}%",
            "",
            "=== 거래 통계 ===",
            f"총 거래 수: {self.total_trades}건",
            f"수익 거래: {self.winning_trades}건",
            f"손실 거래: {self.losing_trades}건",
            f"승률: {self.win_rate:.2f}%",
            "=" * 60,
        ]
        return "\n".join(summary_lines)


class BacktestEngine:
    """
    백테스팅 메인 엔진

    전체 백테스팅 프로세스를 관리합니다.
    일별로 신호를 생성하고, 리스크 관리를 적용하며, 주문을 실행합니다.

    Attributes:
        config: 백테스팅 설정
        data_manager: DataManager 객체
        portfolio: Portfolio 객체
        execution_engine: ExecutionEngine 객체
        market_data: 시장 데이터 딕셔너리
        current_date: 현재 시뮬레이션 날짜

    Methods:
        run_backtest(): 백테스팅 실행
        process_day(): 특정 날짜 처리
        check_and_execute_stops(): 손절 체크 및 실행
        generate_and_execute_exits(): 청산 신호 생성 및 실행
        generate_and_execute_entries(): 진입 신호 생성 및 실행
        get_results(): 백테스팅 결과 반환
    """

    def __init__(
        self,
        config: Optional[Dict[str, Any]] = None
    ):
        """
        백테스팅 엔진 초기화

        Args:
            config: 백테스팅 설정
                - use_cache: 캐시 사용 여부
                - commission_rate: 수수료율
                - slippage_pct: 슬리피지 비율
                - enable_early_signals: 조기 신호 활성화
                - risk_config: 리스크 관리 설정
        """
        self.config = config or {}

        # 데이터 관리자
        self.data_manager = DataManager(
            use_cache=self.config.get('use_cache', True)
        )

        # 포트폴리오 (나중에 초기화)
        self.portfolio: Optional[Portfolio] = None

        # 실행 엔진
        self.execution_engine = ExecutionEngine(
            commission_rate=self.config.get('commission_rate', 0.00015),
            slippage_pct=self.config.get('slippage_pct', 0.001)
        )

        # 시장 데이터
        self.market_data: Optional[Dict[str, pd.DataFrame]] = None

        # 현재 날짜
        self.current_date: Optional[datetime] = None

        logger.info("BacktestEngine 초기화 완료")

    def run_backtest(
        self,
        start_date: str,
        end_date: str,
        initial_capital: float,
        market: str = 'ALL'
    ) -> BacktestResult:
        """
        백테스팅 실행 (전체 시장 스캔 방식)

        Args:
            start_date: 시작일 (YYYY-MM-DD)
            end_date: 종료일 (YYYY-MM-DD)
            initial_capital: 초기 자본금
            market: 시장 구분 ('KOSPI', 'KOSDAQ', 'ALL')

        Returns:
            BacktestResult: 백테스팅 결과 객체

        Process:
            1. 전체 시장 데이터 로드 (코스피/코스닥 전체)
            2. 포트폴리오 초기화
            3. 날짜별 루프:
                a. 손절 체크 → 청산
                b. 청산 신호 → 청산 (보유 종목만)
                c. 진입 신호 → 전체 종목 스캔 → 리스크 관리 → 진입
                d. 포트폴리오 스냅샷 기록
            4. 성과 분석

        Examples:
            >>> engine = BacktestEngine()
            >>> result = engine.run_backtest(
            ...     start_date='2020-01-01',
            ...     end_date='2023-12-31',
            ...     initial_capital=100_000_000,
            ...     market='ALL'
            ... )
            >>> print(result.summary())
        """
        logger.info("=" * 60)
        logger.info("백테스팅 시작")
        logger.info("=" * 60)
        logger.info(f"기간: {start_date} ~ {end_date}")
        logger.info(f"시장: {market}")
        logger.info(f"초기 자본: {initial_capital:,.0f}원")

        # 1. 전체 시장 데이터 로드
        logger.info("시장 데이터 로딩 중...")
        self.market_data = self.data_manager.load_market_data(
            start_date=start_date,
            end_date=end_date,
            market=market
        )

        logger.info(f"데이터 로딩 완료: {len(self.market_data)}개 종목")

        # 2. 포트폴리오 초기화
        self.portfolio = Portfolio(
            initial_capital=initial_capital,
            commission_rate=self.config.get('commission_rate', 0.00015)
        )

        # 3. 날짜 리스트 생성 (모든 종목 데이터의 교집합)
        dates = self._get_common_dates()
        logger.info(f"거래일 수: {len(dates)}일")

        # 4. 날짜별 루프
        for i, date in enumerate(dates):
            self.current_date = date

            if i % 10 == 0:  # 매 10일마다 진행 상황 로깅
                logger.info(f"진행: {i}/{len(dates)} ({date.strftime('%Y-%m-%d')})")

            self.process_day(date)

        # 5. 성과 분석
        result = self.get_results(start_date, end_date, len(self.market_data))

        logger.info("=" * 60)
        logger.info("백테스팅 완료")
        logger.info(f"총 수익률: {result.total_return:.2f}%")
        logger.info(f"최대 낙폭: {result.max_drawdown:.2f}%")
        logger.info(f"승률: {result.win_rate:.2f}%")
        logger.info("=" * 60)

        return result

    def process_day(self, date: datetime) -> None:
        """
        특정 날짜 처리

        Args:
            date: 거래일

        Process:
            1. 포트폴리오 가치 업데이트
            2. 트레일링 스톱 업데이트
            3. 손절 체크 및 실행
            4. 청산 신호 처리
            5. 진입 신호 처리
            6. 스냅샷 기록
        """
        # 현재가 딕셔너리
        current_prices = self._get_current_prices(date)

        # 1. 포트폴리오 가치 업데이트
        equity = self.portfolio.calculate_equity(current_prices)
        logger.debug(f"{date.strftime('%Y-%m-%d')} - 총 자산: {equity:,.0f}원")

        # 2. 트레일링 스톱 업데이트
        self.portfolio.update_trailing_stops(current_prices, self.market_data)

        # 3. 손절 체크 및 실행
        self.check_and_execute_stops(date, current_prices)

        # 4. 청산 신호 처리
        self.generate_and_execute_exits(date, current_prices)

        # 5. 진입 신호 처리
        self.generate_and_execute_entries(date, current_prices)

        # 6. 스냅샷 기록
        self.portfolio.record_snapshot(date, current_prices)

    def check_and_execute_stops(
        self,
        date: datetime,
        current_prices: Dict[str, float]
    ) -> None:
        """
        손절 체크 및 실행

        Args:
            date: 거래일
            current_prices: 현재가 딕셔너리
        """
        # 손절 발동 체크
        triggered = self.portfolio.check_stop_losses(
            current_prices=current_prices,
            market_data=self.market_data
        )

        if not triggered:
            return

        logger.info(f"손절 발동: {len(triggered)}건")

        # 손절 주문 실행
        for item in triggered:
            ticker = item['ticker']
            stop_price = item['stop_price']

            # 주문 생성
            position = self.portfolio.get_position(ticker)
            order = Order(
                ticker=ticker,
                action='sell',
                shares=position.shares,
                reason=f"stop_loss ({item['stop_type']})"
            )

            # 실행 (손절가로 체결)
            execution_result = self.execution_engine.execute(
                order=order,
                market_price=stop_price
            )

            # 포지션 청산
            close_result = self.portfolio.close_position(
                ticker=ticker,
                exit_price=execution_result['fill_price'],
                current_date=date,
                reason=order.reason
            )

            logger.info(
                f"손절 청산: {ticker} "
                f"손익={close_result['pnl']:,.0f}원 "
                f"({close_result['return_pct']:.2f}%)"
            )

    def generate_and_execute_exits(
        self,
        date: datetime,
        current_prices: Dict[str, float]
    ) -> None:
        """
        청산 신호 생성 및 실행 (보유 종목만)

        Args:
            date: 거래일
            current_prices: 현재가 딕셔너리
        """
        from src.analysis.signal.exit import generate_exit_signal

        # 보유 종목에 대해서만 청산 신호 체크
        for ticker in list(self.portfolio.positions.keys()):
            if ticker not in self.market_data:
                continue

            data = self.market_data[ticker]

            try:
                date_idx = data.index.get_loc(date)
            except KeyError:
                continue

            # 해당 날짜까지의 데이터만 사용
            historical_data = data.iloc[:date_idx + 1]

            # 포지션 정보 가져오기
            position = self.portfolio.get_position(ticker)

            # 청산 신호 생성
            try:
                exit_signals = generate_exit_signal(
                    data=historical_data,
                    position_type=position.position_type,
                    strategy='sequential'
                )
            except ValueError as e:
                # 필수 컬럼 누락 등의 데이터 문제
                logger.warning(f"청산 신호 생성 실패 ({ticker}): {e}")
                continue
            except Exception as e:
                logger.error(f"청산 신호 생성 중 오류 ({ticker}): {e}")
                continue

            latest_signal = exit_signals.iloc[-1]

            # 청산 신호가 없으면 스킵
            if latest_signal['Exit_Level'] == 0:
                continue

            # 청산 비율 결정 (Exit_Ratio는 퍼센트 값: 0, 50, 100)
            exit_ratio = latest_signal['Exit_Ratio']

            if exit_ratio == 0:
                continue

            position = self.portfolio.get_position(ticker)
            shares_to_sell = int(position.shares * exit_ratio / 100)

            if shares_to_sell == 0:
                continue

            # 주문 생성
            order = Order(
                ticker=ticker,
                action='sell',
                shares=shares_to_sell,
                reason=f"exit_signal ({latest_signal['Exit_Signal']})"
            )

            # 실행
            execution_result = self.execution_engine.execute(
                order=order,
                market_price=current_prices.get(ticker, position.entry_price)
            )

            # 포지션 청산
            close_result = self.portfolio.close_position(
                ticker=ticker,
                exit_price=execution_result['fill_price'],
                current_date=date,
                shares=shares_to_sell,
                reason=order.reason
            )

            logger.info(
                f"청산 신호: {ticker} "
                f"{shares_to_sell}주 ({exit_ratio * 100:.0f}%) "
                f"손익={close_result['pnl']:,.0f}원 "
                f"({close_result['return_pct']:.2f}%)"
            )

    def generate_and_execute_entries(
        self,
        date: datetime,
        current_prices: Dict[str, float]
    ) -> None:
        """
        진입 신호 생성 및 실행 (전체 시장 스캔)

        Args:
            date: 거래일
            current_prices: 현재가 딕셔너리

        Process:
            1. 전체 종목에 대해 진입 신호 생성
               - 이미 보유 중인 종목은 스킵
            2. 신호 강도 평가 및 필터링
            3. 리스크 관리 적용 (포트폴리오 제한 제외)
            4. 승인된 주문 실행
        """
        from src.analysis.signal.entry import generate_entry_signals
        from src.analysis.signal.strength import evaluate_signal_strength
        from src.analysis.risk import apply_risk_management

        signals = []

        # 1. 각 종목별 진입 신호 생성
        for ticker in self.market_data.keys():
            # 이미 보유 중이면 스킵
            if ticker in self.portfolio.positions:
                continue

            data = self.market_data[ticker]

            try:
                date_idx = data.index.get_loc(date)
            except KeyError:
                continue

            # 해당 날짜까지의 데이터만 사용
            historical_data = data.iloc[:date_idx + 1]

            # 진입 신호 생성
            try:
                entry_signals = generate_entry_signals(
                    data=historical_data,
                    enable_early=self.config.get('enable_early_signals', False)
                )

                latest_signal = entry_signals.iloc[-1]

                if latest_signal['Entry_Signal'] == 0:
                    continue

                # 신호 강도 평가
                strength = evaluate_signal_strength(historical_data).iloc[-1]

                signals.append({
                    'ticker': ticker,
                    'action': 'buy' if latest_signal['Entry_Signal'] > 0 else 'sell',
                    'signal_type': latest_signal['Signal_Type'],
                    'signal_strength': int(strength),
                    'current_price': current_prices.get(ticker, historical_data['Close'].iloc[-1]),
                    'stage': historical_data['Stage'].iloc[-1]
                })

            except ValueError as e:
                # 필수 컬럼 누락 등의 데이터 문제
                logger.debug(f"신호 생성 실패 ({ticker}): {e}")
                continue
            except Exception as e:
                logger.debug(f"신호 생성 중 오류 ({ticker}): {e}")
                continue

        if not signals:
            return

        logger.debug(f"진입 신호 {len(signals)}건 발생")

        # 2. 각 신호에 대해 리스크 관리 적용
        for signal in signals:
            ticker = signal['ticker']

            try:
                # 리스크 관리 적용
                risk_result = apply_risk_management(
                    signal=signal,
                    account_balance=self.portfolio.calculate_equity(current_prices),
                    positions=self.portfolio.get_position_dict(),
                    market_data=self.market_data[ticker],
                    config=self.config.get('risk_config', {})
                )

                # 승인되지 않으면 스킵
                if not risk_result['approved']:
                    logger.debug(
                        f"진입 거부: {ticker} - {risk_result.get('reason', 'unknown')}"
                    )
                    continue

                # 3. 주문 실행
                order = Order(
                    ticker=ticker,
                    action='buy',
                    shares=risk_result['position_size'],
                    position_type='long',
                    units=risk_result['units'],
                    stop_price=risk_result['stop_price'],
                    signal_strength=signal['signal_strength'],
                    reason=f"{signal['signal_type']} (Stage {signal['stage']})"
                )

                execution_result = self.execution_engine.execute(
                    order=order,
                    market_price=signal['current_price']
                )

                # 4. 포트폴리오에 포지션 추가
                # 진입 전략 결정
                if signal['signal_type'] == 'sell':
                    # 역발상 매수 (Stage 2 or 3)
                    if signal['stage'] == 3:
                        entry_strategy = 'contrarian_buy'
                    elif signal['stage'] == 2:
                        entry_strategy = 'early_contrarian_buy'
                    else:
                        entry_strategy = 'contrarian_buy'  # 기본값
                else:
                    # 일반 매수 (Stage 5 or 6)
                    if signal['stage'] == 6:
                        entry_strategy = 'normal_buy'
                    elif signal['stage'] == 5:
                        entry_strategy = 'early_buy'
                    else:
                        entry_strategy = 'normal_buy'  # 기본값

                position = Position(
                    ticker=ticker,
                    position_type='long',
                    entry_date=date,
                    entry_price=execution_result['fill_price'],
                    shares=risk_result['position_size'],
                    units=risk_result['units'],
                    stop_price=risk_result['stop_price'],
                    stop_type=risk_result['stop_type'],
                    signal_strength=signal['signal_strength'],
                    stage_at_entry=signal['stage'],
                    entry_strategy=entry_strategy
                )

                self.portfolio.add_position(
                    position=position,
                    cost=execution_result['total_cost']
                )

                logger.info(
                    f"진입: {ticker} "
                    f"{risk_result['position_size']}주 @ {execution_result['fill_price']:,.0f}원 "
                    f"(손절가: {risk_result['stop_price']:,.0f}원)"
                )

            except Exception as e:
                logger.error(f"진입 실행 실패: {ticker} - {e}")
                continue

    def get_results(
        self,
        start_date: str,
        end_date: str,
        market_count: int
    ) -> BacktestResult:
        """
        백테스팅 결과 반환

        Args:
            start_date: 시작일
            end_date: 종료일
            market_count: 스캔한 종목 수

        Returns:
            BacktestResult: 백테스팅 결과
        """
        from src.backtest.analytics import PerformanceAnalyzer

        # 최종 자본
        final_equity = self.portfolio.calculate_equity({})

        # analytics.py를 사용하여 통계 계산
        analyzer = PerformanceAnalyzer(
            portfolio_history=self.portfolio.history,
            trades=self.portfolio.trades,
            initial_capital=self.portfolio.initial_capital
        )

        # 수익률 지표
        returns = analyzer.calculate_returns()
        total_return = returns['total_return']

        # MDD 계산
        mdd_info = analyzer.calculate_max_drawdown()
        max_drawdown = mdd_info['max_drawdown']

        # 거래 통계
        win_rate_info = analyzer.calculate_win_rate()
        total_trades = win_rate_info['total_trades']
        winning_trades = win_rate_info['winning_trades']
        losing_trades = win_rate_info['losing_trades']
        win_rate = win_rate_info['win_rate']

        return BacktestResult(
            start_date=start_date,
            end_date=end_date,
            initial_capital=self.portfolio.initial_capital,
            final_capital=final_equity,
            total_return=total_return,
            max_drawdown=max_drawdown,
            total_trades=total_trades,
            winning_trades=winning_trades,
            losing_trades=losing_trades,
            win_rate=win_rate,
            portfolio_history=self.portfolio.history,
            trades=self.portfolio.trades,
            market_count=market_count
        )

    def _get_common_dates(self) -> List[datetime]:
        """
        모든 종목 데이터의 공통 날짜 추출

        Returns:
            List[datetime]: 공통 거래일 리스트
        """
        if not self.market_data:
            return []

        # 모든 종목의 날짜 인덱스 수집
        all_dates = set()
        for ticker, data in self.market_data.items():
            all_dates.update(data.index.tolist())

        # 정렬하여 반환
        return sorted(list(all_dates))

    def _get_current_prices(self, date: datetime) -> Dict[str, float]:
        """
        특정 날짜의 모든 종목 현재가 조회

        Args:
            date: 거래일

        Returns:
            Dict[str, float]: {ticker: price}
        """
        prices = {}

        for ticker, data in self.market_data.items():
            try:
                price = data.loc[date, 'Close']
                prices[ticker] = float(price)
            except (KeyError, IndexError):
                # 해당 날짜에 데이터 없음 (거래 정지 등)
                continue

        return prices


def main():
    from src.backtest.analytics import PerformanceAnalyzer

    # 1. 엔진 생성
    engine = BacktestEngine(config={
        'use_cache': True,
        'commission_rate': 0.00015,
        'slippage_pct': 0.001,
        'enable_early_signals': False,
        'risk_config': {
            'risk_per_trade': 0.01,
            'atr_multiplier': 2.0,
            'skip_portfolio_limits': True  # 포트폴리오 제한 제외
        }
    })

    # 2. 백테스팅 실행
    result = engine.run_backtest(
        start_date='2025-05-01',
        end_date='2025-10-31',
        initial_capital=10_000_000,
        market='ALL'  # KOSPI + KOSDAQ 전체
    )

    # 3. 결과 확인 (기본 요약)
    print(result.summary())

    print(f"최종 자본: {result.final_capital:,.0f}원")
    print(f"총 수익률: {result.total_return:.2f}%")
    print(f"최대 낙폭: {result.max_drawdown:.2f}%")
    print(f"승률: {result.win_rate:.2f}%")

    # 4. 거래 내역 상세 확인 (수익 순)
    print("\n=== 거래 내역 상세 (수익 상위 50건) ===")
    # 수익 순으로 정렬
    sorted_trades = sorted(result.trades, key=lambda x: x['pnl'], reverse=True)
    for trade in sorted_trades[:50]:  # 수익 상위 50개
        print(f"{trade['date']}: {trade['ticker']} {trade['action']} "
              f"손익={trade['pnl']:,.0f}원 "
              f"보유={trade.get('holding_days', 'N/A')}일 "
              f"사유={trade.get('reason', 'N/A')}")

    # 5. 포트폴리오 히스토리 (시각화용)
    history_df = pd.DataFrame(result.portfolio_history)
    history_df.set_index('date', inplace=True)
    print(history_df['equity'].describe())

    # 6. PerformanceAnalyzer를 사용한 상세 분석
    print("\n" + "=" * 70)
    print("PerformanceAnalyzer를 사용한 상세 분석")
    print("=" * 70 + "\n")

    analyzer = PerformanceAnalyzer(
        portfolio_history=result.portfolio_history,
        trades=result.trades,
        initial_capital=result.initial_capital
    )

    # 확장된 리포트 출력
    print(analyzer.generate_report())

    # 7. Stage 6 실패 패턴 분석
    print("\n" + "=" * 70)
    print("Stage 6 실패 패턴 분석")
    print("=" * 70 + "\n")

    stage6_analysis = analyzer.analyze_stage6_failures()

    if stage6_analysis['total_count'] > 0:
        print(f"Stage 6 진입 총 {stage6_analysis['total_count']}건")
        print(f"  - 수익 거래: {stage6_analysis['win_count']}건")
        print(f"  - 손실 거래: {stage6_analysis['loss_count']}건")
        print(f"  - 승률: {stage6_analysis['win_rate']:.1f}%")
        print(f"  - 평균 손익: {stage6_analysis['avg_pnl']:,.0f}원")
        print(f"  - 평균 수익: {stage6_analysis['avg_win']:,.0f}원")
        print(f"  - 평균 손실: {stage6_analysis['avg_loss']:,.0f}원")

        print("\n=== 청산 사유별 분포 ===")
        for reason, stats in stage6_analysis['exit_reason_dist'].items():
            print(f"{reason}: {stats['count']}건 (승률 {stats['win_rate']:.1f}%, 평균 {stats['avg_pnl']:,.0f}원)")

        print("\n=== 보유 기간 통계 ===")
        hp = stage6_analysis['holding_period_stats']
        print(f"전체 평균 보유: {hp['avg_holding_all']:.1f}일")
        print(f"수익 거래 평균 보유: {hp['avg_holding_winners']:.1f}일")
        print(f"손실 거래 평균 보유: {hp['avg_holding_losers']:.1f}일")
        print(f"보유 기간 범위: {hp['min_holding']:.0f}일 ~ {hp['max_holding']:.0f}일")

        if stage6_analysis['signal_strength_comparison']:
            print("\n=== 신호 강도 비교 (수익 vs 손실) ===")
            ss = stage6_analysis['signal_strength_comparison']
            print(f"수익 거래 평균 강도: {ss['winners_avg_strength']:.2f} (범위: {ss['winners_min']:.0f} ~ {ss['winners_max']:.0f})")
            print(f"손실 거래 평균 강도: {ss['losers_avg_strength']:.2f} (범위: {ss['losers_min']:.0f} ~ {ss['losers_max']:.0f})")
            print(f"강도 차이: {ss['strength_diff']:.2f}")
    else:
        print("Stage 6 진입 거래가 없습니다.")

    # 8. Stage 3 성공 패턴 분석
    print("\n" + "=" * 70)
    print("Stage 3 성공 패턴 분석")
    print("=" * 70 + "\n")

    stage3_analysis = analyzer.analyze_stage3_success()

    if stage3_analysis['total_count'] > 0:
        print(f"Stage 3 진입 총 {stage3_analysis['total_count']}건")
        print(f"  - 수익 거래: {stage3_analysis['win_count']}건")
        print(f"  - 손실 거래: {stage3_analysis['loss_count']}건")
        print(f"  - 승률: {stage3_analysis['win_rate']:.1f}%")
        print(f"  - 평균 손익: {stage3_analysis['avg_pnl']:,.0f}원")
        print(f"  - 평균 수익: {stage3_analysis['avg_win']:,.0f}원")
        print(f"  - 평균 손실: {stage3_analysis['avg_loss']:,.0f}원")

        print("\n=== 청산 사유별 분포 ===")
        for reason, stats in stage3_analysis['exit_reason_dist'].items():
            print(f"{reason}: {stats['count']}건 (승률 {stats['win_rate']:.1f}%, 평균 {stats['avg_pnl']:,.0f}원)")

        print("\n=== 보유 기간 통계 ===")
        hp = stage3_analysis['holding_period_stats']
        print(f"전체 평균 보유: {hp['avg_holding_all']:.1f}일")
        print(f"수익 거래 평균 보유: {hp['avg_holding_winners']:.1f}일")
        print(f"손실 거래 평균 보유: {hp['avg_holding_losers']:.1f}일")
        print(f"보유 기간 범위: {hp['min_holding']:.0f}일 ~ {hp['max_holding']:.0f}일")

        print("\n=== 수익 분포 ===")
        pnl = stage3_analysis['pnl_distribution']
        print(f"최대 수익: {pnl['max_profit']:,.0f}원")
        print(f"중간값: {pnl['median_profit']:,.0f}원")
        print(f"최소 수익: {pnl['min_profit']:,.0f}원")
        print(f"표준편차: {pnl['std_profit']:,.0f}원")

        if stage3_analysis['signal_strength_stats']:
            print("\n=== 신호 강도 통계 ===")
            ss = stage3_analysis['signal_strength_stats']
            print(f"평균 신호 강도: {ss['avg_strength']:.2f}")
            print(f"중간값: {ss['median_strength']:.2f}")
            print(f"범위: {ss['min_strength']:.0f} ~ {ss['max_strength']:.0f}")
            print(f"표준편차: {ss['std_strength']:.2f}")
    else:
        print("Stage 3 진입 거래가 없습니다.")

    # 9. Stage × Exit Reason 교차 분석
    print("\n" + "=" * 70)
    print("진입 스테이지 × 청산 사유 교차 분석")
    print("=" * 70 + "\n")

    cross_table = analyzer.analyze_stage_exit_cross()
    if not cross_table.empty:
        print(cross_table)
        print("\n※ 상단: 건수(count), 하단: 평균 손익(mean)")
    else:
        print("교차 분석할 거래 내역이 없습니다.")

if __name__ == "__main__":
    main()