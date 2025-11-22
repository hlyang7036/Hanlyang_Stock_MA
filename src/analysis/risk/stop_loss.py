"""
손절 관리 모듈

이 모듈은 2가지 손절 방식(변동성 기반, 추세 기반)을 제공하고,
트레일링 스톱을 통해 수익을 보호합니다.

Functions:
    calculate_volatility_stop: 변동성 기반 손절가 계산
    calculate_trend_stop: 추세 기반 손절가 계산
    get_stop_loss_price: 최종 손절가 결정
    check_stop_loss_triggered: 손절 발동 체크
    update_trailing_stop: 트레일링 스톱 업데이트
"""

import pandas as pd
import numpy as np
import numbers
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


def calculate_volatility_stop(
    entry_price: float,
    atr: float,
    position_type: str,
    atr_multiplier: float = 2.0
) -> float:
    """
    변동성 기반 손절가 계산
    
    ATR(Average True Range)을 기반으로 손절가를 계산합니다.
    정상적인 변동성은 허용하면서 큰 손실을 방지합니다.
    
    Args:
        entry_price: 진입가 (원/주)
        atr: Average True Range (원)
        position_type: 포지션 유형
            - 'long': 매수 포지션
            - 'short': 매도 포지션
        atr_multiplier: ATR 배수 (기본값: 2.0)
            - 2.0 = 정상 변동성 허용
            - 1.5 = 보수적 (타이트한 손절)
            - 3.0 = 공격적 (여유로운 손절)
    
    Returns:
        float: 손절가 (원/주)
    
    Raises:
        TypeError: 입력값 타입이 잘못되었을 때
        ValueError: entry_price나 atr이 0 이하일 때
        ValueError: position_type이 'long' 또는 'short'가 아닐 때
        ValueError: atr_multiplier가 0 이하일 때
    
    Formula:
        매수 포지션: 손절가 = 진입가 - (ATR × 배수)
        매도 포지션: 손절가 = 진입가 + (ATR × 배수)
    
    Examples:
        >>> # 매수 포지션
        >>> calculate_volatility_stop(50_000, 1_000, 'long', 2.0)
        48000.0
        
        >>> # 매도 포지션
        >>> calculate_volatility_stop(50_000, 1_000, 'short', 2.0)
        52000.0
        
        >>> # 보수적 손절 (1.5배)
        >>> calculate_volatility_stop(50_000, 1_000, 'long', 1.5)
        48500.0
    
    Notes:
        - ATR 2배: 정상적인 변동성 범위 허용
        - 너무 타이트하면 자주 손절됨 (빈번한 거래)
        - 너무 느슨하면 큰 손실 가능 (리스크 증가)
        - 변동성이 큰 종목은 자동으로 넓은 손절폭
    """
    # 1. 타입 검증
    if not isinstance(entry_price, numbers.Number):
        raise TypeError(f"entry_price는 숫자여야 합니다: {type(entry_price)}")
    
    if not isinstance(atr, numbers.Number):
        raise TypeError(f"atr은 숫자여야 합니다: {type(atr)}")
    
    if not isinstance(position_type, str):
        raise TypeError(f"position_type은 문자열이어야 합니다: {type(position_type)}")
    
    if not isinstance(atr_multiplier, numbers.Number):
        raise TypeError(f"atr_multiplier는 숫자여야 합니다: {type(atr_multiplier)}")
    
    # 2. 값 검증
    if entry_price <= 0:
        raise ValueError(f"진입가는 양수여야 합니다: {entry_price:,.0f}")
    
    if atr <= 0:
        raise ValueError(f"ATR은 양수여야 합니다: {atr:,.2f}")
    
    position_type = position_type.lower()
    if position_type not in ['long', 'short']:
        raise ValueError(f"position_type은 'long' 또는 'short'여야 합니다: {position_type}")
    
    if atr_multiplier <= 0:
        raise ValueError(f"atr_multiplier는 양수여야 합니다: {atr_multiplier}")
    
    logger.debug(
        f"변동성 손절 계산: 진입가={entry_price:,.0f}원, "
        f"ATR={atr:,.2f}원, 배수={atr_multiplier:.1f}, 타입={position_type}"
    )
    
    # 3. 손절가 계산
    stop_distance = atr * atr_multiplier
    
    if position_type == 'long':
        # 매수 포지션: 아래로 손절
        stop_price = entry_price - stop_distance
    else:
        # 매도 포지션: 위로 손절
        stop_price = entry_price + stop_distance
    
    # 4. 음수 방지 (매수 포지션)
    if position_type == 'long' and stop_price < 0:
        stop_price = 0.0
        logger.warning(f"손절가가 0 미만이 되어 0으로 조정되었습니다")
    
    logger.debug(
        f"변동성 손절가: {stop_price:,.0f}원 "
        f"(진입가 대비 {abs(stop_price - entry_price):,.0f}원, "
        f"{abs(stop_price - entry_price) / entry_price * 100:.1f}%)"
    )
    
    return float(stop_price)


