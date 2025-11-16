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

import logging
from typing import Dict, Any, Optional
import pandas as pd
import numbers

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

from src.analysis.risk.portfolio import (
    check_single_position_limit,
    check_correlated_group_limit,
    check_diversified_limit,
    check_total_exposure_limit,
    get_available_position_size
)

from src.analysis.risk.exposure import (
    calculate_position_risk,
    calculate_total_portfolio_risk,
    check_risk_limits,
    generate_risk_report
)

logger = logging.getLogger(__name__)


def apply_risk_management(
    signal: Dict[str, Any],
    account_balance: float,
    positions: Dict[str, int],
    market_data: pd.DataFrame,
    config: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    통합 리스크 관리 적용
    
    전체 프로세스:
    1. 포지션 사이징 (Level 5-1)
    2. 포트폴리오 제한 체크 (Level 5-3)
    3. 손절가 계산 (Level 5-2)
    4. 리스크 평가 (Level 5-4)
    5. 최종 승인/거부 결정
    
    Args:
        signal: 매매 신호 (Level 4 출력)
            {
                'ticker': str,
                'action': str,  # 'buy', 'sell', 'exit'
                'signal_strength': int,  # 0-100
                'current_price': float
            }
        account_balance: 계좌 잔고
        positions: 현재 포지션 {종목코드: 유닛수}
        market_data: 시장 데이터 (ATR, 이동평균선 등)
            필수 컬럼: 'ATR', 'EMA_20' (또는 설정된 stop_ma)
        config: 설정 (선택)
            {
                'risk_percentage': float,  # 기본값: 0.01 (1%)
                'desired_units_per_signal': int,  # 기본값: 2 (한 신호당 목표 유닛 수)
                'signal_strength_threshold': int,  # 기본값: 80
                'atr_multiplier': float,  # 기본값: 2.0
                'stop_ma': str,  # 기본값: 'EMA_20'
                'limits': {  # 포트폴리오 제한
                    'single': int,  # 기본값: 4
                    'correlated': int,  # 기본값: 6
                    'diversified': int,  # 기본값: 10
                    'total': int  # 기본값: 12
                },
                'correlation_groups': Dict[str, List[str]],
                'max_risk_percentage': float,  # 기본값: 0.02 (2%)
                'max_single_risk': float  # 기본값: 0.01 (1%)
            }
    
    Returns:
        Dict: 리스크 관리 결과
            - approved: 승인 여부 (bool)
            - position_size: 권장 포지션 크기 (주) - 승인 시
            - units: 유닛 수 - 승인 시
            - stop_price: 손절가 - 승인 시
            - risk_amount: 리스크 금액 - 승인 시
            - risk_percentage: 리스크 비율 - 승인 시
            - warnings: 경고 메시지 (list)
            - reason: 거부 사유 (str) - 불승인 시
            - details: 상세 정보 (dict) - 디버깅용
    
    Raises:
        ValueError: 필수 입력값이 누락되거나 잘못된 경우
        ValueError: market_data에 필수 컬럼이 없는 경우
    
    Examples:
        >>> signal = {
        ...     'ticker': '005930',
        ...     'action': 'buy',
        ...     'signal_strength': 85,
        ...     'current_price': 50_000
        ... }
        >>> market_data = pd.DataFrame({
        ...     'ATR': [1_000],
        ...     'EMA_20': [48_500]
        ... })
        >>> result = apply_risk_management(
        ...     signal, 10_000_000, {'005930': 2}, market_data
        ... )
        >>> if result['approved']:
        ...     print(f"주문 실행: {result['position_size']}주")
        ...     print(f"손절가: {result['stop_price']:,}원")
    """
    # 기본 설정값
    default_config = {
        'risk_percentage': 0.01,
        'desired_units_per_signal': 2,  # 한 번의 신호로 목표하는 기본 유닛 수
        'signal_strength_threshold': 80,
        'atr_multiplier': 2.0,
        'stop_ma': 'EMA_20',
        'limits': {
            'single': 4,
            'correlated': 6,
            'diversified': 10,
            'total': 12
        },
        'correlation_groups': {},
        'max_risk_percentage': 0.02,
        'max_single_risk': 0.01
    }
    
    # 설정 병합
    if config is None:
        config = {}
    
    cfg = {**default_config, **config}
    if 'limits' in config:
        cfg['limits'] = {**default_config['limits'], **config['limits']}
    
    logger.info(f"리스크 관리 시작: {signal.get('ticker')} {signal.get('action')}")
    
    # === 입력 검증 ===
    required_signal_fields = ['ticker', 'action', 'signal_strength', 'current_price']
    missing_fields = [f for f in required_signal_fields if f not in signal]
    if missing_fields:
        raise ValueError(f"신호에 필수 필드가 없습니다: {missing_fields}")
    
    if not isinstance(account_balance, numbers.Number) or account_balance <= 0:
        raise ValueError(f"계좌 잔고는 양수여야 합니다: {account_balance}")
    
    if not isinstance(positions, dict):
        raise ValueError(f"포지션은 딕셔너리여야 합니다: {type(positions)}")
    
    if not isinstance(market_data, pd.DataFrame):
        raise ValueError(f"시장 데이터는 DataFrame이어야 합니다: {type(market_data)}")
    
    # 필수 컬럼 확인
    required_columns = ['ATR', cfg['stop_ma']]
    missing_columns = [col for col in required_columns if col not in market_data.columns]
    if missing_columns:
        raise ValueError(f"시장 데이터에 필수 컬럼이 없습니다: {missing_columns}")
    
    if market_data.empty:
        raise ValueError("시장 데이터가 비어있습니다")
    
    # 신호 추출
    ticker = signal['ticker']
    action = signal['action']
    signal_strength = int(signal['signal_strength'])
    current_price = float(signal['current_price'])
    
    # exit 신호는 리스크 관리 불필요
    if action == 'exit':
        logger.info(f"{ticker} 청산 신호 - 리스크 관리 스킵")
        return {
            'approved': True,
            'position_size': 0,
            'units': 0,
            'stop_price': 0,
            'risk_amount': 0,
            'risk_percentage': 0,
            'warnings': ['청산 신호 - 포지션 종료'],
            'details': {'action': 'exit'}
        }
    
    # 포지션 타입 결정
    position_type = 'long' if action == 'buy' else 'short'
    
    # 현재 데이터 (최신 행)
    latest_data = market_data.iloc[-1]
    atr = float(latest_data['ATR'])
    trend_stop_value = float(latest_data[cfg['stop_ma']])
    
    warnings = []
    
    # =========================
    # 1. 포지션 사이징 (Level 5-1)
    # =========================
    logger.debug("Step 1: 포지션 사이징")
    
    try:
        # 1.1 기본 유닛 계산
        unit_size = calculate_unit_size(
            account_balance=account_balance,
            atr=atr,
            risk_percentage=cfg['risk_percentage']
        )
        
        # 1.2 신호 강도 조정 (주식 수 조정)
        # 기본적으로 2유닛을 목표로 하되, 신호 강도에 따라 조정
        base_shares = unit_size * cfg.get('desired_units_per_signal', 2)
        adjusted_shares = adjust_by_signal_strength(
            base_units=base_shares,
            signal_strength=signal_strength,
            strength_threshold=cfg['signal_strength_threshold']
        )
        
        if adjusted_shares == 0:
            logger.info(f"{ticker} 신호 강도 부족: {signal_strength}점")
            return {
                'approved': False,
                'reason': f'신호 강도가 기준({cfg["signal_strength_threshold"]}점)에 미달: {signal_strength}점',
                'warnings': [],
                'details': {
                    'signal_strength': signal_strength,
                    'threshold': cfg['signal_strength_threshold']
                }
            }
        
        # 1.3 자본 제약 확인
        max_shares_by_capital = get_max_position_by_capital(
            account_balance=account_balance,
            current_price=current_price,
            max_capital_ratio=cfg.get('max_capital_ratio', 0.25)
        )
        
        # 최종 주식 수 (신호 강도 조정과 자본 제약 중 작은 값)
        shares = min(adjusted_shares, max_shares_by_capital)
        
        # 유닛 수 계산
        desired_units = max(1, shares // unit_size) if unit_size > 0 else 0
        
        logger.debug(
            f"포지션 사이징 결과: {shares}주 ({desired_units}유닛) "
            f"(기본 유닛={unit_size}, 목표 shares={base_shares}, 조정 shares={adjusted_shares}, 자본 제약={max_shares_by_capital})"
        )
        
    except Exception as e:
        logger.error(f"포지션 사이징 실패: {e}")
        return {
            'approved': False,
            'reason': f'포지션 사이징 오류: {str(e)}',
            'warnings': [],
            'details': {'error': str(e)}
        }
    
    # =========================
    # 2. 포트폴리오 제한 체크 (Level 5-3)
    # =========================
    logger.debug("Step 2: 포트폴리오 제한 체크")
    
    try:
        available = get_available_position_size(
            ticker=ticker,
            desired_units=desired_units,
            positions=positions,
            correlation_groups=cfg['correlation_groups'],
            limits=cfg['limits']
        )
        
        if available['allowed_units'] < desired_units:
            limiting_factor = available['limiting_factor']
            logger.info(
                f"{ticker} 포트폴리오 제한: "
                f"희망={desired_units}유닛, 허용={available['allowed_units']}유닛 "
                f"(제한 요인: {limiting_factor})"
            )
            
            if available['allowed_units'] == 0:
                return {
                    'approved': False,
                    'reason': f'포트폴리오 제한 초과: {limiting_factor}',
                    'warnings': warnings,
                    'details': available
                }
            else:
                # 일부만 허용
                warning_msg = (
                    f"포지션 크기 축소: {desired_units}유닛 → {available['allowed_units']}유닛 "
                    f"(제한: {limiting_factor})"
                )
                warnings.append(warning_msg)
                logger.warning(warning_msg)
                desired_units = available['allowed_units']
                shares = desired_units * unit_size
        
        logger.debug(f"포트폴리오 제한 통과: {desired_units}유닛 ({shares}주)")
        
    except Exception as e:
        logger.error(f"포트폴리오 제한 체크 실패: {e}")
        return {
            'approved': False,
            'reason': f'포트폴리오 제한 체크 오류: {str(e)}',
            'warnings': warnings,
            'details': {'error': str(e)}
        }
    
    # =========================
    # 3. 손절가 계산 (Level 5-2)
    # =========================
    logger.debug("Step 3: 손절가 계산")
    
    try:
        # 3.1 변동성 기반 손절
        volatility_stop = calculate_volatility_stop(
            entry_price=current_price,
            atr=atr,
            position_type=position_type,
            atr_multiplier=cfg['atr_multiplier']
        )
        
        # 3.2 추세 기반 손절
        # (단일 값이므로 그대로 사용)
        trend_stop = trend_stop_value
        
        # 3.3 최종 손절가 결정
        stop_info = get_stop_loss_price(
            entry_price=current_price,
            current_price=current_price,
            atr=atr,
            trend_stop=trend_stop,
            position_type=position_type
        )
        
        stop_price = stop_info['stop_price']
        stop_type = stop_info['stop_type']
        
        logger.debug(
            f"손절가: {stop_price:,.0f}원 (타입: {stop_type}, "
            f"변동성={volatility_stop:,.0f}, 추세={trend_stop:,.0f})"
        )
        
    except Exception as e:
        logger.error(f"손절가 계산 실패: {e}")
        return {
            'approved': False,
            'reason': f'손절가 계산 오류: {str(e)}',
            'warnings': warnings,
            'details': {'error': str(e)}
        }
    
    # =========================
    # 4. 리스크 평가 (Level 5-4)
    # =========================
    logger.debug("Step 4: 리스크 평가")
    
    try:
        # 4.1 신규 포지션 리스크 계산
        new_position_risk = calculate_position_risk(
            position_size=shares,
            entry_price=current_price,
            stop_price=stop_price,
            position_type=position_type
        )
        
        total_risk = new_position_risk['total_risk']
        # 계좌 대비 리스크 비율 계산
        risk_percentage = total_risk / account_balance
        
        # 4.2 기존 포지션들의 리스크와 합산 (간단 버전)
        # 실제로는 기존 포지션의 손절가 정보가 필요하지만,
        # 여기서는 신규 포지션만 검증
        
        # 4.3 리스크 한도 체크
        limits_check = check_risk_limits(
            total_risk=total_risk,
            account_balance=account_balance,
            positions_risk=None,  # 신규 포지션만 체크
            max_risk_percentage=cfg['max_risk_percentage'],
            max_single_risk=cfg['max_single_risk']
        )
        
        # 경고 추가
        warnings.extend(limits_check['warnings'])
        
        if not limits_check['within_limits']:
            logger.warning(f"{ticker} 리스크 한도 초과")
            return {
                'approved': False,
                'reason': '리스크 한도 초과',
                'warnings': warnings,
                'details': {
                    'risk_check': limits_check,
                    'position_risk': new_position_risk
                }
            }
        
        logger.debug(
            f"리스크 평가: {total_risk:,.0f}원 ({risk_percentage:.2%}), "
            f"한도 내={limits_check['within_limits']}"
        )
        
    except Exception as e:
        logger.error(f"리스크 평가 실패: {e}")
        return {
            'approved': False,
            'reason': f'리스크 평가 오류: {str(e)}',
            'warnings': warnings,
            'details': {'error': str(e)}
        }
    
    # =========================
    # 5. 최종 승인
    # =========================
    logger.info(
        f"✓ {ticker} 리스크 관리 승인: "
        f"{shares}주 ({desired_units}유닛), "
        f"손절가={stop_price:,.0f}원, "
        f"리스크={total_risk:,.0f}원 ({risk_percentage:.2%})"
    )
    
    return {
        'approved': True,
        'position_size': shares,
        'units': desired_units,
        'stop_price': stop_price,
        'stop_type': stop_type,
        'risk_amount': total_risk,
        'risk_percentage': risk_percentage,
        'warnings': warnings,
        'details': {
            'position_sizing': {
                'base_unit_size': unit_size,
                'base_shares': base_shares,
                'adjusted_shares': adjusted_shares,
                'max_shares_by_capital': max_shares_by_capital
            },
            'portfolio_limits': available,
            'stop_loss': stop_info,
            'risk_assessment': {
                'position_risk': new_position_risk,
                'limits_check': limits_check
            }
        }
    }


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
    # Portfolio
    'check_single_position_limit',
    'check_correlated_group_limit',
    'check_diversified_limit',
    'check_total_exposure_limit',
    'get_available_position_size',
    # Exposure
    'calculate_position_risk',
    'calculate_total_portfolio_risk',
    'check_risk_limits',
    'generate_risk_report',
    # Integration
    'apply_risk_management',
]
