"""
포지션 사이징 모듈

이 모듈은 터틀 트레이딩 방식을 기반으로 포지션 크기를 계산합니다.
변동성(ATR)을 고려하여 계좌 리스크를 일정하게 유지합니다.

Functions:
    calculate_unit_size: 기본 유닛 크기 계산 (터틀 방식)
    adjust_by_signal_strength: 신호 강도에 따른 포지션 조정
    calculate_position_size: 최종 포지션 크기 계산
    get_max_position_by_capital: 자본 제약에 따른 최대 포지션
"""

import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)


def calculate_unit_size(
    account_balance: float,
    atr: float,
    risk_percentage: float = 0.01
) -> int:
    """
    기본 유닛 크기 계산 (터틀 트레이딩 방식)
    
    터틀 트레이딩의 핵심 개념인 변동성 기반 포지션 사이징을 구현합니다.
    계좌의 일정 비율(기본 1%)만 리스크에 노출하여 안정적인 자금 관리를 합니다.
    
    Args:
        account_balance: 계좌 잔고 (원)
        atr: Average True Range (원)
            - 변동성이 클수록 유닛이 작아짐 (보수적)
            - 변동성이 작을수록 유닛이 커짐 (공격적)
        risk_percentage: 리스크 비율 (기본값: 0.01 = 1%)
            - 계좌의 1%만 리스크에 노출
            - 0.01 = 1%, 0.02 = 2%
    
    Returns:
        int: 1유닛 크기 (주 단위)
    
    Raises:
        TypeError: 입력값이 숫자가 아닐 때
        ValueError: account_balance나 atr이 0 이하일 때
        ValueError: risk_percentage가 0~1 범위 밖일 때
    
    Formula:
        1유닛 = (계좌잔고 × 리스크비율) / ATR
    
    Examples:
        >>> # 표준 케이스
        >>> calculate_unit_size(10_000_000, 1_000, 0.01)
        100
        
        >>> # 고변동성 (ATR 큼) → 유닛 작음
        >>> calculate_unit_size(10_000_000, 2_000, 0.01)
        50
        
        >>> # 저변동성 (ATR 작음) → 유닛 큼
        >>> calculate_unit_size(10_000_000, 500, 0.01)
        200
        
        >>> # 공격적 리스크 (2%)
        >>> calculate_unit_size(10_000_000, 1_000, 0.02)
        200
    
    Notes:
        - ATR이 클수록 (변동성 높음) → 유닛이 작아짐
        - ATR이 작을수록 (변동성 낮음) → 유닛이 커짐
        - 이를 통해 변동성과 관계없이 일정한 리스크 유지
        - 주식은 정수 단위이므로 반올림하여 반환
    """
    # 1. 타입 검증
    if not isinstance(account_balance, (int, float)):
        raise TypeError(f"account_balance는 숫자여야 합니다: {type(account_balance)}")
    
    if not isinstance(atr, (int, float)):
        raise TypeError(f"atr은 숫자여야 합니다: {type(atr)}")
    
    if not isinstance(risk_percentage, (int, float)):
        raise TypeError(f"risk_percentage는 숫자여야 합니다: {type(risk_percentage)}")
    
    # 2. 값 검증
    if account_balance <= 0:
        raise ValueError(f"계좌 잔고는 양수여야 합니다: {account_balance:,.0f}")
    
    if atr <= 0:
        raise ValueError(f"ATR은 양수여야 합니다: {atr:,.2f}")
    
    if not 0 < risk_percentage <= 1:
        raise ValueError(
            f"리스크 비율은 0~1 사이여야 합니다 (0.01=1%, 0.02=2%): {risk_percentage}"
        )
    
    logger.debug(
        f"유닛 계산: 잔고={account_balance:,.0f}원, "
        f"ATR={atr:,.2f}원, 리스크={risk_percentage:.2%}"
    )
    
    # 3. 유닛 계산
    risk_amount = account_balance * risk_percentage
    unit_size = risk_amount / atr
    
    # 4. 정수로 반올림 (주식은 정수 단위)
    unit_size_int = int(round(unit_size))
    
    logger.debug(
        f"계산 결과: 리스크금액={risk_amount:,.0f}원, "
        f"유닛={unit_size:.2f}주 → {unit_size_int}주"
    )
    
    return unit_size_int


