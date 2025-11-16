"""
리스크 노출 관리 모듈

실시간 포트폴리오 리스크 모니터링 및 관리:
- 개별 포지션 리스크 계산
- 전체 포트폴리오 리스크 집계
- 리스크 한도 검증
- 포괄적 리스크 리포트 생성

총 리스크 = Σ (포지션 크기 × 손절 거리)
"""

import logging
from typing import Dict, List, Any, Optional
import numbers

logger = logging.getLogger(__name__)


def calculate_position_risk(
    position_size: int,
    entry_price: float,
    stop_price: float,
    position_type: str = 'long'
) -> Dict[str, Any]:
    """
    개별 포지션의 리스크 계산
    
    Args:
        position_size: 포지션 크기 (주)
        entry_price: 진입가
        stop_price: 손절가
        position_type: 'long' or 'short'
    
    Returns:
        Dict: 리스크 정보
            - risk_per_share: 주당 리스크
            - total_risk: 총 리스크 금액
            - risk_percentage: 리스크 비율 (진입가 대비)
            - position_value: 포지션 가치
    
    Raises:
        ValueError: position_size가 음수일 때
        ValueError: entry_price나 stop_price가 0 이하일 때
        ValueError: position_type이 'long' 또는 'short'가 아닐 때
        ValueError: long 포지션에서 stop_price > entry_price일 때
        ValueError: short 포지션에서 stop_price < entry_price일 때
    
    Examples:
        >>> calculate_position_risk(100, 50_000, 48_000, 'long')
        {
            'risk_per_share': 2000.0,
            'total_risk': 200000.0,
            'risk_percentage': 0.04,
            'position_value': 5000000.0
        }
        
        >>> calculate_position_risk(50, 100_000, 104_000, 'short')
        {
            'risk_per_share': 4000.0,
            'total_risk': 200000.0,
            'risk_percentage': 0.04,
            'position_value': 5000000.0
        }
    """
    # 입력 검증
    if not isinstance(position_size, (int, numbers.Number)) or position_size < 0:
        raise ValueError(f"포지션 크기는 0 이상의 숫자여야 합니다: {position_size}")
    
    if not isinstance(entry_price, numbers.Number) or entry_price <= 0:
        raise ValueError(f"진입가는 양수여야 합니다: {entry_price}")
    
    if not isinstance(stop_price, numbers.Number) or stop_price <= 0:
        raise ValueError(f"손절가는 양수여야 합니다: {stop_price}")
    
    if position_type not in ['long', 'short']:
        raise ValueError(f"포지션 타입은 'long' 또는 'short'여야 합니다: {position_type}")
    
    # 포지션 타입별 손절가 유효성 검증
    if position_type == 'long' and stop_price > entry_price:
        raise ValueError(
            f"매수 포지션의 손절가는 진입가보다 낮아야 합니다: "
            f"진입가={entry_price}, 손절가={stop_price}"
        )
    
    if position_type == 'short' and stop_price < entry_price:
        raise ValueError(
            f"매도 포지션의 손절가는 진입가보다 높아야 합니다: "
            f"진입가={entry_price}, 손절가={stop_price}"
        )
    
    logger.debug(
        f"포지션 리스크 계산: 크기={position_size}주, "
        f"진입가={entry_price:,.0f}, 손절가={stop_price:,.0f}, 타입={position_type}"
    )
    
    # 주당 리스크 계산
    if position_type == 'long':
        risk_per_share = entry_price - stop_price
    else:  # short
        risk_per_share = stop_price - entry_price
    
    # 총 리스크 계산
    total_risk = risk_per_share * position_size
    
    # 리스크 비율 (진입가 대비)
    risk_percentage = risk_per_share / entry_price
    
    # 포지션 가치
    position_value = entry_price * position_size
    
    result = {
        'risk_per_share': float(risk_per_share),
        'total_risk': float(total_risk),
        'risk_percentage': float(risk_percentage),
        'position_value': float(position_value)
    }
    
    logger.debug(
        f"계산 결과: 주당 리스크={risk_per_share:,.0f}원, "
        f"총 리스크={total_risk:,.0f}원 ({risk_percentage:.2%})"
    )
    
    return result


