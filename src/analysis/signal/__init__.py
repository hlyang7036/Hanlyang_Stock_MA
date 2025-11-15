"""
매매 신호 생성 모듈

이 패키지는 Level 3 스테이지 분석을 기반으로 실제 매매 신호를 생성합니다.

Modules:
    entry: 진입 신호 생성 (매수/매도)
    exit: 청산 신호 생성 (3단계 시스템)
    strength: 신호 강도 평가 (0-100점 채점)
    filter: 신호 필터링 (품질 제어)
"""

from src.analysis.signal.entry import (
    generate_buy_signal,
    generate_sell_signal,
    check_entry_conditions,
    generate_entry_signals
)

from src.analysis.signal.exit import (
    generate_exit_signal,
    check_histogram_peakout,
    check_macd_peakout,
    check_macd_cross
)

from src.analysis.signal.strength import (
    evaluate_signal_strength,
    calculate_macd_alignment_score,
    calculate_trend_strength_score,
    calculate_momentum_score
)

from src.analysis.signal.filter import (
    apply_signal_filters,
    check_strength_filter,
    check_volatility_filter,
    check_trend_filter,
    check_conflicting_signals
)

__all__ = [
    # Entry signals
    'generate_buy_signal',
    'generate_sell_signal',
    'check_entry_conditions',
    'generate_entry_signals',
    # Exit signals
    'generate_exit_signal',
    'check_histogram_peakout',
    'check_macd_peakout',
    'check_macd_cross',
    # Signal strength
    'evaluate_signal_strength',
    'calculate_macd_alignment_score',
    'calculate_trend_strength_score',
    'calculate_momentum_score',
    # Signal filtering
    'apply_signal_filters',
    'check_strength_filter',
    'check_volatility_filter',
    'check_trend_filter',
    'check_conflicting_signals'
]