def calculate_trend_stop(
    data: pd.DataFrame,
    position_type: str,
    stop_ma: str = 'EMA_20'
) -> pd.Series:
    """
    추세 기반 손절가 계산
    
    이동평균선을 기준으로 손절가를 계산합니다.
    추세가 꺾이면 즉시 손절하여 큰 손실을 방지합니다.
    
    Args:
        data: DataFrame (이동평균선 컬럼 필요)
            - 매수 포지션: stop_ma 컬럼 필요 (예: 'EMA_20')
            - 매도 포지션: stop_ma 컬럼 필요
        position_type: 포지션 유형
            - 'long': 매수 포지션 (이동평균선 하단에서 손절)
            - 'short': 매도 포지션 (이동평균선 상단에서 손절)
        stop_ma: 손절 기준선 (기본값: 'EMA_20')
            - 'EMA_20': 중기 추세 (20일)
            - 'EMA_40': 장기 추세 (40일)
            - 'EMA_60': 초장기 추세 (60일)
    
    Returns:
        pd.Series: 추세 기반 손절가
    
    Raises:
        TypeError: data가 DataFrame이 아닐 때
        ValueError: 필수 컬럼이 없을 때
        ValueError: position_type이 'long' 또는 'short'가 아닐 때
    
    Examples:
        >>> # 매수 포지션 손절가 계산
        >>> df['Trend_Stop_Long'] = calculate_trend_stop(df, 'long', 'EMA_20')
        >>> 
        >>> # 매도 포지션 손절가 계산
        >>> df['Trend_Stop_Short'] = calculate_trend_stop(df, 'short', 'EMA_20')
    
    Notes:
        - 매수 포지션: EMA_20 아래로 이탈 시 손절
        - 매도 포지션: EMA_20 위로 이탈 시 손절
        - 추세 추종 전략에 적합
        - 횡보장에서는 자주 손절될 수 있음
    """
    # 1. 타입 검증
    if not isinstance(data, pd.DataFrame):
        raise TypeError(f"DataFrame이 필요합니다. 입력 타입: {type(data)}")
    
    if not isinstance(position_type, str):
        raise TypeError(f"position_type은 문자열이어야 합니다: {type(position_type)}")
    
    if not isinstance(stop_ma, str):
        raise TypeError(f"stop_ma는 문자열이어야 합니다: {type(stop_ma)}")
    
    # 2. 값 검증
    if stop_ma not in data.columns:
        raise ValueError(f"{stop_ma} 컬럼이 필요합니다. 사용 가능 컬럼: {list(data.columns)}")
    
    position_type = position_type.lower()
    if position_type not in ['long', 'short']:
        raise ValueError(f"position_type은 'long' 또는 'short'여야 합니다: {position_type}")
    
    logger.debug(
        f"추세 손절 계산: 기준선={stop_ma}, 타입={position_type}, "
        f"데이터 크기={len(data)}"
    )
    
    # 3. 손절가 계산 (이동평균선 사용)
    if position_type == 'long':
        # 매수 포지션: 이동평균선이 손절가
        stop_price = data[stop_ma].copy()
    else:
        # 매도 포지션: 이동평균선이 손절가
        stop_price = data[stop_ma].copy()
    
    logger.debug(
        f"추세 손절가 계산 완료: "
        f"평균={stop_price.mean():,.0f}원, "
        f"최소={stop_price.min():,.0f}원, "
        f"최대={stop_price.max():,.0f}원"
    )
    
    return stop_price