def calculate_total_portfolio_risk(
    positions: List[Dict[str, Any]],
    account_balance: float
) -> Dict[str, Any]:
    """
    전체 포트폴리오 리스크 계산
    
    Args:
        positions: 포지션 리스트
            각 포지션: {
                'ticker': str,
                'size': int,
                'entry_price': float,
                'stop_price': float,
                'type': str  # 'long' or 'short'
            }
        account_balance: 계좌 잔고
    
    Returns:
        Dict: 포트폴리오 리스크
            - total_risk: 총 리스크 금액
            - risk_percentage: 계좌 대비 리스크 비율
            - positions_at_risk: 리스크 있는 포지션 수
            - largest_risk: 최대 리스크 포지션 정보
            - risk_by_ticker: 종목별 리스크 딕셔너리
    
    Raises:
        ValueError: account_balance가 0 이하일 때
        ValueError: positions가 리스트가 아닐 때
        ValueError: 포지션에 필수 필드가 없을 때
    
    Examples:
        >>> positions = [
        ...     {'ticker': '005930', 'size': 100, 
        ...      'entry_price': 50000, 'stop_price': 48000, 'type': 'long'},
        ...     {'ticker': '000660', 'size': 50, 
        ...      'entry_price': 100000, 'stop_price': 96000, 'type': 'long'}
        ... ]
        >>> calculate_total_portfolio_risk(positions, 10_000_000)
        {
            'total_risk': 400000.0,
            'risk_percentage': 0.04,
            'positions_at_risk': 2,
            'largest_risk': {...},
            'risk_by_ticker': {...}
        }
    """
    # 입력 검증
    if not isinstance(account_balance, numbers.Number) or account_balance <= 0:
        raise ValueError(f"계좌 잔고는 양수여야 합니다: {account_balance}")
    
    if not isinstance(positions, list):
        raise ValueError(f"포지션은 리스트여야 합니다: {type(positions)}")
    
    logger.debug(f"포트폴리오 리스크 계산: {len(positions)}개 포지션, 잔고={account_balance:,.0f}원")
    
    # 빈 포지션 처리
    if not positions:
        return {
            'total_risk': 0.0,
            'risk_percentage': 0.0,
            'positions_at_risk': 0,
            'largest_risk': None,
            'risk_by_ticker': {}
        }
    
    # 필수 필드 검증
    required_fields = ['ticker', 'size', 'entry_price', 'stop_price', 'type']
    for i, pos in enumerate(positions):
        missing_fields = [field for field in required_fields if field not in pos]
        if missing_fields:
            raise ValueError(
                f"포지션 {i}에 필수 필드가 없습니다: {missing_fields}. "
                f"필수 필드: {required_fields}"
            )
    
    # 각 포지션의 리스크 계산
    total_risk = 0.0
    risk_by_ticker = {}
    largest_risk_info = None
    max_risk = 0.0
    
    for pos in positions:
        ticker = pos['ticker']
        
        try:
            risk_info = calculate_position_risk(
                position_size=pos['size'],
                entry_price=pos['entry_price'],
                stop_price=pos['stop_price'],
                position_type=pos['type']
            )
            
            position_total_risk = risk_info['total_risk']
            total_risk += position_total_risk
            
            # 종목별 리스크 저장
            risk_by_ticker[ticker] = {
                'total_risk': position_total_risk,
                'risk_per_share': risk_info['risk_per_share'],
                'risk_percentage': risk_info['risk_percentage'],
                'position_value': risk_info['position_value'],
                'size': pos['size']
            }
            
            # 최대 리스크 포지션 추적
            if position_total_risk > max_risk:
                max_risk = position_total_risk
                largest_risk_info = {
                    'ticker': ticker,
                    'total_risk': position_total_risk,
                    'size': pos['size'],
                    'entry_price': pos['entry_price'],
                    'stop_price': pos['stop_price'],
                    'type': pos['type']
                }
        
        except ValueError as e:
            logger.warning(f"종목 {ticker} 리스크 계산 실패: {e}")
            continue
    
    # 계좌 대비 리스크 비율
    risk_percentage = total_risk / account_balance if account_balance > 0 else 0.0
    
    # 리스크가 있는 포지션 수 (total_risk > 0)
    positions_at_risk = sum(1 for risk in risk_by_ticker.values() if risk['total_risk'] > 0)
    
    result = {
        'total_risk': float(total_risk),
        'risk_percentage': float(risk_percentage),
        'positions_at_risk': positions_at_risk,
        'largest_risk': largest_risk_info,
        'risk_by_ticker': risk_by_ticker
    }
    
    logger.debug(
        f"포트폴리오 총 리스크: {total_risk:,.0f}원 ({risk_percentage:.2%}), "
        f"리스크 포지션 수: {positions_at_risk}개"
    )
    
    return result


