"""
포트폴리오 관리 모듈

백테스팅을 위한 포트폴리오 및 포지션 관리 기능을 제공합니다.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional, Any
import pandas as pd
import logging

logger = logging.getLogger(__name__)


@dataclass
class Position:
    """
    개별 포지션 정보

    Attributes:
        ticker: 종목코드
        position_type: 'long' 또는 'short'
        entry_date: 진입 날짜
        entry_price: 진입 평균가
        shares: 보유 주식 수
        units: 유닛 수 (터틀 트레이딩)
        stop_price: 손절가
        stop_type: 손절 유형 ('volatility' or 'trend')
        highest_price: 진입 후 최고가 (매수 포지션)
        lowest_price: 진입 후 최저가 (매도 포지션)
        signal_strength: 진입 시 신호 강도
        stage_at_entry: 진입 시 스테이지
    """
    ticker: str
    position_type: str  # 'long' or 'short'
    entry_date: datetime
    entry_price: float
    shares: int
    units: int
    stop_price: float
    stop_type: str  # 'volatility' or 'trend'
    highest_price: Optional[float] = None
    lowest_price: Optional[float] = None
    signal_strength: int = 0
    stage_at_entry: int = 0

    def __post_init__(self):
        """초기화 후 검증"""
        if self.position_type not in ['long', 'short']:
            raise ValueError(f"position_type은 'long' 또는 'short'여야 합니다: {self.position_type}")

        if self.shares <= 0:
            raise ValueError(f"shares는 양수여야 합니다: {self.shares}")

        if self.entry_price <= 0:
            raise ValueError(f"entry_price는 양수여야 합니다: {self.entry_price}")

        # 최고가/최저가 초기화
        if self.highest_price is None and self.position_type == 'long':
            self.highest_price = self.entry_price

        if self.lowest_price is None and self.position_type == 'short':
            self.lowest_price = self.entry_price

    def current_value(self, current_price: float) -> float:
        """
        현재 포지션 가치 계산

        Args:
            current_price: 현재가

        Returns:
            float: 포지션 평가액 (원)
        """
        if self.position_type == 'long':
            return self.shares * current_price
        else:  # short
            # 공매도는 진입가와 현재가 차이만큼 손익
            return self.shares * (2 * self.entry_price - current_price)

    def unrealized_pnl(self, current_price: float) -> float:
        """
        미실현 손익 계산

        Args:
            current_price: 현재가

        Returns:
            float: 미실현 손익 (원)
        """
        if self.position_type == 'long':
            return (current_price - self.entry_price) * self.shares
        else:  # short
            return (self.entry_price - current_price) * self.shares

    def realized_pnl(self, exit_price: float, shares: int = None) -> float:
        """
        실현 손익 계산 (청산 시)

        Args:
            exit_price: 청산가
            shares: 청산 주식 수 (None이면 전체 청산)

        Returns:
            float: 실현 손익 (원)
        """
        if shares is None:
            shares = self.shares

        if self.position_type == 'long':
            return (exit_price - self.entry_price) * shares
        else:  # short
            return (self.entry_price - exit_price) * shares

    def update_extremes(self, current_price: float) -> None:
        """
        최고가/최저가 업데이트 (트레일링 스톱용)

        Args:
            current_price: 현재가
        """
        if self.position_type == 'long':
            if self.highest_price is None or current_price > self.highest_price:
                self.highest_price = current_price
                logger.debug(f"{self.ticker} 최고가 갱신: {self.highest_price:,.0f}원")
        else:  # short
            if self.lowest_price is None or current_price < self.lowest_price:
                self.lowest_price = current_price
                logger.debug(f"{self.ticker} 최저가 갱신: {self.lowest_price:,.0f}원")


class Portfolio:
    """
    포트폴리오 관리 클래스

    Attributes:
        initial_capital: 초기 자본금
        cash: 현금 잔고
        positions: 보유 포지션 딕셔너리 {ticker: Position}
        closed_positions: 청산된 포지션 리스트
        history: 포트폴리오 스냅샷 히스토리
        trades: 모든 거래 내역
        commission_rate: 수수료율
    """

    def __init__(
        self,
        initial_capital: float,
        commission_rate: float = 0.00015
    ):
        """
        포트폴리오 초기화

        Args:
            initial_capital: 초기 자본금
            commission_rate: 수수료율 (기본값: 0.00015 = 0.015%)
        """
        if initial_capital <= 0:
            raise ValueError(f"초기 자본금은 양수여야 합니다: {initial_capital}")

        self.initial_capital = initial_capital
        self.cash = initial_capital
        self.commission_rate = commission_rate

        self.positions: Dict[str, Position] = {}
        self.closed_positions: List[Position] = []
        self.history: List[Dict[str, Any]] = []
        self.trades: List[Dict[str, Any]] = []

        logger.info(f"포트폴리오 초기화: 초기자본={initial_capital:,.0f}원, 수수료={commission_rate:.4%}")

    def add_position(
        self,
        position: Position,
        cost: float
    ) -> bool:
        """
        새로운 포지션 추가

        Args:
            position: Position 객체
            cost: 총 비용 (주식 가격 + 수수료)

        Returns:
            bool: 추가 성공 여부

        Raises:
            ValueError: 현금 부족 시
        """
        if cost > self.cash:
            raise ValueError(
                f"현금 부족: 필요={cost:,.0f}원, 보유={self.cash:,.0f}원"
            )

        # 기존 포지션이 있으면 업데이트 (평균가 계산)
        if position.ticker in self.positions:
            existing = self.positions[position.ticker]

            # 평균 진입가 계산
            total_shares = existing.shares + position.shares
            avg_price = (
                (existing.entry_price * existing.shares +
                 position.entry_price * position.shares) / total_shares
            )

            existing.shares = total_shares
            existing.entry_price = avg_price
            existing.units += position.units

            logger.info(
                f"포지션 추가: {position.ticker} "
                f"{position.shares}주 추가 → 총 {total_shares}주 "
                f"(평균가: {avg_price:,.0f}원)"
            )
        else:
            self.positions[position.ticker] = position
            logger.info(
                f"신규 포지션: {position.ticker} "
                f"{position.shares}주 @ {position.entry_price:,.0f}원 "
                f"(손절가: {position.stop_price:,.0f}원)"
            )

        self.cash -= cost

        return True

    def close_position(
        self,
        ticker: str,
        exit_price: float,
        current_date: datetime,
        shares: int = None,
        reason: str = None
    ) -> Dict[str, Any]:
        """
        포지션 청산

        Args:
            ticker: 종목코드
            exit_price: 청산가
            current_date: 청산 날짜 (백테스팅용)
            shares: 청산 주식 수 (None이면 전체 청산)
            reason: 청산 사유 ('stop_loss', 'exit_signal', 'stage_change' 등)

        Returns:
            Dict: 청산 결과
                - ticker: 종목코드
                - shares: 청산 수량
                - entry_price: 진입가
                - exit_price: 청산가
                - pnl: 실현 손익
                - return_pct: 수익률 (%)
                - holding_days: 보유 기간
                - reason: 청산 사유

        Raises:
            ValueError: 포지션이 없거나 청산 수량이 보유량 초과 시
        """
        if ticker not in self.positions:
            raise ValueError(f"포지션이 없습니다: {ticker}")

        position = self.positions[ticker]

        if shares is None:
            shares = position.shares

        if shares > position.shares:
            raise ValueError(
                f"청산 수량 초과: 요청={shares}, 보유={position.shares}"
            )

        # 손익 계산
        pnl = position.realized_pnl(exit_price, shares)
        return_pct = (exit_price / position.entry_price - 1) * 100

        # 현금 회수 (매도 대금 - 수수료)
        proceeds = shares * exit_price
        commission = proceeds * self.commission_rate
        self.cash += (proceeds - commission)

        # 보유 기간 계산 (백테스팅용 current_date 사용)
        holding_days = (current_date - position.entry_date).days

        # 청산 사유 분류 개선: 손절인데 수익이면 trailing_stop으로 재분류
        final_reason = reason
        if reason and 'stop_loss' in reason and pnl > 0:
            # 손절가에 도달했는데 수익이 나는 경우 = 트레일링 스톱
            final_reason = f'trailing_stop ({reason.split("(")[1].rstrip(")")})'

        # 포지션 업데이트 또는 제거
        if shares == position.shares:
            # 전체 청산
            closed_position = self.positions.pop(ticker)
            self.closed_positions.append(closed_position)
            logger.info(
                f"포지션 청산: {ticker} "
                f"{shares}주 @ {exit_price:,.0f}원 "
                f"손익={pnl:,.0f}원 ({return_pct:+.2f}%) "
                f"사유={final_reason}"
            )
        else:
            # 부분 청산
            position.shares -= shares
            # 유닛도 비율에 맞게 조정
            remaining_ratio = position.shares / (position.shares + shares)
            position.units = int(position.units * remaining_ratio)

            logger.info(
                f"부분 청산: {ticker} "
                f"{shares}주 @ {exit_price:,.0f}원 "
                f"(남은 주식: {position.shares}주) "
                f"손익={pnl:,.0f}원 ({return_pct:+.2f}%)"
            )

        # 거래 기록 (백테스팅용 current_date 사용)
        trade_result = {
            'date': current_date,
            'ticker': ticker,
            'action': 'sell',
            'shares': shares,
            'entry_price': position.entry_price,
            'exit_price': exit_price,
            'pnl': pnl,
            'return_pct': return_pct,
            'holding_days': holding_days,
            'reason': final_reason,  # 개선된 청산 사유
            'commission': commission,
            'entry_stage': position.stage_at_entry  # 진입 시 스테이지 추가
        }

        self.record_trade(trade_result)

        return trade_result

    def calculate_equity(
        self,
        current_prices: Dict[str, float]
    ) -> float:
        """
        총 자산 계산

        Args:
            current_prices: 현재가 딕셔너리 {ticker: price}

        Returns:
            float: 총 자산 (현금 + 포지션 평가액)
        """
        positions_value = sum(
            position.current_value(current_prices.get(ticker, position.entry_price))
            for ticker, position in self.positions.items()
        )

        return self.cash + positions_value

    def get_available_capital(self) -> float:
        """
        사용 가능 자본 조회

        Returns:
            float: 현금 잔고
        """
        return self.cash

    def check_stop_losses(
        self,
        current_prices: Dict[str, float],
        market_data: Dict[str, pd.DataFrame]
    ) -> List[Dict[str, Any]]:
        """
        모든 포지션의 손절가 체크

        Args:
            current_prices: 현재가 딕셔너리
            market_data: 시장 데이터 딕셔너리 (ATR, MA 등 포함)

        Returns:
            List[Dict]: 손절 발동 포지션 리스트
        """
        from src.analysis.risk.stop_loss import check_stop_loss_triggered

        triggered = []

        for ticker, position in self.positions.items():
            current_price = current_prices.get(ticker)
            if current_price is None:
                logger.warning(f"현재가 없음: {ticker}")
                continue

            # 손절 발동 체크
            is_triggered = check_stop_loss_triggered(
                current_price=current_price,
                stop_price=position.stop_price,
                position_type=position.position_type
            )

            if is_triggered:
                triggered.append({
                    'ticker': ticker,
                    'stop_price': position.stop_price,
                    'current_price': current_price,
                    'stop_type': position.stop_type
                })

                logger.warning(
                    f"손절 발동: {ticker} "
                    f"손절가={position.stop_price:,.0f}원, "
                    f"현재가={current_price:,.0f}원"
                )

        return triggered

    def update_trailing_stops(
        self,
        current_prices: Dict[str, float],
        market_data: Dict[str, pd.DataFrame]
    ) -> None:
        """
        트레일링 스톱 업데이트

        Args:
            current_prices: 현재가 딕셔너리
            market_data: 시장 데이터 딕셔너리 (ATR 포함)
        """
        from src.analysis.risk.stop_loss import update_trailing_stop

        for ticker, position in self.positions.items():
            current_price = current_prices.get(ticker)
            if current_price is None:
                continue

            # 최고가/최저가 업데이트
            position.update_extremes(current_price)

            # ATR 조회
            data = market_data.get(ticker)
            if data is None or 'ATR' not in data.columns:
                continue

            latest_atr = data['ATR'].iloc[-1]

            # 트레일링 스톱 계산
            if position.position_type == 'long' and position.highest_price:
                new_stop = update_trailing_stop(
                    entry_price=position.entry_price,
                    highest_price=position.highest_price,
                    current_stop=position.stop_price,
                    atr=latest_atr,
                    position_type='long'
                )

                if new_stop > position.stop_price:
                    old_stop = position.stop_price
                    position.stop_price = new_stop
                    logger.debug(
                        f"트레일링 스톱 업데이트: {ticker} "
                        f"{old_stop:,.0f}원 → {new_stop:,.0f}원"
                    )

            elif position.position_type == 'short' and position.lowest_price:
                new_stop = update_trailing_stop(
                    entry_price=position.entry_price,
                    highest_price=position.lowest_price,  # 매도는 lowest 사용
                    current_stop=position.stop_price,
                    atr=latest_atr,
                    position_type='short'
                )

                if new_stop < position.stop_price:
                    old_stop = position.stop_price
                    position.stop_price = new_stop
                    logger.debug(
                        f"트레일링 스톱 업데이트: {ticker} "
                        f"{old_stop:,.0f}원 → {new_stop:,.0f}원"
                    )

    def record_snapshot(
        self,
        date: datetime,
        current_prices: Dict[str, float]
    ) -> None:
        """
        일별 스냅샷 저장

        Args:
            date: 날짜
            current_prices: 현재가 딕셔너리
        """
        equity = self.calculate_equity(current_prices)

        snapshot = {
            'date': date,
            'cash': self.cash,
            'equity': equity,
            'positions_count': len(self.positions),
            'positions': {
                ticker: {
                    'shares': pos.shares,
                    'value': pos.current_value(current_prices.get(ticker, pos.entry_price)),
                    'unrealized_pnl': pos.unrealized_pnl(current_prices.get(ticker, pos.entry_price))
                }
                for ticker, pos in self.positions.items()
            }
        }

        self.history.append(snapshot)

    def record_trade(self, trade_info: Dict[str, Any]) -> None:
        """
        거래 기록

        Args:
            trade_info: 거래 정보
        """
        self.trades.append(trade_info)

    def get_position(self, ticker: str) -> Optional[Position]:
        """
        포지션 조회

        Args:
            ticker: 종목코드

        Returns:
            Position 또는 None
        """
        return self.positions.get(ticker)

    def get_total_units(self) -> int:
        """
        총 유닛 수 (리스크 관리용)

        Returns:
            int: 모든 포지션의 유닛 합계
        """
        return sum(position.units for position in self.positions.values())

    def get_position_dict(self) -> Dict[str, int]:
        """
        리스크 관리용 포지션 딕셔너리 반환

        Returns:
            Dict[str, int]: {ticker: units}
        """
        return {
            ticker: position.units
            for ticker, position in self.positions.items()
        }

    def get_summary(self) -> Dict[str, Any]:
        """
        포트폴리오 요약 정보

        Returns:
            Dict: 포트폴리오 요약
        """
        total_trades = len(self.trades)
        winning_trades = sum(1 for trade in self.trades if trade.get('pnl', 0) > 0)

        return {
            'initial_capital': self.initial_capital,
            'current_cash': self.cash,
            'total_positions': len(self.positions),
            'closed_positions': len(self.closed_positions),
            'total_trades': total_trades,
            'winning_trades': winning_trades,
            'win_rate': winning_trades / total_trades if total_trades > 0 else 0,
            'total_units': self.get_total_units()
        }