def adjust_by_signal_strength(
    base_units: int,
    signal_strength: int,
    strength_threshold: int = 80
) -> int:
    """
    신호 강도에 따른 포지션 조정
    
    신호 강도가 높을수록 더 큰 포지션을 취하고,
    낮을수록 작은 포지션을 취하거나 진입하지 않습니다.
    
    Args:
        base_units: 기본 유닛 크기 (calculate_unit_size 결과)
        signal_strength: 신호 강도 (0-100)
            - Level 4 신호 생성 모듈에서 계산된 값
        strength_threshold: 기준 강도 (기본값: 80)
            - 이 값 이상이면 100% 포지션
    
    Returns:
        int: 조정된 유닛 크기
    
    Raises:
        TypeError: 입력값이 정수가 아닐 때
        ValueError: base_units이 음수일 때
        ValueError: signal_strength가 0-100 범위 밖일 때
        ValueError: strength_threshold가 0-100 범위 밖일 때
    
    Adjustment Rules:
        - 80점 이상: 기본 유닛 × 1.0 (100%)
        - 70-80점: 기본 유닛 × 0.75 (75%)
        - 60-70점: 기본 유닛 × 0.5 (50%)
        - 50-60점: 기본 유닛 × 0.25 (25%)
        - 50점 미만: 0 (진입 안 함)
    
    Examples:
        >>> # 강한 신호 (85점) → 100%
        >>> adjust_by_signal_strength(100, 85, 80)
        100
        
        >>> # 중간 신호 (75점) → 75%
        >>> adjust_by_signal_strength(100, 75, 80)
        75
        
        >>> # 약한 신호 (65점) → 50%
        >>> adjust_by_signal_strength(100, 65, 80)
        50
        
        >>> # 매우 약한 신호 (55점) → 25%
        >>> adjust_by_signal_strength(100, 55, 80)
        25
        
        >>> # 필터링 수준 (45점) → 진입 안 함
        >>> adjust_by_signal_strength(100, 45, 80)
        0
    
    Notes:
        - 강한 신호일수록 큰 포지션으로 수익 극대화
        - 약한 신호는 작은 포지션으로 리스크 최소화
        - 50점 미만은 Level 4 필터에서 걸러지지만 안전장치로 0 반환
    """
    # 1. 타입 검증
    if not isinstance(base_units, int):
        raise TypeError(f"base_units는 정수여야 합니다: {type(base_units)}")
    
    if not isinstance(signal_strength, int):
        raise TypeError(f"signal_strength는 정수여야 합니다: {type(signal_strength)}")
    
    if not isinstance(strength_threshold, int):
        raise TypeError(f"strength_threshold는 정수여야 합니다: {type(strength_threshold)}")
    
    # 2. 값 검증
    if base_units < 0:
        raise ValueError(f"기본 유닛은 음수일 수 없습니다: {base_units}")
    
    if not 0 <= signal_strength <= 100:
        raise ValueError(f"신호 강도는 0-100 사이여야 합니다: {signal_strength}")
    
    if not 0 <= strength_threshold <= 100:
        raise ValueError(f"강도 임계값은 0-100 사이여야 합니다: {strength_threshold}")
    
    logger.debug(
        f"강도 조정: 기본={base_units}주, 강도={signal_strength}점, "
        f"임계값={strength_threshold}점"
    )
    
    # 3. 신호 강도에 따른 배율 결정
    if signal_strength >= strength_threshold:
        multiplier = 1.0  # 100%
    elif signal_strength >= 70:
        multiplier = 0.75  # 75%
    elif signal_strength >= 60:
        multiplier = 0.5   # 50%
    elif signal_strength >= 50:
        multiplier = 0.25  # 25%
    else:
        multiplier = 0.0   # 진입 안 함
    
    # 4. 조정된 유닛 계산
    adjusted = int(base_units * multiplier)
    
    logger.debug(
        f"조정 결과: {adjusted}주 (배율={multiplier:.2f}, "
        f"{int(multiplier * 100)}%)"
    )
    
    return adjusted


def calculate_position_size(
    account_balance: float,
    current_price: float,
    atr: float,
    signal_strength: int = 80,
    risk_percentage: float = 0.01
) -> Dict[str, Any]:
    """
    최종 포지션 크기 계산
    
    기본 유닛 계산과 신호 강도 조정을 통합하여
    실제 매수해야 할 주식 수와 관련 정보를 제공합니다.
    
    Args:
        account_balance: 계좌 잔고 (원)
        current_price: 현재가 (원/주)
        atr: ATR (원)
        signal_strength: 신호 강도 (0-100, 기본값: 80)
        risk_percentage: 리스크 비율 (기본값: 0.01 = 1%)
    
    Returns:
        Dict[str, Any]: 포지션 정보
            - units: 유닛 수 (int)
            - shares: 주식 수 (int)
            - total_value: 총 투자 금액 (float, 원)
            - risk_amount: 리스크 금액 (float, 원)
            - position_percentage: 계좌 대비 포지션 비율 (float, 0-1)
            - unit_value: 1유닛 가치 (float, 원)
    
    Raises:
        TypeError: 입력값 타입이 잘못되었을 때
        ValueError: current_price가 0 이하일 때
        ValueError: 기타 검증 실패 시
    
    Examples:
        >>> # 표준 케이스
        >>> result = calculate_position_size(10_000_000, 50_000, 1_000, 85)
        >>> result
        {
            'units': 1,
            'shares': 100,
            'total_value': 5_000_000.0,
            'risk_amount': 100_000.0,
            'position_percentage': 0.5,
            'unit_value': 5_000_000.0
        }
        
        >>> # 약한 신호 (50% 포지션)
        >>> result = calculate_position_size(10_000_000, 50_000, 1_000, 65)
        >>> result['shares']
        50
    
    Notes:
        - units: 유닛 수 (항상 1, 추가 매수 시 증가)
        - shares: 실제 매수 주식 수
        - total_value: 필요한 현금 = shares × current_price
        - position_percentage: 계좌 대비 투자 비율 (리스크 비율과 다름)
    """
    # 1. 타입 검증
    if not isinstance(current_price, (int, float)):
        raise TypeError(f"current_price는 숫자여야 합니다: {type(current_price)}")
    
    # 2. 값 검증
    if current_price <= 0:
        raise ValueError(f"현재가는 양수여야 합니다: {current_price:,.0f}")
    
    logger.info(
        f"포지션 계산 시작: 잔고={account_balance:,.0f}원, "
        f"가격={current_price:,.0f}원, ATR={atr:,.2f}원, 강도={signal_strength}점"
    )
    
    # 3. 기본 유닛 계산
    base_units = calculate_unit_size(account_balance, atr, risk_percentage)
    
    # 4. 신호 강도 조정
    adjusted_shares = adjust_by_signal_strength(base_units, signal_strength)
    
    # 5. 포지션 정보 계산
    total_value = adjusted_shares * current_price
    risk_amount = account_balance * risk_percentage
    position_percentage = total_value / account_balance if account_balance > 0 else 0
    unit_value = base_units * current_price
    
    result = {
        'units': 1,  # 초기 진입은 항상 1유닛
        'shares': adjusted_shares,
        'total_value': float(total_value),
        'risk_amount': float(risk_amount),
        'position_percentage': float(position_percentage),
        'unit_value': float(unit_value)
    }
    
    logger.info(
        f"포지션 계산 완료: {adjusted_shares}주 "
        f"(1유닛={base_units}주, 조정 후={adjusted_shares}주), "
        f"금액={total_value:,.0f}원 ({position_percentage:.1%})"
    )
    
    return result