def check_risk_limits(
    total_risk: float,
    account_balance: float,
    positions_risk: Dict[str, Dict[str, Any]] = None,
    max_risk_percentage: float = 0.02,
    max_single_risk: float = 0.01
) -> Dict[str, Any]:
    """
    리스크 한도 체크
    
    Args:
        total_risk: 총 리스크
        account_balance: 계좌 잔고
        positions_risk: 종목별 리스크 딕셔너리 (선택)
        max_risk_percentage: 최대 리스크 비율 (기본값: 2%)
        max_single_risk: 단일 포지션 최대 리스크 (기본값: 1%)
    
    Returns:
        Dict: 한도 체크 결과
            - within_limits: 한도 내 여부
            - total_risk_ok: 총 리스크 OK
            - single_risk_ok: 단일 포지션 리스크 OK (positions_risk 제공 시)
            - risk_percentage: 현재 리스크 비율
            - available_risk: 남은 리스크 여유 (금액)
            - warnings: 경고 메시지 리스트
    
    Raises:
        ValueError: total_risk가 음수일 때
        ValueError: account_balance가 0 이하일 때
        ValueError: max_risk_percentage가 0~1 범위 밖일 때
        ValueError: max_single_risk가 0~1 범위 밖일 때
    
    Notes:
        권장 한도:
        - 총 리스크: 계좌의 2% 이하
        - 단일 포지션: 계좌의 1% 이하
    
    Examples:
        >>> check_risk_limits(150_000, 10_000_000)
        {
            'within_limits': True,
            'total_risk_ok': True,
            'single_risk_ok': None,
            'risk_percentage': 0.015,
            'available_risk': 50000.0,
            'warnings': []
        }
    """
    # 입력 검증
    if not isinstance(total_risk, numbers.Number) or total_risk < 0:
        raise ValueError(f"총 리스크는 0 이상이어야 합니다: {total_risk}")
    
    if not isinstance(account_balance, numbers.Number) or account_balance <= 0:
        raise ValueError(f"계좌 잔고는 양수여야 합니다: {account_balance}")
    
    if not isinstance(max_risk_percentage, numbers.Number) or not 0 < max_risk_percentage <= 1:
        raise ValueError(
            f"최대 리스크 비율은 0~1 사이여야 합니다: {max_risk_percentage}"
        )
    
    if not isinstance(max_single_risk, numbers.Number) or not 0 < max_single_risk <= 1:
        raise ValueError(
            f"단일 포지션 최대 리스크는 0~1 사이여야 합니다: {max_single_risk}"
        )
    
    logger.debug(
        f"리스크 한도 체크: 총 리스크={total_risk:,.0f}원, "
        f"잔고={account_balance:,.0f}원, 최대 리스크={max_risk_percentage:.2%}"
    )
    
    warnings = []
    
    # 현재 리스크 비율
    risk_percentage = total_risk / account_balance
    
    # 총 리스크 한도 체크
    max_total_risk = account_balance * max_risk_percentage
    total_risk_ok = total_risk <= max_total_risk
    
    if not total_risk_ok:
        excess = total_risk - max_total_risk
        warnings.append(
            f"총 리스크가 한도를 초과했습니다: "
            f"{total_risk:,.0f}원 > {max_total_risk:,.0f}원 "
            f"(초과: {excess:,.0f}원, {excess/account_balance:.2%})"
        )
    
    # 남은 리스크 여유
    available_risk = max(0, max_total_risk - total_risk)
    
    # 단일 포지션 리스크 체크
    single_risk_ok = None
    if positions_risk:
        max_single_risk_amount = account_balance * max_single_risk
        
        violating_positions = []
        for ticker, risk_info in positions_risk.items():
            position_risk = risk_info['total_risk']
            if position_risk > max_single_risk_amount:
                excess = position_risk - max_single_risk_amount
                violating_positions.append(
                    f"{ticker}: {position_risk:,.0f}원 > {max_single_risk_amount:,.0f}원 "
                    f"(초과: {excess:,.0f}원)"
                )
        
        single_risk_ok = len(violating_positions) == 0
        
        if not single_risk_ok:
            warnings.append(
                f"단일 포지션 리스크 한도 초과: {', '.join(violating_positions)}"
            )
    
    # 경고성 메시지 (한도는 넘지 않았지만 90% 이상)
    if total_risk_ok and risk_percentage >= max_risk_percentage * 0.9:
        warnings.append(
            f"총 리스크가 한도의 90%에 근접했습니다: "
            f"{risk_percentage:.2%} (한도: {max_risk_percentage:.2%})"
        )
    
    # 전체 한도 내 여부
    within_limits = total_risk_ok and (single_risk_ok is None or single_risk_ok)
    
    result = {
        'within_limits': within_limits,
        'total_risk_ok': total_risk_ok,
        'single_risk_ok': single_risk_ok,
        'risk_percentage': float(risk_percentage),
        'available_risk': float(available_risk),
        'warnings': warnings
    }
    
    if warnings:
        for warning in warnings:
            logger.warning(warning)
    else:
        logger.debug(f"리스크 한도 OK: {risk_percentage:.2%}, 여유={available_risk:,.0f}원")
    
    return result


