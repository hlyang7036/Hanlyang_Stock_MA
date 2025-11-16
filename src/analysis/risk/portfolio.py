"""
포트폴리오 제한 모듈

이 모듈은 다층 리스크 제어를 통해 포트폴리오의 집중 리스크를 방지합니다.
4단계 계층적 제한 구조를 사용합니다.

제한 레벨:
1. 단일 종목:          최대 4유닛
2. 상관관계 높은 그룹: 최대 6유닛 (합계)
3. 상관관계 낮은 그룹: 최대 10유닛 (합계)
4. 전체 포트폴리오:    최대 12유닛 (합계)

Functions:
    check_single_position_limit: 단일 종목 포지션 제한 체크
    check_correlated_group_limit: 상관관계 그룹 제한 체크
    check_diversified_limit: 분산 투자 제한 체크
    check_total_exposure_limit: 전체 포트폴리오 노출 제한 체크
    get_available_position_size: 실제 추가 가능한 포지션 크기 계산
"""

import numbers
import logging
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)


def check_single_position_limit(
    current_units: int,
    additional_units: int,
    max_units_per_position: int = 4
) -> Dict[str, Any]:
    """
    단일 종목 포지션 제한 체크
    
    Args:
        current_units: 현재 보유 유닛
        additional_units: 추가 유닛
        max_units_per_position: 단일 종목 최대 유닛 (기본값: 4)
    
    Returns:
        Dict[str, Any]: 체크 결과
            - allowed: 허용 여부 (bool)
            - available_units: 추가 가능 유닛 수 (int)
            - current_units: 현재 유닛 (int)
            - limit: 최대 한도 (int)
            - reason: 거부 사유 (str, 불허 시)
    
    Raises:
        TypeError: 입력값 타입이 잘못되었을 때
        ValueError: 값이 유효하지 않을 때
    
    Examples:
        >>> check_single_position_limit(3, 2, 4)
        {
            'allowed': False,
            'available_units': 1,
            'current_units': 3,
            'limit': 4,
            'reason': '단일 종목 최대 4유닛 초과'
        }
        
        >>> check_single_position_limit(2, 1, 4)
        {
            'allowed': True,
            'available_units': 2,
            'current_units': 2,
            'limit': 4
        }
    
    Notes:
        - 단일 종목에 과도한 집중 방지
        - 한 종목의 급락 시 피해 최소화
    """
    # 1. 타입 검증
    if not isinstance(current_units, numbers.Number):
        raise TypeError(f"current_units는 숫자여야 합니다: {type(current_units)}")
    
    if not isinstance(additional_units, numbers.Number):
        raise TypeError(f"additional_units는 숫자여야 합니다: {type(additional_units)}")
    
    if not isinstance(max_units_per_position, numbers.Number):
        raise TypeError(f"max_units_per_position은 숫자여야 합니다: {type(max_units_per_position)}")
    
    # 2. 값 검증
    if current_units < 0:
        raise ValueError(f"현재 유닛은 음수일 수 없습니다: {current_units}")
    
    if additional_units < 0:
        raise ValueError(f"추가 유닛은 음수일 수 없습니다: {additional_units}")
    
    if max_units_per_position <= 0:
        raise ValueError(f"최대 유닛은 양수여야 합니다: {max_units_per_position}")
    
    # 정수로 변환
    current_units = int(current_units)
    additional_units = int(additional_units)
    max_units_per_position = int(max_units_per_position)
    
    logger.debug(
        f"단일 종목 제한 체크: 현재={current_units}유닛, "
        f"추가={additional_units}유닛, 한도={max_units_per_position}유닛"
    )
    
    # 3. 추가 가능 유닛 계산
    available_units = max_units_per_position - current_units
    available_units = max(0, available_units)
    
    # 4. 허용 여부 판단
    total_units = current_units + additional_units
    allowed = total_units <= max_units_per_position
    
    # 5. 결과 구성
    result = {
        'allowed': allowed,
        'available_units': available_units,
        'current_units': current_units,
        'limit': max_units_per_position
    }
    
    if not allowed:
        result['reason'] = f'단일 종목 최대 {max_units_per_position}유닛 초과'
        logger.warning(
            f"❌ 단일 종목 제한 초과: {total_units}유닛 > {max_units_per_position}유닛 "
            f"(추가 가능: {available_units}유닛)"
        )
    else:
        logger.debug(
            f"✅ 단일 종목 제한 통과: {total_units}유닛 <= {max_units_per_position}유닛 "
            f"(여유: {max_units_per_position - total_units}유닛)"
        )
    
    return result