def get_stop_loss_price(
    entry_price: float,
    current_price: float,
    atr: float,
    trend_stop: float,
    position_type: str,
    atr_multiplier: float = 2.0
) -> Dict[str, Any]:
    """
    최종 손절가 결정
    
    변동성 기반 손절가와 추세 기반 손절가 중
    현재가에 더 가까운 것(더 보수적인 것)을 선택합니다.
    
    Args:
        entry_price: 진입가 (원/주)
        current_price: 현재가 (원/주)
        atr: ATR (원)
        trend_stop: 추세 기반 손절가 (원/주)
        position_type: 'long' or 'short'
        atr_multiplier: ATR 배수 (기본값: 2.0)
    
    Returns:
        Dict[str, Any]: 손절 정보
            - stop_price: 최종 손절가 (float)
            - stop_type: 손절 유형 ('volatility' or 'trend')
            - distance: 현재가와의 거리 (%, float)
            - distance_won: 현재가와의 거리 (원, float)
            - risk_amount: 리스크 금액 (1주당, float)
            - volatility_stop: 변동성 기반 손절가 (float)
            - trend_stop: 추세 기반 손절가 (float)
    
    Raises:
        TypeError: 입력값 타입이 잘못되었을 때
        ValueError: 값이 유효하지 않을 때
    
    Examples:
        >>> # 매수 포지션
        >>> result = get_stop_loss_price(
        ...     entry_price=50_000,
        ...     current_price=52_000,
        ...     atr=1_000,
        ...     trend_stop=49_000,
        ...     position_type='long'
        ... )
        >>> result['stop_price']
        49000.0
        >>> result['stop_type']
        'trend'
    
    Notes:
        - 두 손절가 중 현재가에 더 가까운 것 선택 (보수적)
        - 매수: 더 높은 손절가 선택
        - 매도: 더 낮은 손절가 선택
    """
    # 1. 타입 검증
    if not isinstance(entry_price, numbers.Number):
        raise TypeError(f"entry_price는 숫자여야 합니다: {type(entry_price)}")
    
    if not isinstance(current_price, numbers.Number):
        raise TypeError(f"current_price는 숫자여야 합니다: {type(current_price)}")
    
    if not isinstance(atr, numbers.Number):
        raise TypeError(f"atr은 숫자여야 합니다: {type(atr)}")
    
    if not isinstance(trend_stop, numbers.Number):
        raise TypeError(f"trend_stop은 숫자여야 합니다: {type(trend_stop)}")
    
    if not isinstance(position_type, str):
        raise TypeError(f"position_type은 문자열이어야 합니다: {type(position_type)}")
    
    # 2. 값 검증
    if entry_price <= 0:
        raise ValueError(f"진입가는 양수여야 합니다: {entry_price:,.0f}")
    
    if current_price <= 0:
        raise ValueError(f"현재가는 양수여야 합니다: {current_price:,.0f}")
    
    if atr <= 0:
        raise ValueError(f"ATR은 양수여야 합니다: {atr:,.2f}")
    
    if trend_stop <= 0:
        raise ValueError(f"추세 손절가는 양수여야 합니다: {trend_stop:,.0f}")
    
    position_type = position_type.lower()
    if position_type not in ['long', 'short']:
        raise ValueError(f"position_type은 'long' 또는 'short'여야 합니다: {position_type}")
    
    logger.debug(
        f"최종 손절가 결정: 진입={entry_price:,.0f}원, "
        f"현재={current_price:,.0f}원, 추세손절={trend_stop:,.0f}원"
    )
    
    # 3. 변동성 기반 손절가 계산
    volatility_stop = calculate_volatility_stop(
        entry_price, atr, position_type, atr_multiplier
    )

    # 4. 추세 손절가 유효성 검증
    # 매수 포지션: 추세 손절가는 진입가보다 낮아야 함
    # 매도 포지션: 추세 손절가는 진입가보다 높아야 함
    trend_stop_valid = False

    if position_type == 'long':
        if trend_stop < entry_price:
            trend_stop_valid = True
        else:
            logger.warning(
                f"추세 손절가가 진입가보다 높아 무효 처리: "
                f"진입가={entry_price:,.0f}원, 추세손절={trend_stop:,.0f}원 "
                f"(변동성 손절만 사용)"
            )
    else:  # short
        if trend_stop > entry_price:
            trend_stop_valid = True
        else:
            logger.warning(
                f"추세 손절가가 진입가보다 낮아 무효 처리: "
                f"진입가={entry_price:,.0f}원, 추세손절={trend_stop:,.0f}원 "
                f"(변동성 손절만 사용)"
            )

    # 5. 최종 손절가 선택
    if not trend_stop_valid:
        # 추세 손절가가 무효하면 변동성 손절가만 사용
        final_stop = volatility_stop
        stop_type = 'volatility'
    elif position_type == 'long':
        # 매수 포지션: 더 높은 손절가 선택 (보수적, 현재가에 더 가까움)
        if volatility_stop >= trend_stop:
            final_stop = volatility_stop
            stop_type = 'volatility'
        else:
            final_stop = trend_stop
            stop_type = 'trend'
    else:
        # 매도 포지션: 더 낮은 손절가 선택 (보수적, 현재가에 더 가까움)
        if volatility_stop <= trend_stop:
            final_stop = volatility_stop
            stop_type = 'volatility'
        else:
            final_stop = trend_stop
            stop_type = 'trend'

    # 6. 거리 계산
    distance_won = abs(current_price - final_stop)
    distance_pct = distance_won / current_price

    # 7. 리스크 금액 (1주당)
    risk_amount = abs(entry_price - final_stop)
    
    result = {
        'stop_price': float(final_stop),
        'stop_type': stop_type,
        'distance': float(distance_pct),
        'distance_won': float(distance_won),
        'risk_amount': float(risk_amount),
        'volatility_stop': float(volatility_stop),
        'trend_stop': float(trend_stop)
    }
    
    logger.info(
        f"최종 손절가: {final_stop:,.0f}원 ({stop_type}), "
        f"현재가 대비 {distance_pct:.1%} ({distance_won:,.0f}원), "
        f"1주당 리스크 {risk_amount:,.0f}원"
    )
    
    return result


