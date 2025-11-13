"""
Technical 패키지

기술적 분석(Technical Analysis) 모듈

이동평균선 투자법 전략에 필요한 기술적 지표 계산 기능을 제공합니다.

향후 확장 가능:
- RSI 기반 전략
- 볼린저 밴드 전략
- 스토캐스틱 전략
- 패턴 인식 전략
등 다양한 기술적 분석 전략을 모듈 형태로 추가 가능
"""

from .indicators import (
    calculate_ema,
    calculate_sma,
    calculate_true_range,
    calculate_atr,
    calculate_macd,
    calculate_triple_macd,
    detect_peakout,
    calculate_slope,
    check_direction,
    calculate_all_indicators,
)

__all__ = [
    'calculate_ema',
    'calculate_sma',
    'calculate_true_range',
    'calculate_atr',
    'calculate_macd',
    'calculate_triple_macd',
    'detect_peakout',
    'calculate_slope',
    'check_direction',
    'calculate_all_indicators',
]