def check_correlated_group_limit(
    positions: Dict[str, int],
    correlation_groups: Dict[str, List[str]],
    ticker: str,
    additional_units: int,
    max_correlated_units: int = 6
) -> Dict[str, Any]:
    """
    상관관계 그룹 제한 체크
    
    같은 섹터/산업군 종목들의 합계를 제한합니다.
    
    Args:
        positions: 현재 포지션 딕셔너리 {종목코드: 유닛수}
        correlation_groups: 상관관계 그룹 {그룹명: [종목코드 리스트]}
            예: {'반도체': ['005930', '000660'], 
                 '자동차': ['005380', '000270']}
        ticker: 추가하려는 종목코드
        additional_units: 추가 유닛
        max_correlated_units: 상관관계 그룹 최대 유닛 (기본값: 6)
    
    Returns:
        Dict[str, Any]: 체크 결과
            - allowed: 허용 여부 (bool)
            - available_units: 추가 가능 유닛 수 (int)
            - group_name: 해당 그룹명 (str, 그룹에 속할 때)
            - group_total: 그룹 총 유닛 (int, 그룹에 속할 때)
            - limit: 최대 한도 (int)
            - reason: 거부 사유 (str, 불허 시)
    
    Raises:
        TypeError: 입력값 타입이 잘못되었을 때
        ValueError: 값이 유효하지 않을 때
    
    Examples:
        >>> positions = {'005930': 3, '000660': 2}
        >>> groups = {'반도체': ['005930', '000660']}
        >>> check_correlated_group_limit(positions, groups, '005930', 2, 6)
        {
            'allowed': False,
            'available_units': 1,
            'group_name': '반도체',
            'group_total': 5,
            'limit': 6,
            'reason': '상관관계 그룹(반도체) 최대 6유닛 초과'
        }
    
    Notes:
        - 같은 섹터 종목들의 동반 하락 방지
        - 종목이 여러 그룹에 속할 수 있음 (가장 제한적인 것 적용)
        - 그룹에 속하지 않은 종목은 체크 통과
    """
    # 1. 타입 검증
    if not isinstance(positions, dict):
        raise TypeError(f"positions는 딕셔너리여야 합니다: {type(positions)}")
    
    if not isinstance(correlation_groups, dict):
        raise TypeError(f"correlation_groups는 딕셔너리여야 합니다: {type(correlation_groups)}")
    
    if not isinstance(ticker, str):
        raise TypeError(f"ticker는 문자열이어야 합니다: {type(ticker)}")
    
    if not isinstance(additional_units, numbers.Number):
        raise TypeError(f"additional_units는 숫자여야 합니다: {type(additional_units)}")
    
    if not isinstance(max_correlated_units, numbers.Number):
        raise TypeError(f"max_correlated_units는 숫자여야 합니다: {type(max_correlated_units)}")
    
    # 2. 값 검증
    if additional_units < 0:
        raise ValueError(f"추가 유닛은 음수일 수 없습니다: {additional_units}")
    
    if max_correlated_units <= 0:
        raise ValueError(f"최대 유닛은 양수여야 합니다: {max_correlated_units}")
    
    # 정수로 변환
    additional_units = int(additional_units)
    max_correlated_units = int(max_correlated_units)
    
    logger.debug(
        f"상관관계 그룹 제한 체크: 종목={ticker}, 추가={additional_units}유닛, "
        f"한도={max_correlated_units}유닛"
    )
    
    # 3. 해당 종목이 속한 그룹 찾기
    ticker_groups = []
    for group_name, group_tickers in correlation_groups.items():
        if ticker in group_tickers:
            ticker_groups.append(group_name)
    
    # 4. 그룹에 속하지 않으면 통과
    if not ticker_groups:
        logger.debug(f"종목 {ticker}은 상관관계 그룹에 속하지 않음 - 통과")
        return {
            'allowed': True,
            'available_units': max_correlated_units,
            'limit': max_correlated_units
        }
    
    # 5. 각 그룹별로 체크 (가장 제한적인 것 적용)
    most_restrictive = None
    min_available = float('inf')
    
    for group_name in ticker_groups:
        group_tickers = correlation_groups[group_name]
        
        # 그룹 내 총 유닛 계산
        group_total = sum(positions.get(t, 0) for t in group_tickers)
        
        # 추가 가능 유닛
        available = max_correlated_units - group_total
        available = max(0, available)
        
        # 허용 여부
        new_total = group_total + additional_units
        allowed = new_total <= max_correlated_units
        
        logger.debug(
            f"그룹 '{group_name}': 현재={group_total}유닛, "
            f"추가 후={new_total}유닛, 한도={max_correlated_units}유닛"
        )
        
        # 가장 제한적인 그룹 추적
        if available < min_available:
            min_available = available
            most_restrictive = {
                'allowed': allowed,
                'available_units': available,
                'group_name': group_name,
                'group_total': group_total,
                'limit': max_correlated_units
            }
            
            if not allowed:
                most_restrictive['reason'] = (
                    f'상관관계 그룹({group_name}) 최대 {max_correlated_units}유닛 초과'
                )
    
    # 6. 결과 반환
    if most_restrictive['allowed']:
        logger.debug(
            f"✅ 상관관계 그룹 제한 통과: {most_restrictive['group_name']} 그룹 "
            f"(여유: {most_restrictive['available_units']}유닛)"
        )
    else:
        logger.warning(
            f"❌ 상관관계 그룹 제한 초과: {most_restrictive['group_name']} 그룹 "
            f"(추가 가능: {most_restrictive['available_units']}유닛)"
        )
    
    return most_restrictive