def check_stop_loss_triggered(
    current_price: float,
    stop_price: float,
    position_type: str
) -> bool:
    """
    손절 발동 체크
    
    현재가가 손절가에 도달했는지 확인합니다.
    
    Args:
        current_price: 현재가 (원/주)
        stop_price: 손절가 (원/주)
        position_type: 'long' or 'short'
    
    Returns:
        bool: 손절 발동 여부
            - True: 손절 발동 (청산 필요)
            - False: 정상 (포지션 유지)
    
    Raises:
        TypeError: 입력값 타입이 잘못되었을 때
        ValueError: 값이 유효하지 않을 때
    
    Examples:
        >>> # 매수 포지션 - 손절 발동
        >>> check_stop_loss_triggered(47_000, 48_000, 'long')
        True
        
        >>> # 매수 포지션 - 정상
        >>> check_stop_loss_triggered(49_000, 48_000, 'long')
        False
        
        >>> # 매도 포지션 - 손절 발동
        >>> check_stop_loss_triggered(53_000, 52_000, 'short')
        True
    
    Notes:
        - 매수 포지션: 현재가 <= 손절가 → 손절
        - 매도 포지션: 현재가 >= 손절가 → 손절
        - 정확히 손절가와 같으면 손절 발동
    """
    # 1. 타입 검증
    if not isinstance(current_price, numbers.Number):
        raise TypeError(f"current_price는 숫자여야 합니다: {type(current_price)}")
    
    if not isinstance(stop_price, numbers.Number):
        raise TypeError(f"stop_price는 숫자여야 합니다: {type(stop_price)}")
    
    if not isinstance(position_type, str):
        raise TypeError(f"position_type은 문자열이어야 합니다: {type(position_type)}")
    
    # 2. 값 검증
    if current_price <= 0:
        raise ValueError(f"현재가는 양수여야 합니다: {current_price:,.0f}")
    
    if stop_price <= 0:
        raise ValueError(f"손절가는 양수여야 합니다: {stop_price:,.0f}")
    
    position_type = position_type.lower()
    if position_type not in ['long', 'short']:
        raise ValueError(f"position_type은 'long' 또는 'short'여야 합니다: {position_type}")
    
    # 3. 손절 발동 확인
    if position_type == 'long':
        # 매수 포지션: 현재가 <= 손절가
        triggered = current_price <= stop_price
    else:
        # 매도 포지션: 현재가 >= 손절가
        triggered = current_price >= stop_price
    
    if triggered:
        logger.warning(
            f"⚠️ 손절 발동! 현재가={current_price:,.0f}원, "
            f"손절가={stop_price:,.0f}원, 타입={position_type}"
        )
    else:
        logger.debug(
            f"손절 안전: 현재가={current_price:,.0f}원, "
            f"손절가={stop_price:,.0f}원 (여유 {abs(current_price - stop_price):,.0f}원)"
        )
    
    return triggered