def get_max_position_by_capital(
    account_balance: float,
    current_price: float,
    max_capital_ratio: float = 0.25
) -> int:
    """
    자본 제약에 따른 최대 포지션
    
    단일 종목에 과도한 자본이 집중되는 것을 방지합니다.
    계좌의 일정 비율(기본 25%) 이상을 한 종목에 투자하지 않습니다.
    
    Args:
        account_balance: 계좌 잔고 (원)
        current_price: 현재가 (원/주)
        max_capital_ratio: 최대 자본 비율 (기본값: 0.25 = 25%)
            - 단일 종목 최대 투자 한도
    
    Returns:
        int: 최대 매수 가능 주식 수
    
    Raises:
        TypeError: 입력값 타입이 잘못되었을 때
        ValueError: account_balance나 current_price가 0 이하일 때
        ValueError: max_capital_ratio가 0~1 범위 밖일 때
    
    Examples:
        >>> # 표준 케이스 (25% 제한)
        >>> get_max_position_by_capital(10_000_000, 50_000, 0.25)
        50
        
        >>> # 보수적 (20% 제한)
        >>> get_max_position_by_capital(10_000_000, 50_000, 0.20)
        40
        
        >>> # 공격적 (30% 제한)
        >>> get_max_position_by_capital(10_000_000, 50_000, 0.30)
        60
        
        >>> # 고가 주식
        >>> get_max_position_by_capital(10_000_000, 1_000_000, 0.25)
        2
    
    Notes:
        - 변동성 기반 포지션 사이징과 별개의 제약
        - 두 제약 중 더 작은 값을 최종 포지션으로 사용
        - 집중 투자 리스크 방지가 목적
        - 실제 매수 시 min(변동성 기반, 자본 기반) 선택
    """
    # 1. 타입 검증
    if not isinstance(account_balance, (int, float)):
        raise TypeError(f"account_balance는 숫자여야 합니다: {type(account_balance)}")
    
    if not isinstance(current_price, (int, float)):
        raise TypeError(f"current_price는 숫자여야 합니다: {type(current_price)}")
    
    if not isinstance(max_capital_ratio, (int, float)):
        raise TypeError(f"max_capital_ratio는 숫자여야 합니다: {type(max_capital_ratio)}")
    
    # 2. 값 검증
    if account_balance <= 0:
        raise ValueError(f"계좌 잔고는 양수여야 합니다: {account_balance:,.0f}")
    
    if current_price <= 0:
        raise ValueError(f"현재가는 양수여야 합니다: {current_price:,.0f}")
    
    if not 0 < max_capital_ratio <= 1:
        raise ValueError(
            f"최대 자본 비율은 0~1 사이여야 합니다 (0.25=25%): {max_capital_ratio}"
        )
    
    logger.debug(
        f"자본 제약 계산: 잔고={account_balance:,.0f}원, "
        f"가격={current_price:,.0f}원, 최대비율={max_capital_ratio:.1%}"
    )
    
    # 3. 최대 투자 가능 금액
    max_capital = account_balance * max_capital_ratio
    
    # 4. 최대 매수 가능 주식 수
    max_shares = max_capital / current_price
    
    # 5. 정수로 내림 (보수적 접근)
    max_shares_int = int(max_shares)
    
    logger.debug(
        f"자본 제약 결과: 최대금액={max_capital:,.0f}원, "
        f"최대주식={max_shares:.2f}주 → {max_shares_int}주"
    )
    
    return max_shares_int