def check_diversified_limit(
    positions: Dict[str, int],
    correlation_groups: Dict[str, List[str]],
    ticker: str,
    additional_units: int,
    max_diversified_units: int = 10
) -> Dict[str, Any]:
    """
    분산 투자 제한 체크 (상관관계 낮은 종목)
    
    서로 다른 섹터 종목들의 합계를 제한합니다.
    
    Args:
        positions: 현재 포지션 딕셔너리 {종목코드: 유닛수}
        correlation_groups: 상관관계 그룹 {그룹명: [종목코드 리스트]}
        ticker: 추가하려는 종목코드
        additional_units: 추가 유닛
        max_diversified_units: 최대 유닛 (기본값: 10)
    
    Returns:
        Dict[str, Any]: 체크 결과
            - allowed: 허용 여부 (bool)
            - available_units: 추가 가능 유닛 수 (int)
            - diversified_total: 분산 투자 총 유닛 (int)
            - limit: 최대 한도 (int)
            - reason: 거부 사유 (str, 불허 시)
    
    Raises:
        TypeError: 입력값 타입이 잘못되었을 때
        ValueError: 값이 유효하지 않을 때
    
    Examples:
        >>> positions = {'005930': 3, '000660': 2, '005380': 4}
        >>> groups = {'반도체': ['005930', '000660'], '자동차': ['005380']}
        >>> check_diversified_limit(positions, groups, '051910', 2, 10)
        {
            'allowed': False,
            'available_units': 1,
            'diversified_total': 9,
            'limit': 10,
            'reason': '분산 투자 최대 10유닛 초과'
        }
    
    Notes:
        - 서로 다른 섹터 종목들의 합계 제한
        - 예: 반도체(6) + 자동차(4) = 10유닛
        - 과도한 분산으로 인한 관리 어려움 방지
    """
    # 1. 타입 검증
    if not isinstance(positions, dict):
        raise TypeError(f"positions는 딕셔너리여야 합니다: {type(positions)}")
    
    if not isinstance(correlation_groups, dict):
        raise TypeError(f"correlation_groups는 딕셔너리여야 합니다: {type(correlation_groups)}")
    
    if not isinstance(ticker, str):
        raise TypeError(f"ticker는 문자열이어야 합니다: {type(ticker)}")
    
    if not isinstance(additional_units, numbers.Number):
        raise TypeError(f"additional_units는 숫자여야 합니다: {type(additional_units)}")
    
    if not isinstance(max_diversified_units, numbers.Number):
        raise TypeError(f"max_diversified_units는 숫자여야 합니다: {type(max_diversified_units)}")
    
    # 2. 값 검증
    if additional_units < 0:
        raise ValueError(f"추가 유닛은 음수일 수 없습니다: {additional_units}")
    
    if max_diversified_units <= 0:
        raise ValueError(f"최대 유닛은 양수여야 합니다: {max_diversified_units}")
    
    # 정수로 변환
    additional_units = int(additional_units)
    max_diversified_units = int(max_diversified_units)
    
    logger.debug(
        f"분산 투자 제한 체크: 종목={ticker}, 추가={additional_units}유닛, "
        f"한도={max_diversified_units}유닛"
    )
    
    # 3. 그룹별 합계 계산
    group_totals = {}
    all_grouped_tickers = set()
    
    for group_name, group_tickers in correlation_groups.items():
        group_total = sum(positions.get(t, 0) for t in group_tickers)
        if group_total > 0:
            group_totals[group_name] = group_total
        all_grouped_tickers.update(group_tickers)
    
    # 4. 그룹에 속하지 않은 종목들의 합계
    ungrouped_total = sum(
        units for t, units in positions.items() 
        if t not in all_grouped_tickers
    )
    
    # 5. 분산 투자 총 유닛 (그룹별 합계 + 미분류 종목)
    diversified_total = sum(group_totals.values()) + ungrouped_total
    
    # 추가 종목 반영
    if ticker in all_grouped_tickers:
        # 그룹에 속한 종목이면 이미 계산됨
        diversified_total += additional_units
    else:
        # 그룹에 속하지 않은 종목
        diversified_total += additional_units
    
    logger.debug(
        f"분산 투자 현황: 그룹별={group_totals}, 미분류={ungrouped_total}유닛, "
        f"총={diversified_total}유닛"
    )
    
    # 6. 추가 가능 유닛
    current_total = sum(group_totals.values()) + ungrouped_total
    available_units = max_diversified_units - current_total
    available_units = max(0, available_units)
    
    # 7. 허용 여부
    allowed = diversified_total <= max_diversified_units
    
    # 8. 결과 구성
    result = {
        'allowed': allowed,
        'available_units': available_units,
        'diversified_total': current_total,
        'limit': max_diversified_units
    }
    
    if not allowed:
        result['reason'] = f'분산 투자 최대 {max_diversified_units}유닛 초과'
        logger.warning(
            f"❌ 분산 투자 제한 초과: {diversified_total}유닛 > {max_diversified_units}유닛 "
            f"(추가 가능: {available_units}유닛)"
        )
    else:
        logger.debug(
            f"✅ 분산 투자 제한 통과: {diversified_total}유닛 <= {max_diversified_units}유닛 "
            f"(여유: {max_diversified_units - diversified_total}유닛)"
        )
    
    return result