def update_trailing_stop(
    entry_price: float,
    highest_price: float,
    current_stop: float,
    atr: float,
    position_type: str,
    atr_multiplier: float = 2.0
) -> float:
    """
    트레일링 스톱 업데이트
    
    수익이 나면 손절가를 올려서(매수) 또는 내려서(매도) 이익을 보호합니다.
    손실 방지뿐만 아니라 수익 보호 기능을 제공합니다.
    
    Args:
        entry_price: 진입가 (원/주)
        highest_price: 최고가 (매수) 또는 최저가 (매도) (원/주)
        current_stop: 현재 손절가 (원/주)
        atr: ATR (원)
        position_type: 'long' or 'short'
        atr_multiplier: ATR 배수 (기본값: 2.0)
    
    Returns:
        float: 업데이트된 손절가 (원/주)
    
    Raises:
        TypeError: 입력값 타입이 잘못되었을 때
        ValueError: 값이 유효하지 않을 때
    
    Examples:
        >>> # 매수 포지션 - 신고가 경신 시
        >>> update_trailing_stop(
        ...     entry_price=50_000,
        ...     highest_price=55_000,  # 신고가
        ...     current_stop=48_000,
        ...     atr=1_000,
        ...     position_type='long'
        ... )
        53000.0  # 55,000 - 2,000 = 53,000 (손절가 상향)
        
        >>> # 매수 포지션 - 신고가 아닐 때
        >>> update_trailing_stop(
        ...     entry_price=50_000,
        ...     highest_price=52_000,
        ...     current_stop=50_000,  # 기존 손절가가 더 높음
        ...     atr=1_000,
        ...     position_type='long'
        ... )
        50000.0  # 손절가 유지
    
    Notes:
        매수 포지션:
        - 신고가 경신 시 손절가 상향 조정
        - 손절가 = max(현재 손절가, 최고가 - 2ATR)
        - 진입가 이하로는 내려가지 않음
        
        매도 포지션:
        - 신저가 경신 시 손절가 하향 조정
        - 손절가 = min(현재 손절가, 최저가 + 2ATR)
        - 진입가 이상으로는 올라가지 않음
    """
    # 1. 타입 검증
    if not isinstance(entry_price, numbers.Number):
        raise TypeError(f"entry_price는 숫자여야 합니다: {type(entry_price)}")
    
    if not isinstance(highest_price, numbers.Number):
        raise TypeError(f"highest_price는 숫자여야 합니다: {type(highest_price)}")
    
    if not isinstance(current_stop, numbers.Number):
        raise TypeError(f"current_stop은 숫자여야 합니다: {type(current_stop)}")
    
    if not isinstance(atr, numbers.Number):
        raise TypeError(f"atr은 숫자여야 합니다: {type(atr)}")
    
    if not isinstance(position_type, str):
        raise TypeError(f"position_type은 문자열이어야 합니다: {type(position_type)}")
    
    # 2. 값 검증
    if entry_price <= 0:
        raise ValueError(f"진입가는 양수여야 합니다: {entry_price:,.0f}")
    
    if highest_price <= 0:
        raise ValueError(f"최고가/최저가는 양수여야 합니다: {highest_price:,.0f}")
    
    if current_stop <= 0:
        raise ValueError(f"현재 손절가는 양수여야 합니다: {current_stop:,.0f}")
    
    if atr <= 0:
        raise ValueError(f"ATR은 양수여야 합니다: {atr:,.2f}")
    
    position_type = position_type.lower()
    if position_type not in ['long', 'short']:
        raise ValueError(f"position_type은 'long' 또는 'short'여야 합니다: {position_type}")
    
    logger.debug(
        f"트레일링 스톱 업데이트: 진입={entry_price:,.0f}원, "
        f"{'최고' if position_type == 'long' else '최저'}가={highest_price:,.0f}원, "
        f"현재손절={current_stop:,.0f}원"
    )
    
    # 3. 트레일링 손절가 계산
    stop_distance = atr * atr_multiplier
    
    if position_type == 'long':
        # 매수 포지션: 최고가 - 2ATR
        trailing_stop = highest_price - stop_distance
        
        # 현재 손절가보다 높으면 업데이트
        new_stop = max(current_stop, trailing_stop)
        
        # 진입가 이하로는 내려가지 않음 (최소 본전)
        new_stop = max(new_stop, entry_price)
    else:
        # 매도 포지션: 최저가 + 2ATR
        trailing_stop = highest_price + stop_distance  # highest_price는 실제로 lowest_price
        
        # 현재 손절가보다 낮으면 업데이트
        new_stop = min(current_stop, trailing_stop)
        
        # 진입가 이상으로는 올라가지 않음 (최소 본전)
        new_stop = min(new_stop, entry_price)
    
    # 4. 업데이트 여부 로깅
    if new_stop != current_stop:
        logger.info(
            f"✅ 트레일링 스톱 업데이트: {current_stop:,.0f}원 → {new_stop:,.0f}원 "
            f"({abs(new_stop - current_stop):,.0f}원 {'상향' if position_type == 'long' else '하향'})"
        )
    else:
        logger.debug(f"트레일링 스톱 유지: {current_stop:,.0f}원")
    
    return float(new_stop)
