"""
매매 신호 생성 모듈

이 패키지는 Level 3 스테이지 분석을 기반으로 실제 매매 신호를 생성합니다.

Modules:
    entry: 진입 신호 생성 (매수/매도)
    exit: 청산 신호 생성 (3단계 시스템)
    strength: 신호 강도 평가 (향후 구현)
    filter: 신호 필터링 (향후 구현)
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
    'check_macd_cross'
]