def check_total_exposure_limit(
    positions: Dict[str, int],
    additional_units: int,
    max_total_units: int = 12
) -> Dict[str, Any]:
    """
    전체 포트폴리오 노출 제한 체크
    
    전체 포트폴리오의 절대 한도를 체크합니다.
    
    Args:
        positions: 현재 포지션 딕셔너리 {종목코드: 유닛수}
        additional_units: 추가 유닛
        max_total_units: 전체 최대 유닛 (기본값: 12)
    
    Returns:
        Dict[str, Any]: 체크 결과
            - allowed: 허용 여부 (bool)
            - available_units: 추가 가능 유닛 수 (int)
            - total_units: 현재 총 유닛 (int)
            - limit: 최대 한도 (int)
            - reason: 거부 사유 (str, 불허 시)
    
    Raises:
        TypeError: 입력값 타입이 잘못되었을 때
        ValueError: 값이 유효하지 않을 때
    
    Examples:
        >>> positions = {'005930': 4, '000660': 3, '005380': 4}
        >>> check_total_exposure_limit(positions, 2, 12)
        {
            'allowed': False,
            'available_units': 1,
            'total_units': 11,
            'limit': 12,
            'reason': '전체 포트폴리오 최대 12유닛 초과'
        }
    
    Notes:
        - 전체 포트폴리오의 절대 한도
        - 계좌의 12% 이상 리스크에 노출 금지
        - 모든 제한 중 최종 안전장치
    """
    # 1. 타입 검증
    if not isinstance(positions, dict):
        raise TypeError(f"positions는 딕셔너리여야 합니다: {type(positions)}")
    
    if not isinstance(additional_units, numbers.Number):
        raise TypeError(f"additional_units는 숫자여야 합니다: {type(additional_units)}")
    
    if not isinstance(max_total_units, numbers.Number):
        raise TypeError(f"max_total_units는 숫자여야 합니다: {type(max_total_units)}")
    
    # 2. 값 검증
    if additional_units < 0:
        raise ValueError(f"추가 유닛은 음수일 수 없습니다: {additional_units}")
    
    if max_total_units <= 0:
        raise ValueError(f"최대 유닛은 양수여야 합니다: {max_total_units}")
    
    # 정수로 변환
    additional_units = int(additional_units)
    max_total_units = int(max_total_units)
    
    logger.debug(
        f"전체 포트폴리오 제한 체크: 추가={additional_units}유닛, "
        f"한도={max_total_units}유닛"
    )
    
    # 3. 현재 총 유닛
    total_units = sum(positions.values())
    
    # 4. 추가 가능 유닛
    available_units = max_total_units - total_units
    available_units = max(0, available_units)
    
    # 5. 허용 여부
    new_total = total_units + additional_units
    allowed = new_total <= max_total_units
    
    # 6. 결과 구성
    result = {
        'allowed': allowed,
        'available_units': available_units,
        'total_units': total_units,
        'limit': max_total_units
    }
    
    if not allowed:
        result['reason'] = f'전체 포트폴리오 최대 {max_total_units}유닛 초과'
        logger.warning(
            f"❌ 전체 포트폴리오 제한 초과: {new_total}유닛 > {max_total_units}유닛 "
            f"(추가 가능: {available_units}유닛)"
        )
    else:
        logger.debug(
            f"✅ 전체 포트폴리오 제한 통과: {new_total}유닛 <= {max_total_units}유닛 "
            f"(여유: {max_total_units - new_total}유닛)"
        )
    
    return result


