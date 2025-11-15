"""
리스크 관리 모듈

이 패키지는 터틀 트레이딩 방식을 기반으로 한 체계적인 리스크 관리 기능을 제공합니다.

Modules:
    position_sizing: 포지션 사이징 (변동성 기반 유닛 계산)
    stop_loss: 손절 관리 (변동성/추세 기반)
    portfolio: 포트폴리오 제한 (다층 리스크 제어)
    exposure: 리스크 노출 관리 (실시간 모니터링)

Main Functions:
    apply_risk_management: 통합 리스크 관리
"""

from src.analysis.risk.position_sizing import (
    calculate_unit_size,
    adjust_by_signal_strength,
    calculate_position_size,
    get_max_position_by_capital
)

from src.analysis.risk.stop_loss import (
    calculate_volatility_stop,
    calculate_trend_stop,
    get_stop_loss_price,
    check_stop_loss_triggered,
    update_trailing_stop
)

__all__ = [
    # Position Sizing
    'calculate_unit_size',
    'adjust_by_signal_strength',
    'calculate_position_size',
    'get_max_position_by_capital',
    # Stop Loss
    'calculate_volatility_stop',
    'calculate_trend_stop',
    'get_stop_loss_price',
    'check_stop_loss_triggered',
    'update_trailing_stop',
]