def generate_risk_report(
    positions: List[Dict[str, Any]],
    account_balance: float,
    correlation_groups: Dict[str, List[str]] = None,
    max_risk_percentage: float = 0.02,
    max_single_risk: float = 0.01
) -> Dict[str, Any]:
    """
    포괄적 리스크 리포트 생성
    
    Args:
        positions: 포지션 리스트
            각 포지션: {
                'ticker': str,
                'size': int,
                'entry_price': float,
                'stop_price': float,
                'type': str
            }
        account_balance: 계좌 잔고
        correlation_groups: 상관관계 그룹 (선택)
            예: {'반도체': ['005930', '000660']}
        max_risk_percentage: 최대 리스크 비율 (기본값: 2%)
        max_single_risk: 단일 포지션 최대 리스크 (기본값: 1%)
    
    Returns:
        Dict: 리스크 리포트
            - summary: 요약 정보
                - total_positions: 총 포지션 수
                - total_value: 총 포지션 가치
                - total_risk: 총 리스크
                - risk_percentage: 리스크 비율
                - within_limits: 한도 내 여부
            - by_ticker: 종목별 리스크
            - by_group: 그룹별 리스크 (상관관계 그룹 제공 시)
            - limits: 한도 체크 결과
            - warnings: 경고 및 권장사항
    
    Raises:
        ValueError: account_balance가 0 이하일 때
        ValueError: positions가 리스트가 아닐 때
    
    Notes:
        대시보드/알림 시스템에서 활용
        
    Examples:
        >>> positions = [
        ...     {'ticker': '005930', 'size': 100, 
        ...      'entry_price': 50000, 'stop_price': 48000, 'type': 'long'},
        ...     {'ticker': '000660', 'size': 50, 
        ...      'entry_price': 100000, 'stop_price': 96000, 'type': 'long'}
        ... ]
        >>> groups = {'반도체': ['005930', '000660']}
        >>> report = generate_risk_report(positions, 10_000_000, groups)
    """
    # 입력 검증
    if not isinstance(account_balance, numbers.Number) or account_balance <= 0:
        raise ValueError(f"계좌 잔고는 양수여야 합니다: {account_balance}")
    
    if not isinstance(positions, list):
        raise ValueError(f"포지션은 리스트여야 합니다: {type(positions)}")
    
    logger.info(f"리스크 리포트 생성 시작: {len(positions)}개 포지션")
    
    # 1. 전체 포트폴리오 리스크 계산
    portfolio_risk = calculate_total_portfolio_risk(positions, account_balance)
    
    # 2. 리스크 한도 체크
    limits_check = check_risk_limits(
        total_risk=portfolio_risk['total_risk'],
        account_balance=account_balance,
        positions_risk=portfolio_risk['risk_by_ticker'],
        max_risk_percentage=max_risk_percentage,
        max_single_risk=max_single_risk
    )
    
    # 3. 요약 정보
    total_value = sum(
        pos['entry_price'] * pos['size'] for pos in positions
    )
    
    summary = {
        'total_positions': len(positions),
        'total_value': float(total_value),
        'total_risk': portfolio_risk['total_risk'],
        'risk_percentage': portfolio_risk['risk_percentage'],
        'within_limits': limits_check['within_limits'],
        'positions_at_risk': portfolio_risk['positions_at_risk']
    }
    
    # 4. 종목별 리스크 (상세 정보 추가)
    by_ticker = {}
    for ticker, risk_info in portfolio_risk['risk_by_ticker'].items():
        # 해당 종목의 포지션 정보 찾기
        pos_info = next((p for p in positions if p['ticker'] == ticker), None)
        
        by_ticker[ticker] = {
            **risk_info,
            'entry_price': pos_info['entry_price'] if pos_info else 0,
            'stop_price': pos_info['stop_price'] if pos_info else 0,
            'type': pos_info['type'] if pos_info else 'unknown',
            'risk_ratio': risk_info['total_risk'] / account_balance
        }
    
    # 5. 그룹별 리스크 (상관관계 그룹 제공 시)
    by_group = None
    if correlation_groups:
        by_group = {}
        for group_name, tickers in correlation_groups.items():
            group_risk = 0.0
            group_value = 0.0
            group_positions = []
            
            for ticker in tickers:
                if ticker in portfolio_risk['risk_by_ticker']:
                    risk_info = portfolio_risk['risk_by_ticker'][ticker]
                    group_risk += risk_info['total_risk']
                    group_value += risk_info['position_value']
                    group_positions.append(ticker)
            
            if group_positions:  # 그룹에 포지션이 있을 때만 추가
                by_group[group_name] = {
                    'total_risk': float(group_risk),
                    'total_value': float(group_value),
                    'risk_percentage': float(group_risk / account_balance),
                    'positions': group_positions,
                    'position_count': len(group_positions)
                }
    
    # 6. 경고 및 권장사항
    warnings = limits_check['warnings'].copy()
    
    # 추가 경고 및 권장사항
    if portfolio_risk['positions_at_risk'] > 5:
        warnings.append(
            f"보유 포지션이 많습니다 ({portfolio_risk['positions_at_risk']}개). "
            "포트폴리오 관리에 주의가 필요합니다."
        )
    
    if portfolio_risk['largest_risk']:
        largest = portfolio_risk['largest_risk']
        largest_ratio = largest['total_risk'] / account_balance
        if largest_ratio > max_single_risk * 0.8:
            warnings.append(
                f"최대 리스크 포지션({largest['ticker']})이 "
                f"단일 포지션 한도의 80%를 초과했습니다: {largest_ratio:.2%}"
            )
    
    # 7. 최종 리포트
    report = {
        'summary': summary,
        'by_ticker': by_ticker,
        'by_group': by_group,
        'limits': limits_check,
        'warnings': warnings,
        'largest_risk': portfolio_risk['largest_risk']
    }
    
    logger.info(
        f"리스크 리포트 생성 완료: "
        f"총 리스크={summary['total_risk']:,.0f}원 ({summary['risk_percentage']:.2%}), "
        f"한도 내={limits_check['within_limits']}, "
        f"경고={len(warnings)}개"
    )
    
    return report