def get_available_position_size(
    ticker: str,
    desired_units: int,
    positions: Dict[str, int],
    correlation_groups: Dict[str, List[str]],
    limits: Optional[Dict[str, int]] = None
) -> Dict[str, Any]:
    """
    실제 추가 가능한 포지션 크기 계산
    
    모든 제한 조건을 종합하여 실제로 추가할 수 있는
    최대 유닛 수를 계산합니다.
    
    Args:
        ticker: 종목코드
        desired_units: 희망 유닛
        positions: 현재 포지션 딕셔너리 {종목코드: 유닛수}
        correlation_groups: 상관관계 그룹 {그룹명: [종목코드 리스트]}
        limits: 제한 설정 (None이면 기본값 사용)
            예: {
                'single': 4,
                'correlated': 6,
                'diversified': 10,
                'total': 12
            }
    
    Returns:
        Dict[str, Any]: 최종 결과
            - allowed_units: 실제 허용 유닛 (int)
            - limiting_factor: 제한 요인 (str)
                - 'single': 단일 종목 제한
                - 'correlated': 상관관계 그룹 제한
                - 'diversified': 분산 투자 제한
                - 'total': 전체 노출 제한
                - 'none': 제한 없음
            - checks: 각 제한 체크 결과 (dict)
    
    Raises:
        TypeError: 입력값 타입이 잘못되었을 때
        ValueError: 값이 유효하지 않을 때
    
    Examples:
        >>> positions = {'005930': 3, '000660': 2}
        >>> groups = {'반도체': ['005930', '000660']}
        >>> get_available_position_size('005930', 2, positions, groups)
        {
            'allowed_units': 1,
            'limiting_factor': 'correlated',
            'checks': {
                'single': {'allowed': True, ...},
                'correlated': {'allowed': False, ...},
                'diversified': {'allowed': True, ...},
                'total': {'allowed': True, ...}
            }
        }
    
    Notes:
        - 모든 제한 중 가장 제한적인 것 적용
        - 각 제한별 체크 결과도 함께 반환
        - 0 유닛이 허용될 수도 있음 (모든 한도 초과 시)
    """
    # 1. 타입 검증
    if not isinstance(ticker, str):
        raise TypeError(f"ticker는 문자열이어야 합니다: {type(ticker)}")
    
    if not isinstance(desired_units, numbers.Number):
        raise TypeError(f"desired_units는 숫자여야 합니다: {type(desired_units)}")
    
    if not isinstance(positions, dict):
        raise TypeError(f"positions는 딕셔너리여야 합니다: {type(positions)}")
    
    if not isinstance(correlation_groups, dict):
        raise TypeError(f"correlation_groups는 딕셔너리여야 합니다: {type(correlation_groups)}")
    
    if limits is not None and not isinstance(limits, dict):
        raise TypeError(f"limits는 딕셔너리여야 합니다: {type(limits)}")
    
    # 2. 값 검증
    if desired_units < 0:
        raise ValueError(f"희망 유닛은 음수일 수 없습니다: {desired_units}")
    
    # 정수로 변환
    desired_units = int(desired_units)
    
    # 3. 기본 제한값 설정
    if limits is None:
        limits = {
            'single': 4,
            'correlated': 6,
            'diversified': 10,
            'total': 12
        }
    
    logger.info(
        f"포지션 크기 계산 시작: 종목={ticker}, 희망={desired_units}유닛, "
        f"제한={limits}"
    )
    
    # 4. 현재 보유 유닛
    current_units = positions.get(ticker, 0)
    
    # 5. 각 제한별 체크
    checks = {}
    
    # 5-1. 단일 종목 제한
    checks['single'] = check_single_position_limit(
        current_units,
        desired_units,
        limits.get('single', 4)
    )
    
    # 5-2. 상관관계 그룹 제한
    checks['correlated'] = check_correlated_group_limit(
        positions,
        correlation_groups,
        ticker,
        desired_units,
        limits.get('correlated', 6)
    )
    
    # 5-3. 분산 투자 제한
    checks['diversified'] = check_diversified_limit(
        positions,
        correlation_groups,
        ticker,
        desired_units,
        limits.get('diversified', 10)
    )
    
    # 5-4. 전체 노출 제한
    checks['total'] = check_total_exposure_limit(
        positions,
        desired_units,
        limits.get('total', 12)
    )
    
    # 6. 가장 제한적인 요인 찾기
    min_available = desired_units
    limiting_factor = 'none'
    
    for check_name, check_result in checks.items():
        available = check_result['available_units']
        if available < min_available:
            min_available = available
            limiting_factor = check_name
    
    # 7. 최종 허용 유닛
    allowed_units = min_available
    
    # 8. 결과 구성
    result = {
        'allowed_units': allowed_units,
        'limiting_factor': limiting_factor,
        'checks': checks
    }
    
    # 9. 로깅
    if allowed_units == 0:
        logger.warning(
            f"⛔ 포지션 추가 불가: 종목={ticker}, "
            f"제한 요인={limiting_factor}"
        )
    elif allowed_units < desired_units:
        logger.warning(
            f"⚠️ 포지션 부분 허용: 종목={ticker}, "
            f"희망={desired_units}유닛 → 허용={allowed_units}유닛, "
            f"제한 요인={limiting_factor}"
        )
    else:
        logger.info(
            f"✅ 포지션 전체 허용: 종목={ticker}, "
            f"허용={allowed_units}유닛"
        )
    
    return result
