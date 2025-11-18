"""
주문 실행 시뮬레이션 모듈

백테스팅을 위한 주문 실행 시뮬레이션 기능을 제공합니다.
슬리피지와 수수료를 반영하여 현실적인 체결 가격을 계산합니다.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional, Dict, Any
import logging

logger = logging.getLogger(__name__)


@dataclass
class Order:
    """
    주문 정보

    Attributes:
        ticker: 종목코드
        action: 'buy' 또는 'sell'
        shares: 주식 수
        order_type: 주문 유형 ('market', 'limit')
        limit_price: 지정가 (limit 주문 시)
        timestamp: 주문 시각
        position_type: 포지션 유형 ('long', 'short')
        units: 유닛 수
        stop_price: 손절가
        signal_strength: 신호 강도
        reason: 주문 사유
    """
    ticker: str
    action: str  # 'buy' or 'sell'
    shares: int
    order_type: str = 'market'  # 'market' or 'limit'
    limit_price: Optional[float] = None
    timestamp: Optional[datetime] = None
    position_type: str = 'long'  # 'long' or 'short'
    units: int = 0
    stop_price: float = 0.0
    signal_strength: int = 0
    reason: Optional[str] = None

    def __post_init__(self):
        """초기화 후 검증 및 기본값 설정"""
        if self.timestamp is None:
            self.timestamp = datetime.now()

        # 입력 검증
        if self.action not in ['buy', 'sell']:
            raise ValueError(f"action은 'buy' 또는 'sell'이어야 합니다: {self.action}")

        if self.shares <= 0:
            raise ValueError(f"shares는 양수여야 합니다: {self.shares}")

        if self.order_type not in ['market', 'limit']:
            raise ValueError(f"order_type은 'market' 또는 'limit'이어야 합니다: {self.order_type}")

        if self.order_type == 'limit' and self.limit_price is None:
            raise ValueError("limit 주문은 limit_price가 필요합니다")

        if self.position_type not in ['long', 'short']:
            raise ValueError(f"position_type은 'long' 또는 'short'여야 합니다: {self.position_type}")


class ExecutionEngine:
    """
    주문 실행 엔진

    백테스팅에서 주문 체결을 시뮬레이션합니다.
    슬리피지와 수수료를 반영한 실제 체결가를 계산합니다.

    Attributes:
        commission_rate: 수수료율 (기본값: 0.00015 = 0.015%)
        slippage_pct: 슬리피지 비율 (기본값: 0.001 = 0.1%)
    """

    def __init__(
        self,
        commission_rate: float = 0.00015,
        slippage_pct: float = 0.001
    ):
        """
        실행 엔진 초기화

        Args:
            commission_rate: 수수료율 (기본값: 0.00015 = 0.015%)
            slippage_pct: 슬리피지 비율 (기본값: 0.001 = 0.1%)
        """
        if commission_rate < 0:
            raise ValueError(f"수수료율은 0 이상이어야 합니다: {commission_rate}")

        if slippage_pct < 0:
            raise ValueError(f"슬리피지 비율은 0 이상이어야 합니다: {slippage_pct}")

        self.commission_rate = commission_rate
        self.slippage_pct = slippage_pct

        logger.info(
            f"ExecutionEngine 초기화: "
            f"수수료={commission_rate:.4%}, "
            f"슬리피지={slippage_pct:.3%}"
        )

    def execute(
        self,
        order: Order,
        market_price: float
    ) -> Dict[str, Any]:
        """
        주문 실행

        Args:
            order: Order 객체
            market_price: 시장가 (현재가)

        Returns:
            Dict: 체결 결과
                - filled: 체결 여부 (bool)
                - fill_price: 체결가
                - shares: 체결 수량
                - commission: 수수료
                - total_cost: 총 비용 (매수) 또는 총 수령액 (매도)
                - slippage: 슬리피지 금액
                - ticker: 종목코드
                - action: 매수/매도
                - timestamp: 체결 시각

        Examples:
            >>> engine = ExecutionEngine()
            >>> order = Order(ticker='005930', action='buy', shares=100)
            >>> result = engine.execute(order, 50000)
            >>> result['fill_price']  # 50050.0 (0.1% 슬리피지)
        """
        if market_price <= 0:
            raise ValueError(f"시장가는 양수여야 합니다: {market_price}")

        # 체결가 계산 (슬리피지 포함)
        fill_price = self.calculate_fill_price(order, market_price)

        # 수수료 계산
        commission = self.calculate_commission(fill_price, order.shares)

        # 총 비용/수령액 계산
        gross_amount = fill_price * order.shares

        if order.action == 'buy':
            # 매수: 주식 가격 + 수수료
            total_cost = gross_amount + commission
        else:  # sell
            # 매도: 주식 가격 - 수수료
            total_cost = gross_amount - commission

        # 슬리피지 금액
        slippage_amount = abs(fill_price - market_price) * order.shares

        result = {
            'filled': True,
            'fill_price': fill_price,
            'shares': order.shares,
            'commission': commission,
            'total_cost': total_cost,
            'slippage': slippage_amount,
            'ticker': order.ticker,
            'action': order.action,
            'timestamp': order.timestamp
        }

        logger.debug(
            f"주문 체결: {order.ticker} {order.action} {order.shares}주 "
            f"@ {fill_price:,.0f}원 "
            f"(시장가={market_price:,.0f}원, 슬리피지={slippage_amount:,.0f}원, "
            f"수수료={commission:,.0f}원)"
        )

        return result

    def calculate_fill_price(
        self,
        order: Order,
        market_price: float
    ) -> float:
        """
        체결가 계산 (슬리피지 반영)

        Args:
            order: Order 객체
            market_price: 시장가

        Returns:
            float: 체결가

        Notes:
            매수: 시장가 + 슬리피지 (불리하게)
            매도: 시장가 - 슬리피지 (불리하게)

        Examples:
            >>> engine = ExecutionEngine(slippage_pct=0.001)
            >>> order = Order(action='buy', ...)
            >>> engine.calculate_fill_price(order, 50000)
            50050.0

            >>> order = Order(action='sell', ...)
            >>> engine.calculate_fill_price(order, 50000)
            49950.0
        """
        if order.action == 'buy':
            # 매수: 시장가보다 높게 체결 (불리)
            fill_price = market_price * (1 + self.slippage_pct)
        else:  # sell
            # 매도: 시장가보다 낮게 체결 (불리)
            fill_price = market_price * (1 - self.slippage_pct)

        return fill_price

    def calculate_commission(
        self,
        fill_price: float,
        shares: int
    ) -> float:
        """
        수수료 계산

        Args:
            fill_price: 체결가
            shares: 주식 수

        Returns:
            float: 수수료 (원)

        Notes:
            한국 증권사 수수료율: 약 0.015% (온라인)
            최소 수수료: 없음 (소액 거래도 비율만 적용)

        Examples:
            >>> engine = ExecutionEngine(commission_rate=0.00015)
            >>> engine.calculate_commission(50000, 100)
            7.5
        """
        commission = fill_price * shares * self.commission_rate
        return commission

    def calculate_total_cost(
        self,
        fill_price: float,
        shares: int,
        commission: float,
        action: str
    ) -> float:
        """
        총 비용 계산

        Args:
            fill_price: 체결가
            shares: 주식 수
            commission: 수수료
            action: 'buy' or 'sell'

        Returns:
            float: 총 비용 (매수) 또는 총 수령액 (매도)

        Notes:
            매수: 주식 가격 + 수수료
            매도: 주식 가격 - 수수료

        Examples:
            >>> engine = ExecutionEngine()
            >>> # 매수
            >>> engine.calculate_total_cost(50000, 100, 7.5, 'buy')
            5000007.5

            >>> # 매도
            >>> engine.calculate_total_cost(50000, 100, 7.5, 'sell')
            4999992.5
        """
        gross_amount = fill_price * shares

        if action == 'buy':
            return gross_amount + commission
        else:  # sell
            return gross_amount - commission

    def get_config(self) -> Dict[str, float]:
        """
        실행 엔진 설정 조회

        Returns:
            Dict: 설정 정보
                - commission_rate: 수수료율
                - slippage_pct: 슬리피지 비율
        """
        return {
            'commission_rate': self.commission_rate,
            'slippage_pct': self.slippage_pct
        }

    def update_config(
        self,
        commission_rate: Optional[float] = None,
        slippage_pct: Optional[float] = None
    ) -> None:
        """
        실행 엔진 설정 업데이트

        Args:
            commission_rate: 새로운 수수료율 (None이면 변경하지 않음)
            slippage_pct: 새로운 슬리피지 비율 (None이면 변경하지 않음)
        """
        if commission_rate is not None:
            if commission_rate < 0:
                raise ValueError(f"수수료율은 0 이상이어야 합니다: {commission_rate}")
            old_rate = self.commission_rate
            self.commission_rate = commission_rate
            logger.info(f"수수료율 업데이트: {old_rate:.4%} → {commission_rate:.4%}")

        if slippage_pct is not None:
            if slippage_pct < 0:
                raise ValueError(f"슬리피지 비율은 0 이상이어야 합니다: {slippage_pct}")
            old_slippage = self.slippage_pct
            self.slippage_pct = slippage_pct
            logger.info(f"슬리피지 비율 업데이트: {old_slippage:.3%} → {slippage_pct:.3%}")
